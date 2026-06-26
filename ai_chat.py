from openai import AsyncOpenAI
from config import (DEEPSEEK_API_KEY, GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3,
    GROQ_API_KEY_4, GROQ_API_KEY_5, GEMINI_API_KEY, GEMINI_API_KEY_2,
    CEREBRAS_API_KEY, CEREBRAS_API_KEY_2, CEREBRAS_API_KEY_3,
    SAMBANOVA_API_KEY, MISTRAL_API_KEY)
from characters import get_character, POKE_MESSAGES
import database as db
import random

GROQ_KEYS = [k for k in [GROQ_API_KEY, GROQ_API_KEY_2, GROQ_API_KEY_3, GROQ_API_KEY_4, GROQ_API_KEY_5] if k]

# collect all available keys with their configs
CLIENTS = []
for key in GROQ_KEYS:
    CLIENTS.append({"key": key, "base_url": "https://api.groq.com/openai/v1", "model": "llama-3.3-70b-versatile"})
CEREBRAS_KEYS = [k for k in [CEREBRAS_API_KEY, CEREBRAS_API_KEY_2, CEREBRAS_API_KEY_3] if k]
for key in CEREBRAS_KEYS:
    CLIENTS.append({"key": key, "base_url": "https://api.cerebras.ai/v1", "model": "llama-3.3-70b"})
if SAMBANOVA_API_KEY:
    CLIENTS.append({"key": SAMBANOVA_API_KEY, "base_url": "https://api.sambanova.ai/v1", "model": "Meta-Llama-3.1-70B-Instruct"})
if MISTRAL_API_KEY:
    CLIENTS.append({"key": MISTRAL_API_KEY, "base_url": "https://api.mistral.ai/v1", "model": "mistral-small-latest"})
GEMINI_KEYS = [k for k in [GEMINI_API_KEY, GEMINI_API_KEY_2] if k]
for key in GEMINI_KEYS:
    CLIENTS.append({"key": key, "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/", "model": "gemini-2.0-flash"})
if DEEPSEEK_API_KEY:
    CLIENTS.append({"key": DEEPSEEK_API_KEY, "base_url": "https://api.deepseek.com", "model": "deepseek-chat"})

if not CLIENTS:
    raise ValueError("No AI API key found.")

current_index = 0


def get_client():
    global current_index
    c = CLIENTS[current_index % len(CLIENTS)]
    current_index += 1
    return AsyncOpenAI(api_key=c["key"], base_url=c["base_url"]), c["model"]

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

    # try each client in rotation until one works
    for _ in range(len(CLIENTS)):
        client, MODEL = get_client()
        try:
            response = await client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=1.0,
                max_tokens=100
            )
            reply = response.choices[0].message.content
            db.save_conversation(user_id, character_slug, user_message, reply)
            return reply, is_photo_request(user_message)
        except Exception as e:
            print(f"[WARN] {MODEL} failed: {e} — trying next provider")
            continue

    raise Exception("All AI providers failed")


async def get_poke_message(character_slug, user_id) -> str:
    return random.choice(POKE_MESSAGES)
