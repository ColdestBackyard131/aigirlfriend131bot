from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, PreCheckoutQueryHandler, filters
)
from telegram.request import HTTPXRequest
from dotenv import load_dotenv
load_dotenv()

import logging
import time
import random

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO
)
from config import TELEGRAM_TOKEN, ADMIN_ID
from characters import get_character, get_all_characters
import database as db
import ai_chat
import image_gen
from payments import subscribe_command, buy_callback, pre_checkout, successful_payment, SUBSCRIPTION_TEXT
from utils import age_gate, age_confirm_callback

# photo prompts per character
PHOTO_PROMPTS = {
    "kriti": {
        "sfw":    ["beautiful indian girl smiling, casual outfit", "pretty indian girl in kurta"],
        "bikini": ["beautiful indian girl in bikini at beach", "indian girl in swimsuit"],
        "lingerie": ["indian girl in lingerie, boudoir photo", "beautiful indian girl in sexy lingerie"],
        "nude":   ["beautiful indian girl nude, artistic photo"]
    },
    "naina": {
        "sfw":    ["pretty delhi girl casual outfit selfie", "indian college girl smiling"],
        "bikini": ["indian girl in bikini poolside", "pretty girl in swimwear"],
        "lingerie": ["indian girl in lingerie bedroom", "sexy indian girl in lingerie"],
        "nude":   ["beautiful indian girl nude artistic"]
    },
    "sara": {
        "sfw":    ["confident beautiful indian girl", "stylish indian girl outfit"],
        "bikini": ["sexy indian girl in bikini", "indian model in swimsuit"],
        "lingerie": ["dominant indian girl in lingerie", "sexy girl in black lingerie"],
        "nude":   ["beautiful indian girl nude artistic"]
    }
}

MORNING_CAPTIONS = [
    "Good morning jaan ☀️ aaj ka din tumhara ho 😘",
    "Uthh jao baby 😈 main already tayaar hoon",
    "Good morning ☀️ miss kar rahi thi tumhe 🙈",
]

NIGHT_CAPTIONS = [
    "Good night jaan 🌙 sapne mein milte hain 💋",
    "Sone ja rahi hoon... akele 😢 good night baby",
    "Good night 🌙 kal milte hain 😘",
]


async def send_photo_to_user(bot, user_id, active_char, user, caption):
    is_paid = user["tier"] != "free"
    nsfw = is_paid and int(user.get("nsfw_allowed", 0)) == 1
    prompts = PHOTO_PROMPTS.get(active_char, PHOTO_PROMPTS["kriti"])
    category = random.choice(["bikini", "lingerie"]) if nsfw else "sfw"
    prompt = random.choice(prompts[category])
    try:
        img_bytes = await image_gen.generate_image(prompt, nsfw=nsfw)
        await bot.send_photo(chat_id=user_id, photo=img_bytes, caption=caption)
    except:
        pass


async def send_photo_on_request(update, user_id, active_char, user):
    is_paid = user["tier"] != "free"
    nsfw = is_paid and int(user.get("nsfw_allowed", 0)) == 1
    if not is_paid:
        return  # free users don't get photos on demand
    prompts = PHOTO_PROMPTS.get(active_char, PHOTO_PROMPTS["kriti"])
    category = random.choice(["bikini", "lingerie", "nude"]) if nsfw else "bikini"
    prompt = random.choice(prompts[category])
    captions = [
        "sirf tumhare liye 💋",
        "lo jaan 😈",
        "kaisa laga? 😏",
        "iske baad kuch bolna hai? 🔥",
        "abhi khush? 😘"
    ]
    try:
        img_bytes = await image_gen.generate_image(prompt, nsfw=nsfw)
        await update.message.reply_photo(photo=img_bytes, caption=random.choice(captions))
    except:
        pass


last_message_time = {}


async def start(update: Update, context):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username)
    keyboard = [
        [InlineKeyboardButton(c["name"], callback_data=f"char_{slug}")]
        for slug, c in get_all_characters().items()
    ]
    await update.message.reply_text("Choose your companion 👇", reply_markup=InlineKeyboardMarkup(keyboard))


async def char_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    slug = query.data.replace("char_", "")
    user_id = query.from_user.id
    char = get_character(slug)
    db.update_user(user_id, active_char=slug)

    existing_history = db.get_conversation_history(user_id, slug)

    if not existing_history:
        await query.edit_message_text(f"💬 New chat with {char['name']} started!")
        await query.message.reply_text(char["greeting"])
        # seed history with only the assistant greeting, no fake user message
        db.seed_greeting(user_id, slug, char["greeting"])
    else:
        last_assistant = next(
            (m["content"] for m in reversed(existing_history) if m["role"] == "assistant"), ""
        )
        await query.edit_message_text(
            f"Welcome back! Continuing with {char['name']} 💬\n\n{char['name']}: {last_assistant}"
        )


async def handle_message(update: Update, context):
    user_id = update.effective_user.id
    logging.info(f"Message from {user_id}: {update.message.text[:30]}")
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("Use /start first.")
        return

    last_message_time[user_id] = time.time()

    active_char = user["active_char"]
    if not active_char:
        await update.message.reply_text("Choose a companion first 👇", reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton(c["name"], callback_data=f"char_{slug}")] for slug, c in get_all_characters().items()]
        ))
        return

    if user["tier"] == "free":
        if int(user["msg_credits"]) <= 0:
            keyboard = [
                [InlineKeyboardButton("💕 Crush — 100 ⭐", callback_data="buy_crush")],
                [InlineKeyboardButton("🫦 Fling — 500 ⭐", callback_data="buy_fling")],
                [InlineKeyboardButton("❤️🔥 Fantasy — 1000 ⭐", callback_data="buy_fantasy")],
            ]
            await update.message.reply_text(
                SUBSCRIPTION_TEXT,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        db.decrement_message_credit(user_id)

    # show typing indicator while AI is thinking
    await context.bot.send_chat_action(chat_id=user_id, action="typing")

    # retry up to 3 times if API fails
    reply = None
    for attempt in range(3):
        try:
            reply, is_photo_req = await ai_chat.get_ai_reply(user_id, active_char, update.message.text)
            break
        except Exception as e:
            print(f"[ERROR] Attempt {attempt+1} failed: {e}")
            if attempt < 2:
                await context.bot.send_chat_action(chat_id=user_id, action="typing")
                import asyncio
                await asyncio.sleep(2)

    if not reply:
        # silent retry failed — just ignore, don't show error to user
        return

    await update.message.reply_text(reply)

    if is_photo_req:
        is_paid = user["tier"] != "free"
        if is_paid:
            await send_photo_on_request(update, user_id, active_char, user)
        else:
            keyboard = [
                [InlineKeyboardButton("💕 Crush — 100 ⭐", callback_data="buy_crush")],
                [InlineKeyboardButton("🫦 Fling — 500 ⭐ (Popular)", callback_data="buy_fling")],
                [InlineKeyboardButton("❤️🔥 Fantasy — 1000 ⭐ (Best)", callback_data="buy_fantasy")],
            ]
            await update.message.reply_text(
                SUBSCRIPTION_TEXT,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )


async def image_command(update: Update, context):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user or user["tier"] not in ["crush", "fling", "fantasy"]:
        await update.message.reply_text("🔒 Image generation is for subscribers only. Use /subscribe.")
        return
    if int(user["img_credits"]) <= 0:
        await update.message.reply_text("Image credits used up. Upgrade your plan!")
        return
    prompt = " ".join(context.args) if context.args else "a beautiful indian girl"
    nsfw_allowed = int(user.get("nsfw_allowed", 0)) == 1
    img_bytes = await image_gen.generate_image(prompt, nsfw=nsfw_allowed)
    await update.message.reply_photo(photo=img_bytes, caption=f"🎨 {prompt}")
    db.decrement_image_credit(user_id)


async def stats(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    total_users = db.count_users()
    premium_users = db.count_premium()
    total_chats = db.count_conversations()
    await update.message.reply_text(
        f"📊 Stats:\n"
        f"👥 Users: {total_users}\n"
        f"💎 Paid: {premium_users}\n"
        f"💬 Chats: {total_chats}"
    )


async def freevip(update: Update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    target_id = user_id
    if context.args:
        target_id = int(context.args[0])
    db.set_subscription(target_id, "fantasy", days=36500)
    db.update_user(target_id, nsfw_allowed=1, age_verified=1)
    await update.message.reply_text(f"✅ Fantasy VIP activated for {target_id} forever!")


async def broadcast(update: Update, context):
    if update.effective_user.id != ADMIN_ID:
        return
    message = " ".join(context.args)
    for user in db.get_all_users():
        try:
            await context.bot.send_message(user["user_id"], message)
        except:
            pass
    await update.message.reply_text("✅ Broadcast sent.")


async def morning_photo(context):
    for user in db.get_all_users():
        user_id = int(user["user_id"])
        active_char = user.get("active_char")
        if not active_char:
            continue
        try:
            await send_photo_to_user(context.bot, user_id, active_char, user, random.choice(MORNING_CAPTIONS))
        except:
            pass


async def night_photo(context):
    for user in db.get_all_users():
        user_id = int(user["user_id"])
        active_char = user.get("active_char")
        if not active_char:
            continue
        try:
            await send_photo_to_user(context.bot, user_id, active_char, user, random.choice(NIGHT_CAPTIONS))
        except:
            pass


async def poke_inactive_users(context):
    now = time.time()
    for user in db.get_all_users():
        user_id = int(user["user_id"])
        active_char = user.get("active_char")
        if not active_char:
            continue
        last_time = last_message_time.get(user_id, 0)
        if last_time > 0 and (now - last_time) > 3600:
            try:
                poke_msg = await ai_chat.get_poke_message(active_char, user_id)
                await context.bot.send_message(user_id, poke_msg)
                last_message_time[user_id] = now
            except:
                pass


def main():
    import threading, os, signal
    # auto-exit at 55 min so Job B (started at :55) takes over
    threading.Timer(55 * 60, lambda: os.kill(os.getpid(), signal.SIGTERM)).start()

    request = HTTPXRequest(connect_timeout=30, read_timeout=30)
    app = Application.builder().token(TELEGRAM_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("subscribe", subscribe_command))
    app.add_handler(CommandHandler("image", image_command))
    app.add_handler(CommandHandler("verify", age_gate))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("freevip", freevip))
    app.add_handler(CommandHandler("broadcast", broadcast))

    app.add_handler(CallbackQueryHandler(char_callback, pattern="^char_"))
    app.add_handler(CallbackQueryHandler(buy_callback, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(age_confirm_callback, pattern="^age_confirm$"))

    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.job_queue.run_repeating(poke_inactive_users, interval=1800, first=1800)

    # morning photo at 8 AM IST (2:30 UTC)
    from datetime import time as dtime
    app.job_queue.run_daily(morning_photo, time=dtime(2, 30))
    # night photo at 11 PM IST (17:30 UTC)
    app.job_queue.run_daily(night_photo, time=dtime(17, 30))

    app.run_polling()


if __name__ == "__main__":
    main()
