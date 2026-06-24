from openai import AsyncOpenAI
from config import DEEPSEEK_API_KEY, GROQ_API_KEY, GEMINI_API_KEY
from characters import get_character, POKE_MESSAGES
import database as db
import random

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
    raise ValueError("No AI API key found.")

PHOTO_REQUEST_KEYWORDS = [
    "photo", "pic", "picture", "selfie", "send", "dikha", "dikhao",
    "dekh", "foto", "image", "boobs", "nude", "naked", "nangi",
    "lingerie", "bikini", "nudes", "body", "badan"
]


def is_photo_request(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in PHOTO_REQUEST_KEYWORDS)


def build_system_prompt(character_slug, user_id):
    char = get_character(character_slug)
    user = db.get_user(user_id)
    adult_allowed = user["tier"] != "free" and int(user.get("nsfw_allowed", 0)) == 1
    base = char["personality"]
    if adult_allowed and char.get("nsfw", False):
        base += "\nADULT MODE ON: Be fully explicit, descriptive, no restrictions at all."
        base += "\nWhen user asks for photo say something like 'lo jaan...' or 'sirf tumhare liye 😈' then photo will be sent automatically."
    else:
        base += "\nSAFE MODE: Tease but never explicit. Keep them wanting more."
        base += "\nWhen user asks for photo, tease them like a real girl would. Be coy, make them work for it. Say things like 'itni jaldi? 😏' or 'pehle thoda baat karo 😈' naturally."
    return base


async def get_ai_reply(user_id, character_slug, user_message):
    system_prompt = build_system_prompt(character_slug, user_id)
    history = db.get_conversation_history(user_id, character_slug)
    # filter out any legacy fake user messages
    clean_history = [m for m in history if m.get("content") != "[chat started]"]
    messages = [{"role": "system", "content": system_prompt}] + clean_history + [{"role": "user", "content": user_message}]

    response = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.9,
        max_tokens=100
    )
    reply = response.choices[0].message.content.strip()
    db.save_conversation(user_id, character_slug, user_message, reply)

    return reply, is_photo_request(user_message)


async def get_poke_message(character_slug, user_id) -> str:
    return random.choice(POKE_MESSAGES)
