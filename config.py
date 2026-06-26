import os
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("BOT_TOKEN", "")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_API_KEY_2 = os.getenv("GROQ_API_KEY_2", "")
GROQ_API_KEY_3 = os.getenv("GROQ_API_KEY_3", "")
GROQ_API_KEY_4 = os.getenv("GROQ_API_KEY_4", "")
GROQ_API_KEY_5 = os.getenv("GROQ_API_KEY_5", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY", "")
CEREBRAS_API_KEY_2 = os.getenv("CEREBRAS_API_KEY_2", "")
CEREBRAS_API_KEY_3 = os.getenv("CEREBRAS_API_KEY_3", "")
SAMBANOVA_API_KEY = os.getenv("SAMBANOVA_API_KEY", "")
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
STABLE_HORDE_API_KEY = os.getenv("STABLE_HORDE_API_KEY", "0000000000")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
TURSO_URL = os.getenv("TURSO_URL", "")
TURSO_TOKEN = os.getenv("TURSO_TOKEN", "")

FREE_CREDITS = 10
SUBSCRIPTION_PRICE = 499
