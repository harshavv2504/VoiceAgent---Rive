# Voice Agent Application Documentation

This document provides a comprehensive overview of the Voice Agent application's architecture, components, and key "endpoints" for dynamic control.

## Project Structure

The application is organized into a clear and logical file structure:

```
.
├── components/
│   ├── MicButton.tsx           # The mute/unmute control button.
│   ├── ParticleBackground.tsx  # The dynamic, audio-reactive background.
│   └── StartStopButton.tsx     # The master button to control the WebSocket connection.
├── hooks/
│   ├── useAudioRecorder.ts     # Custom hook to manage microphone input and audio analysis.
│   └── useWebSocket.ts         # Custom hook to manage the WebSocket lifecycle.
├── types.ts                    # Shared TypeScript types and enums.
├── App.tsx                     # The main application component, state management, and layout.
├── index.html                  # The main HTML entry point.
├── index.tsx                   # The React application entry point.
├── metadata.json               # Application metadata and permissions.
└── documentation.md            # This documentation file.
```

---

## Architecture Overview

The application is driven by a **WebSocket connection**. The `StartStopButton` acts as the master control, initiating and terminating the WebSocket session. The audio recorder and its associated visual effects are synchronized with the WebSocket's state: they become active when the connection is open and deactivate when it is closed.

---

## Core Logic & Hooks

### 1. `useWebSocket` Hook (within `hooks/useWebSocket.ts`)

This custom hook is the brain of the connection management.

-   **Responsibilities:**
    1.  **State Management:** Manages the `connectionState` lifecycle (`CONNECTING`, `OPEN`, `CLOSING`, `CLOSED`).
    2.  **Connection Handling:** Encapsulates the `WebSocket` API to connect, disconnect, and handle events (`onopen`, `onmessage`, `onerror`, `onclose`).
    3.  **Exposing Controls:** Returns a `toggleConnection` function that serves as the primary endpoint for user control.

### 2. `useAudioRecorder` Hook (within `hooks/useAudioRecorder.ts`)

This custom hook encapsulates all logic related to microphone interaction and audio analysis. It acts as a slave to the `useWebSocket` hook.

-   **Responsibilities:**
    1.  **Microphone Access:** Handles `navigator.mediaDevices.getUserMedia`.
    2.  **Audio Analysis:** Uses the Web Audio API to calculate `audioLevel` and `bassLevel` for visualizations.
    3.  **Error Handling:** Manages microphone permission errors.
    4.  **Exposing Controls:** Returns `startRecording` and `stopRecording` functions that are now called programmatically based on the WebSocket's state.

---

## Components

### 1. `StartStopButton.tsx`

The central control for starting and stopping the WebSocket session.

-   **Role:** Provides a clear visual indicator of the WebSocket's `connectionState` and captures user clicks to toggle the connection.

### 2. `MicButton.tsx`

The control for muting and unmuting the microphone while a session is active.

-   **Role:** Allows the user to temporarily mute their audio input without disconnecting the session. It is disabled when the audio recorder is not active.

---

## Key Endpoints

### 1. Primary User Control (Start/Stop Button)

The `toggleConnection` function, returned by the `useWebSocket` hook, is the single entry point for the user's manual control via the `StartStopButton`. It checks the current `connectionState` and either initiates a new WebSocket connection or closes the existing one.

### 2. Programmatic Recording Control

The audio recorder is controlled programmatically within `App.tsx` by an effect that watches the `connectionState`.
-   **`startRecording()`**: Called automatically when `connectionState` becomes `OPEN`.
-   **`stopRecording()`**: Called automatically when `connectionState` becomes `CLOSED` or `ERROR`.

### 3. Endpoint: Displaying Dynamic Text from the Backend

The main text container in the UI is designed to display messages sent from the backend server. **This is the primary method for the voice agent to communicate with the user.**

-   **Current State:** The container is initialized with dummy placeholder text: *"The agent's response will appear here once connected..."*
-   **Connection Point:** The official connecting point is the `onMessage` callback passed to the `useWebSocket` hook within `App.tsx`. Any data received from the WebSocket server triggers this callback.
-   **How it Works:** The `handleWebSocketMessage` function in `App.tsx` receives the data from the server and calls `setDisplayText` to update the UI.

#### How to Connect Your Backend:

To display text, your backend simply needs to send a message over the established WebSocket connection. The frontend is already configured to listen for and display these messages.

**Example Implementation (`App.tsx`):**
```tsx
// In App.tsx

// 1. This state holds the text for the display container.
// It is initialized with dummy text.
const [displayText, setDisplayText] = useState<string>(
  "The agent's response will appear here once connected..."
);

// 2. This function is the connection point. It's called when the WebSocket receives a message.
const handleWebSocketMessage = useCallback((data: string) => {
  // The 'data' variable contains the raw message from your server.
  // TODO: Update this logic if you need to parse JSON or handle complex message types.
  setDisplayText(data);
}, []);

// 3. The callback is passed to the WebSocket hook, establishing the connection.
const { connectionState, toggleConnection } = useWebSocket({
  onMessage: handleWebSocketMessage,
});

// The UI component simply renders the state:
// <p>{displayText}</p>
```
---
