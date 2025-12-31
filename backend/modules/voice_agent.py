"""
Voice Agent Module
Handles the core voice agent functionality including audio streaming,
message processing, and function calling
"""
import os
import sys
from contextlib import contextmanager
import pyaudio
import asyncio
import websockets
import json
import logging
import time
from datetime import datetime
from fastapi import WebSocket

@contextmanager
def suppress_stderr():
    """Suppress stderr to hide ALSA warnings"""
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)

# Configure logger for this module
logger = logging.getLogger(__name__)

# Import common modules
try:
    from common.agent_functions import FUNCTION_MAP
    from common.agent_templates import AgentTemplates
except ImportError:
    from backend.common.agent_functions import FUNCTION_MAP
    from backend.common.agent_templates import AgentTemplates

# Import audio handler and conversation logger
try:
    from .audio_handler import Speaker
    from .conversation_logger import ConversationLogger
except ImportError:
    try:
        from audio_handler import Speaker
        from conversation_logger import ConversationLogger
    except ImportError:
        from backend.modules.audio_handler import Speaker
        from backend.modules.conversation_logger import ConversationLogger

logger = logging.getLogger(__name__)


class VoiceAgent:
    """
    Main Voice Agent class that handles:
    - Audio input/output
    - WebSocket communication with Deepgram
    - Function calling and message processing
    """
    
    def __init__(
        self,
        industry="deepgram",
        voiceModel="aura-2-thalia-en",
        voiceName="",
        browser_audio=False,
    ):
        self.mic_audio_queue = asyncio.Queue()
        self.speaker = None
        self.ws = None
        self.is_running = False
        self.loop = None
        self.audio = None
        self.stream = None
        self.input_device_id = None
        self.output_device_id = None
        self.browser_audio = browser_audio  # For browser microphone input
        self.browser_output = browser_audio  # Use same setting for browser output
        self.agent_templates = AgentTemplates(industry, voiceModel, voiceName)
        
        # Task management
        self.tasks = set()
        self._shutdown_event = asyncio.Event()
        self.websocket_connection = None
        
        # Conversation logger
        self.conversation_logger = ConversationLogger()

    def set_loop(self, loop):
        """Set the event loop for this voice agent"""
        self.loop = loop

    def set_websocket_connection(self, websocket: WebSocket):
        """Set the WebSocket connection for frontend communication"""
        self.websocket_connection = websocket

    async def create_task(self, coro, name=None):
        """Create a managed task that will be properly cleaned up"""
        task = asyncio.create_task(coro, name=name)
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)
        return task

    async def cancel_all_tasks(self):
        """Cancel all managed tasks and wait for them to complete"""
        if not self.tasks:
            return
        
        logger.info(f"Cancelling {len(self.tasks)} tasks")
        for task in self.tasks.copy():
            if not task.done():
                task.cancel()
        
        # Wait for all tasks to complete (cancelled or finished)
        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        
        self.tasks.clear()

    async def shutdown(self):
        """Gracefully shutdown the voice agent"""
        logger.info("Shutting down voice agent")
        self.is_running = False
        self._shutdown_event.set()
        
        # End conversation logging
        self.conversation_logger.end_session()
        
        # Cancel all tasks
        await self.cancel_all_tasks()
        
        # Close websocket if still open
        if self.ws:
            try:
                await close_websocket_with_timeout(self.ws)
            except Exception as e:
                logger.warning(f"Error closing websocket during shutdown: {e}")
        
        # Cleanup resources
        self.cleanup()

    async def setup(self):
        """Setup connection to Deepgram Voice Agent API"""
        dg_api_key = os.environ.get("DEEPGRAM_API_KEY")
        if dg_api_key is None:
            logger.error("DEEPGRAM_API_KEY env var not present")
            return False

        settings = self.agent_templates.settings

        try:
            self.ws = await websockets.connect(
                self.agent_templates.voice_agent_url,
                additional_headers={"Authorization": f"Token {dg_api_key}"},
            )
            await self.ws.send(json.dumps(settings))
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Deepgram: {e}")
            return False

    def audio_callback(self, input_data, frame_count, time_info, status_flag):
        """PyAudio callback for microphone input"""
        if self.is_running and self.loop and not self.loop.is_closed():
            try:
                future = asyncio.run_coroutine_threadsafe(
                    self.mic_audio_queue.put(input_data), self.loop
                )
                future.result(timeout=1)  # Add timeout to prevent blocking
            except Exception as e:
                logger.error(f"Error in audio callback: {e}")
        return (input_data, pyaudio.paContinue)

    async def start_microphone(self):
        """Start microphone input stream - DISABLED for browser audio mode"""
        # In Docker/Cloud environments, we use browser audio capture instead
        # This avoids PyAudio/ALSA errors in containers without audio devices
        logger.info("Skipping local microphone initialization - using browser audio capture")
        return None, None

    def cleanup(self):
        """Clean up audio resources"""
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error closing audio stream: {e}")

        if self.audio:
            try:
                self.audio.terminate()
            except Exception as e:
                logger.error(f"Error terminating audio: {e}")

    async def sender(self):
        """Send audio data from microphone to Deepgram"""
        try:
            logger.info(f"Audio sender started (browser_audio={self.browser_audio})")
            first_chunk = True

            while self.is_running and not self._shutdown_event.is_set():
                data = await self.mic_audio_queue.get()
                if self.ws and data:
                    if first_chunk:
                        logger.debug(
                            f"Sending first audio chunk to Deepgram: {len(data)} bytes"
                        )
                        first_chunk = False

                    await self.ws.send(data)

        except websockets.exceptions.ConnectionClosedError as e:
            logger.info(f"Websocket connection closed: {e}")
        except Exception as e:
            logger.error(f"Error in sender: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def receiver(self):
        """Receive and process messages from Deepgram"""
        # Import manager here to avoid circular imports
        try:
            from .websocket_manager import ConnectionManager
        except ImportError:
            try:
                from websocket_manager import ConnectionManager
            except ImportError:
                from backend.modules.websocket_manager import ConnectionManager
        
        # Get the global manager instance
        manager = getattr(self.receiver, 'manager', None)
        
        try:
            self.speaker = Speaker(browser_output=self.browser_output)
            last_user_message = None
            last_function_response_time = None
            in_function_chain = False

            with self.speaker:
                async for message in self.ws:
                    # Check for shutdown before processing each message
                    if self._shutdown_event.is_set():
                        break
                        
                    if isinstance(message, str):
                        message_json = json.loads(message)
                        message_type = message_json.get("type")
                        current_time = time.time()
                        
                        # Only log important message types, not conversation text
                        if message_type not in ["ConversationText", "History"]:
                            logger.info(f"Server: {message}")

                        if message_type == "UserStartedSpeaking":
                            self.speaker.stop()
                            
                        elif message_type == "ConversationText":
                            # Emit the conversation text to the client
                            if self.websocket_connection and manager:
                                await manager.send_json(
                                    {"type": "conversation_update", "data": message_json}, 
                                    self.websocket_connection
                                )

                            # Log conversation message
                            role = message_json.get("role")
                            content = message_json.get("content")
                            if role and content:
                                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                self.conversation_logger.add_message(role, content, timestamp)

                            if message_json.get("role") == "user":
                                last_user_message = current_time
                                in_function_chain = False
                            elif message_json.get("role") == "assistant":
                                in_function_chain = False

                        elif message_type == "FunctionCalling":
                            if in_function_chain and last_function_response_time:
                                latency = current_time - last_function_response_time
                                logger.info(f"LLM Decision Latency (chain): {latency:.3f}s")
                            elif last_user_message:
                                latency = current_time - last_user_message
                                logger.info(f"LLM Decision Latency (initial): {latency:.3f}s")
                            in_function_chain = True

                        elif message_type == "FunctionCallRequest":
                            await self._handle_function_call(
                                message_json, 
                                last_function_response_time,
                                manager
                            )
                            last_function_response_time = time.time()

                        elif message_type == "Welcome":
                            request_id = message_json.get('request_id')
                            logger.info(f"✅ Connected - Session ID: {request_id[:8]}...")
                            # Start conversation logging
                            if request_id:
                                timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                                self.conversation_logger.start_session(request_id, timestamp)
                        elif message_type == "CloseConnection":
                            logger.info("Closing connection...")
                            await self.ws.close()
                            break

                    elif isinstance(message, bytes):
                        await self.speaker.play(message)

        except websockets.exceptions.ConnectionClosedError as e:
            logger.info(f"Websocket connection closed in receiver: {e}")
            if self.websocket_connection and manager:
                await manager.send_json(
                    {'type': 'voice_agent_stopped', 'reason': 'connection_closed'}, 
                    self.websocket_connection
                )
            self._shutdown_event.set()
        except Exception as e:
            logger.error(f"Error in receiver: {e}")

    async def _handle_function_call(self, message_json, last_function_response_time, manager):
        """Handle function call requests from Deepgram"""
        functions = message_json.get("functions", [])
        if len(functions) > 1:
            raise NotImplementedError("Multiple functions not supported")
            
        function_name = functions[0].get("name")
        function_call_id = functions[0].get("id")
        parameters = json.loads(functions[0].get("arguments", {}))

        logger.info(f"Function call received: {function_name}")
        logger.info(f"Parameters: {parameters}")

        start_time = time.time()
        try:
            func = FUNCTION_MAP.get(function_name)
            if not func:
                raise ValueError(f"Function {function_name} not found")

            # Special handling for functions that need websocket
            if function_name in ["agent_filler", "end_call"]:
                result = await func(self.ws, parameters)

                if function_name == "agent_filler":
                    await self._handle_agent_filler(result, function_call_id, function_name)
                    return

                elif function_name == "end_call":
                    await self._handle_end_call(result, function_call_id, function_name, manager)
                    return
            else:
                result = await func(parameters)

            execution_time = time.time() - start_time
            logger.info(f"Function Execution Latency: {execution_time:.3f}s")

            # Send the response back
            response = {
                "type": "FunctionCallResponse",
                "id": function_call_id,
                "name": function_name,
                "content": json.dumps(result),
            }
            await self.ws.send(json.dumps(response))
            logger.info(f"Function response sent: {json.dumps(result)}")

        except Exception as e:
            logger.error(f"Error executing function: {str(e)}")
            result = {"error": str(e)}
            response = {
                "type": "FunctionCallResponse",
                "id": function_call_id,
                "name": function_name,
                "content": json.dumps(result),
            }
            await self.ws.send(json.dumps(response))

    async def _handle_agent_filler(self, result, function_call_id, function_name):
        """Handle agent filler function response"""
        inject_message = result["inject_message"]
        function_response = result["function_response"]

        # First send the function response
        response = {
            "type": "FunctionCallResponse",
            "id": function_call_id,
            "name": function_name,
            "content": json.dumps(function_response),
        }
        await self.ws.send(json.dumps(response))
        logger.info(f"Function response sent: {json.dumps(function_response)}")

        # Then inject the message
        await inject_agent_message(self.ws, inject_message)

    async def _handle_end_call(self, result, function_call_id, function_name, manager):
        """Handle end call function response"""
        inject_message = result["inject_message"]
        function_response = result["function_response"]

        # First send the function response
        response = {
            "type": "FunctionCallResponse",
            "id": function_call_id,
            "name": function_name,
            "content": json.dumps(function_response),
        }
        await self.ws.send(json.dumps(response))
        logger.info(f"Function response sent: {json.dumps(function_response)}")

        # Wait for farewell sequence to complete
        await wait_for_farewell_completion(self.ws, self.speaker, inject_message)

        # Notify frontend that the voice agent has stopped
        logger.info("Notifying frontend that voice agent stopped due to end_call")
        if self.websocket_connection and manager:
            await manager.send_json(
                {'type': 'voice_agent_stopped', 'reason': 'end_call'}, 
                self.websocket_connection
            )
        
        # Close the websocket
        logger.info("Sending ws close message")
        await close_websocket_with_timeout(self.ws)
        
        # Trigger shutdown
        self._shutdown_event.set()

    async def run(self):
        """Main run loop for the voice agent"""
        if not await self.setup():
            return

        self.is_running = True
        try:
            # Only start the microphone if not using browser audio
            if not self.browser_audio:
                stream, audio = await self.start_microphone()

            # Create managed tasks for sender and receiver
            sender_task = await self.create_task(self.sender(), "sender")
            receiver_task = await self.create_task(self.receiver(), "receiver")
            
            # Wait for either task to complete or shutdown event
            done, pending = await asyncio.wait(
                [sender_task, receiver_task, asyncio.create_task(self._shutdown_event.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel any remaining tasks
            for task in pending:
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
                
        except websockets.exceptions.ConnectionClosedError as e:
            logger.info(f"Websocket connection closed in run: {e}")
            # Import manager here to avoid circular imports
            from websocket_manager import ConnectionManager
            manager = getattr(self.receiver, 'manager', None)
            if self.websocket_connection and manager:
                await manager.send_json(
                    {'type': 'voice_agent_stopped', 'reason': 'connection_closed'}, 
                    self.websocket_connection
                )
        except Exception as e:
            logger.error(f"Error in run: {e}")
        finally:
            await self.shutdown()


# Helper functions

async def inject_agent_message(ws, inject_message):
    """Simple helper to inject an agent message"""
    logger.info(f"Sending InjectAgentMessage: {json.dumps(inject_message)}")
    await ws.send(json.dumps(inject_message))


async def close_websocket_with_timeout(ws, timeout=3):
    """Close websocket with timeout to avoid hanging if no close frame is received"""
    try:
        await asyncio.wait_for(ws.close(), timeout=timeout)
    except asyncio.TimeoutError:
        logger.warning(f"Websocket close timed out after {timeout}s, forcing close")
        try:
            await ws.close_connection()
        except Exception:
            pass
    except Exception as e:
        logger.error(f"Error during websocket closure: {e}")
        try:
            await ws.close_connection()
        except Exception:
            pass


async def wait_for_farewell_completion(ws, speaker, inject_message):
    """Wait for the farewell message to be spoken completely by the agent"""
    await inject_agent_message(ws, inject_message)

    # First wait for either AgentStartedSpeaking or matching ConversationText
    speaking_started = False
    while not speaking_started:
        message = await ws.recv()
        if isinstance(message, bytes):
            await speaker.play(message)
            continue

        try:
            message_json = json.loads(message)
            logger.info(f"Server: {message}")
            if message_json.get("type") == "AgentStartedSpeaking" or (
                message_json.get("type") == "ConversationText"
                and message_json.get("role") == "assistant"
                and message_json.get("content") == inject_message["message"]
            ):
                speaking_started = True
        except json.JSONDecodeError:
            continue

    # Then wait for AgentAudioDone
    audio_done = False
    while not audio_done:
        message = await ws.recv()
        if isinstance(message, bytes):
            await speaker.play(message)
            continue

        try:
            message_json = json.loads(message)
            logger.info(f"Server: {message}")
            if message_json.get("type") == "AgentAudioDone":
                audio_done = True
        except json.JSONDecodeError:
            continue

    # Give audio time to play completely
    await asyncio.sleep(3.5)


def set_manager_for_voice_agent(manager):
    """Set the ConnectionManager instance for the voice agent receiver"""
    VoiceAgent.receiver.manager = manager
