# System-Level README

## 1. System Overview
This system is a real-time voice AI agent designed for "Bean & Brew", a coffee shop business. It handles customer interactions via voice, capable of managing appointments, orders, customer accounts, and answering domain-specific questions using a knowledge base.

Technically, it is a WebSocket-based full-duplex audio streaming application that orchestrates communication between a web frontend, the Deepgram Voice Agent API, and a local backend for business logic and data persistence.

## 2. High-Level Architecture

### Components
*   **Frontend (Static SPA)**: A web interface (served via FastAPI) that captures microphone input and plays back audio. It communicates with the backend via WebSocket.
*   **Backend (FastAPI)**: The core orchestration layer.
    *   **WebSocket Manager**: Handles client connections.
    *   **Voice Agent**: Manages the session with Deepgram, handles audio buffering, and processes function calls.
    *   **Audio Handler**: Utilities for audio device management (though primarily browser-based audio is used).
*   **AI Service (Deepgram)**: External API providing Speech-to-Text (STT), Large Language Model (LLM) processing, and Text-to-Speech (TTS) in a low-latency pipeline.
*   **Persistence (MongoDB)**: Stores customer data, appointment schedules, order history, and conversation logs.
*   **Knowledge Base (RAG)**: A local vector search system using `sentence-transformers` and FAISS (implied) to retrieve relevant context for user queries.

### Responsibilities
*   **Frontend**: Audio capture/playback, UI state.
*   **Backend**: Authentication (API keys), session management, tool execution (business logic), database operations, RAG retrieval.
*   **Deepgram**: Voice activity detection, transcription, intent understanding, response generation, audio synthesis.

## 3. Execution Flow

1.  **Connection**: Client connects to `wss://<host>/ws`. Backend establishes a corresponding WebSocket connection to Deepgram.
2.  **Audio Streaming**:
    *   **Inbound**: Browser sends raw audio chunks -> Backend -> Deepgram.
    *   **Outbound**: Deepgram sends audio chunks -> Backend -> Browser -> Web Audio API.
3.  **Interaction Loop**:
    *   User speaks -> Deepgram detects VAD & Transcribes.
    *   LLM processes text.
    *   **If Tool Needed**: Deepgram sends `FunctionCallRequest` -> Backend executes function (e.g., `find_customer`, `search_knowledge_base`) -> Backend returns result -> Deepgram incorporates result.
    *   Deepgram generates response text -> TTS synthesizes audio -> Streamed to client.
4.  **Termination**: Session ends via user intent ("Goodbye"), timeout, or connection loss.

## 4. AI / Model Integration

### Models
*   **Voice/LLM**: Managed by Deepgram (configurable via `VoiceAgent` templates, default `aura-2-thalia-en`).
*   **Embeddings**: `sentence-transformers` (local) for knowledge base retrieval.

### Tools (Function Calling)
The system exposes specific Python functions to the LLM via a JSON schema definition. Key tools include:
*   `find_customer`, `create_customer_account`: Identity management.
*   `get_appointments`, `create_appointment`, `reschedule_appointment`, `cancel_appointment`: Scheduling logic.
*   `get_orders`: E-commerce/POS integration.
*   `search_knowledge_base`, `get_best_answer`: RAG retrieval for domain questions.
*   `check_availability`: Calendar logic.

### Flow Control
*   **System Prompt**: Defined in `agent_templates.py` (not shown but implied), setting the persona and constraints.
*   **Filler Messages**: `agent_filler` tool allows the agent to speak ("Let me check that...") while performing high-latency lookups.

## 5. State & Persistence

### Database (MongoDB)
State is persisted in a MongoDB instance (`bean_and_brew` database).
*   **Collections**:
    *   `customers`: Profile data (Name, Phone, Email).
    *   `appointments`: Scheduling data (Date, Service, Status).
    *   `orders`: Transaction history.
    *   `conversations`: Full logs of interaction sessions.

### Runtime State
*   **VoiceAgent Instance**: Exists per WebSocket connection. Stores thread-safe queues for audio and connection status.
*   **Global State**: `voice_agents` dictionary maps WebSocket IDs to active agent instances.

## 6. API Surface

### HTTP Endpoints
*   `GET /api`: System status and endpoint listing.
*   `GET /health`: Health check for container orchestration.
*   `GET /audio-devices`: List server-side audio devices (mostly for debug/local dev).
*   `GET /*`: Serves the frontend static assets.

### WebSocket
*   `/ws`: The primary control and data plane.
    *   **Input**: JSON control messages (`start_voice_agent`, `stop_voice_agent`) and binary/base64 audio data.
    *   **Output**: JSON status updates (`conversation_update`, `voice_agent_stopped`) and binary audio data.

## 7. Error Handling & Reliability
*   **Graceful Shutdown**: `atexit` handlers ensure thread pools are cleaned up.
*   **Connection Resilience**: Timeouts implemented for WebSocket closures to prevent hanging threads.
*   **Fallback**: If MongoDB is unavailable, the system logs a warning and operates in a degraded mode (DB operations will fail safely).
*   **Concurrency**: Each user session runs in its own thread via `ThreadPoolExecutor` to ensure non-blocking audio processing.

## 8. Security & Configuration
*   **Environment Variables**:
    *   `DEEPGRAM_API_KEY`: Required for AI services.
    *   `MONGODB_URI`: Database connection string.
*   **CORS**: Currently set to allow all origins (`*`). **Production Note**: Must be restricted to trusted domains.
*   **Auth**: No user authentication on the WebSocket endpoint itself; relies on network-level security or upstream gateways.

## 9. Deployment & Runtime Considerations
*   **Containerization**: Dockerfile present.
*   **Audio**: Browser-based audio capture is preferred over server-side audio to avoid ALSA/driver issues in containerized environments.
*   **Threading**: Uses `asyncio` for I/O bound tasks and `ThreadPoolExecutor` for managing concurrent agent sessions.

## 10. Known Limitations & Future Improvements
*   **Scalability**: In-memory `voice_agents` dictionary limits scaling to a single instance. Redis would be needed for multi-node deployments.
*   **Security**: Lack of authentication on the WebSocket endpoint.
*   **Audio Codecs**: Currently assumes raw PCM/bytes; robust handling for various codecs (Opus, etc.) is handled by Deepgram but frontend capture must match.
