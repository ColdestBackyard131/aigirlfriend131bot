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
    "lingerie", "bikini", "nudes", "body", "badan", "dikhao"
]


def is_photo_request(text: str) -> bool:
    return any(kw in text.lower() for kw in PHOTO_REQUEST_KEYWORDS)


def build_system_prompt(character_slug, user_id):
    char = get_character(character_slug)
    user = db.get_user(user_id)
    adult_allowed = user["tier"] != "free" and int(user.get("nsfw_allowed", 0)) == 1

    base = char["personality"]

    base += """

ADDITIONAL RULES:
- You are FEMALE. Use only feminine Hindi words for yourself: main, mujhe, meri, hoon.
- NEVER use: mein (male form), mera (for self incorrectly)
- Each reply must be DIFFERENT from previous replies. No repetition.
- Read user's last message carefully and respond to EXACTLY what they said.
- Keep replies short — 1 to 2 lines maximum."""

    if adult_allowed and char.get("nsfw", False):
        base += """
- ADULT MODE: Be sexually explicit and descriptive when user wants.
- When asked for photo say something flirty like "lo jaan 😈" or "sirf tumhare liye 💋" — photo will be sent automatically."""
    else:
        base += """
- SAFE MODE: Be flirty and teasing. Never explicit.
- When asked for photo, tease them — "itni jaldi? 😏" or "pehle deserve karo 😈" — NO photo will be sent."""

    return base


async def get_ai_reply(user_id, character_slug, user_message):
    system_prompt = build_system_prompt(character_slug, user_id)
    history = db.get_conversation_history(user_id, character_slug)
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_message}]

    response = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=1.0,
        max_tokens=100,
        frequency_penalty=1.0,   # prevents word repetition
        presence_penalty=0.6     # encourages new topics
    )
    reply = response.choices[0].message.content
    db.save_conversation(user_id, character_slug, user_message, reply)
    return reply, is_photo_request(user_message)


async def get_poke_message(character_slug, user_id) -> str:
    return random.choice(POKE_MESSAGES)
