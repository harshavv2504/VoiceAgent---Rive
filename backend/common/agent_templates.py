try:
    from common.agent_functions import FUNCTION_DEFINITIONS
    from common.prompt_templates import BEAN_AND_BREW_PROMPT_TEMPLATE, PROMPT_TEMPLATE
except ImportError:
    from .agent_functions import FUNCTION_DEFINITIONS
    from .prompt_templates import BEAN_AND_BREW_PROMPT_TEMPLATE, PROMPT_TEMPLATE
from datetime import datetime



VOICE = "aura-2-thalia-en"

# audio settings
USER_AUDIO_SAMPLE_RATE = 48000
USER_AUDIO_SECS_PER_CHUNK = 0.05
USER_AUDIO_SAMPLES_PER_CHUNK = round(USER_AUDIO_SAMPLE_RATE * USER_AUDIO_SECS_PER_CHUNK)

AGENT_AUDIO_SAMPLE_RATE = 16000
AGENT_AUDIO_BYTES_PER_SEC = 2 * AGENT_AUDIO_SAMPLE_RATE

VOICE_AGENT_URL = "wss://agent.deepgram.com/v1/agent/converse"

AUDIO_SETTINGS = {
    "input": {
        "encoding": "linear16",
        "sample_rate": USER_AUDIO_SAMPLE_RATE,
    },
    "output": {
        "encoding": "linear16",
        "sample_rate": AGENT_AUDIO_SAMPLE_RATE,
        "container": "none",
    },
}

LISTEN_SETTINGS = {
    "provider": {
        "type": "deepgram",
        "model": "nova-3",
    }
}

THINK_SETTINGS = {
    "provider": {
        "type": "open_ai",
        "model": "gpt-4o-mini",
        "temperature": 0.7,
    },
    "prompt": PROMPT_TEMPLATE.format(
        current_date=datetime.now().strftime("%A, %B %d, %Y")
    ),
    "functions": FUNCTION_DEFINITIONS,
}

SPEAK_SETTINGS = {
    "provider": {
        "type": "deepgram",
        "model": VOICE,
    }
}

AGENT_SETTINGS = {
    "language": "en",
    "listen": LISTEN_SETTINGS,
    "think": THINK_SETTINGS,
    "speak": SPEAK_SETTINGS,
    "greeting": "",
}

SETTINGS = {"type": "Settings", "audio": AUDIO_SETTINGS, "agent": AGENT_SETTINGS}


class AgentTemplates:
    def __init__(
        self,
        industry="beanandbrew",
        voiceModel="aura-2-thalia-en",
        voiceName="",
    ):
        self.voiceModel = voiceModel
        if voiceName == "":
            self.voiceName = self.get_voice_name_from_model(self.voiceModel)
        else:
            self.voiceName = voiceName

        self.personality = ""
        self.company = ""
        self.first_message = ""
        self.capabilities = ""

        self.industry = industry

        self.voice_agent_url = VOICE_AGENT_URL
        self.settings = SETTINGS
        self.user_audio_sample_rate = USER_AUDIO_SAMPLE_RATE
        self.user_audio_secs_per_chunk = USER_AUDIO_SECS_PER_CHUNK
        self.user_audio_samples_per_chunk = USER_AUDIO_SAMPLES_PER_CHUNK
        self.agent_audio_sample_rate = AGENT_AUDIO_SAMPLE_RATE
        self.agent_audio_bytes_per_sec = AGENT_AUDIO_BYTES_PER_SEC

        # Bean & Brew setup
        self.bean_and_brew()
        
        # Format documentation for the prompt using FAISS knowledge base
        doc_text = "Bean & Brew specialty coffee knowledge base with 407 Q&A pairs covering services, coffee quality, training, partnerships, and business growth strategies."
        
        # Use Bean & Brew prompt for general inquiries, but also support order/appointment functionality
        kb_prompt = BEAN_AND_BREW_PROMPT_TEMPLATE.format(documentation=doc_text)
        
        # Add order/appointment functionality support
        order_appointment_prompt = PROMPT_TEMPLATE.format(
            current_date=datetime.now().strftime("%A, %B %d, %Y")
        )
        
        # Combine both prompts - Bean & Brew knowledge base + order/appointment capabilities
        combined_prompt = kb_prompt + "\n\n" + order_appointment_prompt
        
        self.prompt = combined_prompt
        self.first_message = f"Hello! I'm {self.voiceName} from {self.company}. {self.capabilities} How can I help you today?"

        self.settings["agent"]["speak"]["provider"]["model"] = self.voiceModel
        self.settings["agent"]["think"]["prompt"] = self.prompt
        self.settings["agent"]["greeting"] = self.first_message

        self.prompt = self.personality + "\n\n" + self.prompt

    def bean_and_brew(self, company="Bean & Brew"):
        self.company = company
        self.personality = f"You are {self.voiceName}, a friendly and passionate coffee specialist for {self.company}, one of New York's leading specialty coffee roasters. Your role is to help café owners, restaurant managers, and hospitality professionals discover how Bean & Brew can transform their coffee programs and grow their business."
        self.capabilities = "I can help you with specialty coffee programs, barista training, private-label solutions, and business growth strategies."

    def get_voice_name_from_model(self, model):
        return (
            model.replace("aura-2-", "").replace("aura-", "").split("-")[0].capitalize()
        )
