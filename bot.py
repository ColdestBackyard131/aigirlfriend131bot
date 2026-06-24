from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, PreCheckoutQueryHandler, filters,
    JobQueue
)
from telegram.request import HTTPXRequest
from dotenv import load_dotenv
load_dotenv()

import time
from config import TELEGRAM_TOKEN, ADMIN_ID
from characters import get_character, get_all_characters
import database as db
import ai_chat
import image_gen
from payments import subscribe_command, buy_callback, pre_checkout, successful_payment
from utils import age_gate, age_confirm_callback

# track last message time per user
last_message_time = {}


async def start(update: Update, context):
    user = update.effective_user
    db.get_or_create_user(user.id, user.username)
    keyboard = [
        [InlineKeyboardButton(c["name"], callback_data=f"char_{slug}")]
        for slug, c in get_all_characters().items()
    ]
    await update.message.reply_text("👋 Choose your character:", reply_markup=InlineKeyboardMarkup(keyboard))


async def char_callback(update: Update, context):
    query = update.callback_query
    slug = query.data.replace("char_", "")
    user_id = query.from_user.id
    char = get_character(slug)
    db.update_user(user_id, active_char=slug)
    await query.edit_message_text(f"🎭 Now chatting with *{char['name']}*\n\n{char['greeting']}", parse_mode="Markdown")


async def handle_message(update: Update, context):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("Please use /start first.")
        return

    last_message_time[user_id] = time.time()

    if user["tier"] == "free":
        if user["msg_credits"] <= 0:
            await update.message.reply_text("💸 Free limit reached. Use /subscribe to continue!")
            return
        db.decrement_message_credit(user_id)

    active_char = user["active_char"]
    if not active_char:
        await update.message.reply_text("Please select a character first using /start")
        return

    reply = await ai_chat.get_ai_reply(user_id, active_char, update.message.text)
    await update.message.reply_text(reply)


async def image_command(update: Update, context):
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user or user["tier"] not in ["premium", "vip"]:
        await update.message.reply_text("🔒 Image generation is for subscribers only. Use /subscribe.")
        return
    if user["img_credits"] <= 0:
        await update.message.reply_text("You've used your daily image credits. Upgrade for more!")
        return

    prompt = " ".join(context.args) if context.args else "a beautiful anime girl"
    nsfw_allowed = user["nsfw_allowed"] and user["tier"] != "free"
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
        f"👥 Total users: {total_users}\n"
        f"💎 Premium users: {premium_users}\n"
        f"💬 Total conversations: {total_chats}"
    )


async def freevip(update: Update, context):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
    target_id = user_id
    if context.args:
        target_id = int(context.args[0])
    db.set_subscription(target_id, "vip", days=36500)
    db.update_user(target_id, nsfw_allowed=1, age_verified=1)
    await update.message.reply_text(f"✅ VIP activated for {target_id} forever!")


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


async def poke_inactive_users(context):
    now = time.time()
    for user in db.get_all_users():
        user_id = int(user["user_id"])
        active_char = user.get("active_char")
        if not active_char:
            continue
        last_time = last_message_time.get(user_id, 0)
        # poke if inactive for 1-2 hours (randomly pick users)
        if last_time > 0 and (now - last_time) > 3600:
            try:
                poke_msg = await ai_chat.get_poke_message(active_char, user_id)
                await context.bot.send_message(user_id, poke_msg)
                last_message_time[user_id] = now  # reset so it doesn't spam
            except:
                pass


def main():
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

    # auto poke inactive users every 30 minutes
    app.job_queue.run_repeating(poke_inactive_users, interval=1800, first=1800)

    app.run_polling()


if __name__ == "__main__":
    main()
