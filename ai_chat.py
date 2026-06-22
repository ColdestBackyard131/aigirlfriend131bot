from openai import AsyncOpenAI
from config import DEEPSEEK_API_KEY, GROQ_API_KEY, GEMINI_API_KEY
from characters import get_character
import database as db

if GROQ_API_KEY:
    client = AsyncOpenAI(api_key=GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
    MODEL = "llama-3.3-70b-versatile"
elif DEEPSEEK_API_KEY:
    client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    MODEL = "deepseek-chat"
elif GEMINI_API_KEY:
    client = AsyncOpenAI(api_key=GEMINI_API_KEY, base_url="https://generativelanguage.googleapis.com/v1beta/openai/")
    MODEL = "gemini-1.5-flash"
else:
    raise ValueError("No AI API key found. Set GROQ_API_KEY, DEEPSEEK_API_KEY, or GEMINI_API_KEY in .env")


def build_system_prompt(character_slug, user_id):
    char = get_character(character_slug)
    user = db.get_user(user_id)
    adult_allowed = user["tier"] != "free" and user["nsfw_allowed"]
    base = char["personality"]
    if adult_allowed and char.get("nsfw", False):
        base += " The user has paid for adult content. You can engage in consensual sexual roleplay, use suggestive language, and describe intimate scenes. Always ask for consent and stay respectful."
    else:
        base += " You must NOT include any sexual or adult content. Keep all replies PG-13."
    return base


async def get_ai_reply(user_id, character_slug, user_message):
    system_prompt = build_system_prompt(character_slug, user_id)
    history = db.get_conversation_history(user_id, character_slug)
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_message}]

    response = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.8
    )
    reply = response.choices[0].message.content
    db.save_conversation(user_id, character_slug, user_message, reply)
    return reply
