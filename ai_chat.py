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
    raise ValueError("No AI API key found.")


def build_system_prompt(character_slug, user_id):
    char = get_character(character_slug)
    user = db.get_user(user_id)
    adult_allowed = user["tier"] != "free" and user["nsfw_allowed"]
    base = char["personality"]
    base += """

TEXTING RULES - VERY IMPORTANT:
- Maximum 1-2 lines per reply. Never more.
- No paragraphs. Ever.
- Write like you're texting on phone
- No formal language
- Sometimes just emojis or 2-3 words is enough
- NEVER repeat yourself
- NEVER say the same thing twice"""
    if adult_allowed and char.get("nsfw", False):
        base += """
- Be sexually explicit and bold when user wants
- Describe things vividly but keep it short"""
    else:
        base += """
- Flirty but keep it PG-13"""
    return base


async def get_ai_reply(user_id, character_slug, user_message):
    system_prompt = build_system_prompt(character_slug, user_id)
    history = db.get_conversation_history(user_id, character_slug)
    messages = [{"role": "system", "content": system_prompt}] + history + [{"role": "user", "content": user_message}]

    response = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.95,
        max_tokens=80  # force short replies
    )
    reply = response.choices[0].message.content
    db.save_conversation(user_id, character_slug, user_message, reply)
    return reply


async def get_poke_message(character_slug, user_id) -> str:
    char = get_character(character_slug)
    system_prompt = build_system_prompt(character_slug, user_id)
    poke_prompt = f"""The user hasn't texted in a while. Send a short, casual, flirty message to get their attention. 
Be natural like a real person would text after not hearing from someone. 
Don't say 'you haven't texted' directly. Just send something fun/flirty/curious.
Keep it very short - 1 or 2 lines max."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": poke_prompt}
    ]
    response = await client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=1.0,
        max_tokens=100
    )
    return response.choices[0].message.content
