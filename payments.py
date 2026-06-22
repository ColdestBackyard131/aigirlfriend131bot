import time
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, LabeledPrice
from telegram.ext import PreCheckoutQueryHandler
import database as db
from database import set_subscription

TIERS = {
    "premium": {"price": 100, "description": "30 days: Unlimited chat + 50 NSFW images"},
    "vip":     {"price": 300, "description": "30 days: Unlimited + custom characters"}
}


async def subscribe_command(update, context):
    keyboard = [
        [InlineKeyboardButton(f"💰 {tier.upper()} - {info['price']} Stars", callback_data=f"buy_{tier}")]
        for tier, info in TIERS.items()
    ]
    await update.message.reply_text("Select your plan:", reply_markup=InlineKeyboardMarkup(keyboard))


async def buy_callback(update, context):
    query = update.callback_query
    tier = query.data.split("_")[1]
    price = TIERS[tier]["price"]
    await query.answer()
    await context.bot.send_invoice(
        chat_id=query.message.chat_id,
        title=f"{tier.upper()} Subscription",
        description=TIERS[tier]["description"],
        payload=f"sub_{tier}",
        provider_token="",  # empty for Telegram Stars
        currency="XTR",
        prices=[LabeledPrice("Subscription", price)],
        need_shipping_address=False,
        is_flexible=False
    )


async def pre_checkout(update, context):
    await update.pre_checkout_query.answer(ok=True)


async def successful_payment(update, context):
    payload = update.message.successful_payment.invoice_payload
    tier = payload.split("_")[1]
    user_id = update.effective_user.id
    expiry = time.time() + 30 * 86400
    set_subscription(user_id, tier)
    await update.message.reply_text(f"✅ Activated {tier} plan! Enjoy adult content and image generation.")
