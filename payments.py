import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
import database as db

TIERS = {
    "crush": {
        "stars": 100,
        "label": "💕 Crush",
        "description": "100 Messages • 10 Images",
        "msg_credits": 100,
        "img_credits": 10,
    },
    "fling": {
        "stars": 500,
        "label": "🫦 Fling — Most Popular",
        "description": "1000 Messages • 100 Images • 10 Videos",
        "msg_credits": 1000,
        "img_credits": 100,
    },
    "fantasy": {
        "stars": 1000,
        "label": "❤️🔥 Fantasy — Best Value",
        "description": "5000 Messages • 500 Images • 50 Videos",
        "msg_credits": 5000,
        "img_credits": 500,
    }
}

SUBSCRIPTION_TEXT = """<b>UNRESTRICTED ACCESS 🙈 UNLIMITED FUN</b>

💋 Uncensored Chats and Roleplay
🔥 Spicy Photos & Videos
🔞 Remove all restrictions

━━━━━━━━━━━━━━━━━━━━━━

<b>💕 Crush</b>
• 100 Messages
• 10 Images

━━━━━━━━━━━━━━━━━━━━━━

<b>🫦 Fling (Most Popular)</b>
• 1000 Messages
• 100 Images
• 10 Videos

━━━━━━━━━━━━━━━━━━━━━━

<b>❤️🔥 Fantasy (Best Value)</b>
• 5000 Messages
• 500 Images
• 50 Videos

━━━━━━━━━━━━━━━━━━━━━━

<i>🔒 Secure payment via Telegram Stars</i>
Unlock Premium 👇"""


async def subscribe_command(update, context):
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


async def buy_callback(update, context):
    query = update.callback_query
    tier = query.data.split("_")[1]
    info = TIERS[tier]
    await query.answer()
    await context.bot.send_invoice(
        chat_id=query.message.chat_id,
        title=info["label"],
        description=info["description"],
        payload=f"sub_{tier}",
        provider_token="",
        currency="XTR",
        prices=[LabeledPrice(info["label"], info["stars"])],
        need_shipping_address=False,
        is_flexible=False
    )


async def pre_checkout(update, context):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment(update, context):
    payload = update.message.successful_payment.invoice_payload
    tier = payload.split("_")[1]
    user_id = update.effective_user.id
    info = TIERS[tier]
    expiry = int(time.time()) + 30 * 86400
    db.update_user(user_id,
        tier=tier,
        expires_at=expiry,
        msg_credits=info["msg_credits"],
        img_credits=info["img_credits"],
        nsfw_allowed=1,
        age_verified=1
    )
    await update.message.reply_text(f"✅ {info['label']} activated! Ab koi restriction nahi 🔥")
