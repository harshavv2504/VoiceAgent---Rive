"""
FastAPI Voice Agent Server
Main application file that orchestrates WebSocket connections,
voice agent instances, and audio handling
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import json
import logging
import base64
import atexit
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

# Try to load .env from backend directory first, then from current directory
backend_env = Path(__file__).parent / ".env"
if backend_env.exists():
    load_dotenv(backend_env)
else:
    load_dotenv()

# Import common modules
try:
    from backend.common.log_formatter import CustomFormatter
except ImportError:
    from common.log_formatter import CustomFormatter

# Import our modular components
try:
    from backend.modules import (
        ConnectionManager,
        VoiceAgent,
        get_audio_devices,
        set_manager_for_voice_agent,
        set_manager_for_audio_playback,
    )
except ImportError:
    from modules import (
        ConnectionManager,
        VoiceAgent,
        get_audio_devices,
        set_manager_for_voice_agent,
        set_manager_for_audio_playback,
    )

# Configure FastAPI
app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins like ["http://localhost:3000"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging for the entire application
# Set up root logger to capture all logs
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)

# Remove any existing handlers to avoid duplicates
root_logger.handlers = []

# Create console handler with the custom formatter
console_handler = logging.StreamHandler()
console_handler.setFormatter(CustomFormatter(socketio=None))
root_logger.addHandler(console_handler)

# Get logger for this module
logger = logging.getLogger(__name__)

# Startup event to preload knowledge base
@app.on_event("startup")
async def startup_event():
    """Preload knowledge base and model at startup"""
    try:
        from backend.common.agent_functions import kb_search
    except ImportError:
        from common.agent_functions import kb_search
    
    if kb_search:
        logger.info("🔄 Preloading FastEmbed model...")
        kb_search._load_model()
        logger.info("✅ Model preloaded and ready!")
    else:
        logger.warning("⚠️ Knowledge base not available")

# Voice agent instances - one per user session
voice_agents = {}  # Dictionary: {websocket_id: voice_agent}
voice_agent_lock = asyncio.Lock()  # Thread-safe access

# Thread pool executor for voice agent operations (support multiple users)
voice_agent_executor = ThreadPoolExecutor(max_workers=10, thread_name_prefix="voice_agent")

# WebSocket connection manager
manager = ConnectionManager()

# Set the manager for voice agent and audio playback
set_manager_for_voice_agent(manager)
set_manager_for_audio_playback(manager)

# Mount static files (frontend build)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir / "assets")), name="assets")
    logger.info(f"✅ Serving frontend from {static_dir}")
else:
    logger.warning(f"⚠️ Static directory not found: {static_dir}")


# FastAPI routes
@app.get("/api")
async def root():
    """API status endpoint"""
    return {
        "status": "running",
        "service": "Voice Agent API",
        "endpoints": {
            "websocket": "/ws",
            "audio_devices": "/audio-devices"
        }
    }


@app.get("/audio-devices")
async def audio_devices():
    """Get available audio input devices"""
    devices = get_audio_devices()
    return {"devices": devices}


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker and monitoring"""
    return {
        "status": "healthy",
        "service": "Bean & Brew Voice Agent",
        "version": "1.0.0"
    }


def reset_voice_agent(websocket_id: int):
    """Remove a voice agent for a specific user session"""
    global voice_agents
    if websocket_id in voice_agents:
        del voice_agents[websocket_id]
        logger.info(f"Voice agent cleared for session {websocket_id}")


def run_voice_agent_in_thread(voice_agent_data, websocket_connection, websocket_id):
    """Run voice agent in separate thread with its own event loop"""
    global voice_agents
    
    # Create new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # Create voice agent for this specific user
        voice_agent = VoiceAgent(
            industry=voice_agent_data.get("industry", "beanandbrew"),
            voiceModel=voice_agent_data.get("voiceModel", "aura-2-thalia-en"),
            voiceName=voice_agent_data.get("voiceName", ""),
            browser_audio=voice_agent_data.get("browserAudio", False),
        )
        
        # Set device IDs
        voice_agent.input_device_id = voice_agent_data.get("inputDeviceId")
        voice_agent.output_device_id = voice_agent_data.get("outputDeviceId")
        
        # Set WebSocket connection for communication
        voice_agent.set_websocket_connection(websocket_connection)
        voice_agent.set_loop(loop)
        
        # Store in dictionary by websocket ID
        voice_agents[websocket_id] = voice_agent
        logger.info(f"Voice agent created for session {websocket_id} (Total active: {len(voice_agents)})")
        
        # Run the voice agent
        loop.run_until_complete(voice_agent.run())
        
    except Exception as e:
        logger.error(f"Error in voice agent thread: {e}")
    finally:
        # Clear this user's voice agent when done
        if websocket_id in voice_agents:
            del voice_agents[websocket_id]
        logger.info(f"Voice agent cleared for session {websocket_id} (Total active: {len(voice_agents)})")
        
        # Clean up the loop
        try:
            # Cancel all running tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            
            # Allow cancelled tasks to complete
            if pending:
                loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
            
            loop.run_until_complete(loop.shutdown_asyncgens())
        finally:
            loop.close()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for client communication"""
    global voice_agents
    
    # Get unique ID for this websocket connection
    websocket_id = id(websocket)
    
    await manager.connect(websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "start_voice_agent":
                # Start voice agent in separate thread
                logger.info(f"🎙️ Starting voice agent for session {websocket_id}...")
                
                # Check if this user already has a voice agent
                if websocket_id not in voice_agents:
                    data_dict = message.get("data", {})
                    
                    # Submit voice agent to thread pool executor
                    future = voice_agent_executor.submit(
                        run_voice_agent_in_thread, 
                        data_dict, 
                        websocket,
                        websocket_id
                    )
                else:
                    logger.warning(f"Voice agent already running for session {websocket_id}")
                    
            elif message.get("type") == "stop_voice_agent":
                # Stop voice agent for this user
                logger.info(f"🛑 Stopping voice agent for session {websocket_id}...")
                if websocket_id in voice_agents:
                    voice_agent = voice_agents[websocket_id]
                    # Trigger shutdown event in the voice agent
                    voice_agent.is_running = False
                    voice_agent._shutdown_event.set()
                    
            elif message.get("type") == "audio_data":
                # Handle audio data from browser for this user
                if websocket_id in voice_agents:
                    voice_agent = voice_agents[websocket_id]
                    if voice_agent.is_running and voice_agent.browser_audio:
                        try:
                            # Get the audio buffer and sample rate
                            audio_buffer = message.get("audio")
                            sample_rate = message.get("sampleRate", 44100)

                            if audio_buffer:
                                try:
                                    # Convert the audio data to bytes
                                    if isinstance(audio_buffer, str):
                                        # Frontend sends base64 encoded audio data
                                        audio_bytes = base64.b64decode(audio_buffer)
                                    elif isinstance(audio_buffer, memoryview):
                                        # Convert memoryview to bytes
                                        audio_bytes = audio_buffer.tobytes()
                                    elif isinstance(audio_buffer, bytes):
                                        # Already bytes, use directly
                                        audio_bytes = audio_buffer
                                    else:
                                        # Unexpected type, try to convert and log a warning
                                        logger.warning(
                                            f"Unexpected audio buffer type: {type(audio_buffer)}"
                                        )
                                        try:
                                            audio_bytes = bytes(audio_buffer)
                                        except Exception as e:
                                            logger.error(
                                                f"Failed to convert audio buffer to bytes: {e}"
                                            )
                                            return

                                    # Log the first time we receive audio data
                                    if not hasattr(handle_audio_data, "first_log_done"):
                                        logger.debug(
                                            f"Received first browser audio chunk: {len(audio_bytes)} bytes, sample rate: {sample_rate}Hz"
                                        )
                                        handle_audio_data.first_log_done = True

                                    # Put the audio data in the queue for processing
                                    if voice_agent.loop and not voice_agent.loop.is_closed():
                                        asyncio.run_coroutine_threadsafe(
                                            voice_agent.mic_audio_queue.put(audio_bytes),
                                            voice_agent.loop,
                                        )
                                except Exception as e:
                                    logger.error(
                                        f"Error converting audio buffer: {e}, type: {type(audio_buffer)}"
                                    )
                                    import traceback
                                    logger.error(traceback.format_exc())
                        except Exception as e:
                            logger.error(f"Error processing browser audio data: {e}")

    except WebSocketDisconnect:
        logger.info("Client disconnected")
        manager.disconnect(websocket)
    except asyncio.CancelledError:
        # Handle cancellation gracefully during shutdown
        logger.info("WebSocket operation cancelled during shutdown")
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


def handle_audio_data(data):
    """Handle audio data from browser - placeholder function for hasattr check"""
    pass


def cleanup_voice_agent_executor():
    """Clean up the voice agent thread pool executor"""
    global voice_agent_executor
    if voice_agent_executor:
        voice_agent_executor.shutdown(wait=True)
        logger.info("Voice agent thread pool executor shutdown complete")


# Register cleanup function
atexit.register(cleanup_voice_agent_executor)


# Serve frontend - catch-all route for SPA (must be last)
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve the frontend application"""
    static_dir = Path(__file__).parent / "static"
    
    # If static directory doesn't exist, return API info
    if not static_dir.exists():
        return {
            "message": "Frontend not built yet",
            "instructions": "Run 'npm run build' in the frontend directory"
        }
    
    # Try to serve the requested file
    file_path = static_dir / full_path
    if file_path.is_file():
        return FileResponse(file_path)
    
    # For all other routes, serve index.html (SPA routing)
    index_path = static_dir / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    
    return {"error": "Frontend not found"}


# Run with: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
