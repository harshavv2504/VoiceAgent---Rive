/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_WEBSOCKET_URL: string
  readonly VITE_VOICE_MODEL: string
  readonly VITE_VOICE_NAME: string
  readonly VITE_BUSINESS_NAME: string
  readonly GEMINI_API_KEY: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
