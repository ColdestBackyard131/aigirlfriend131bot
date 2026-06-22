from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import database as db


async def age_gate(update, context):
    keyboard = [[InlineKeyboardButton("✅ I am 18+", callback_data="age_confirm")]]
    await update.message.reply_text(
        "⚠️ This bot may contain adult content. You must be 18 years or older.\nDo you confirm?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def age_confirm_callback(update, context):
    query = update.callback_query
    user_id = query.from_user.id
    db.update_user(user_id, age_verified=1, nsfw_allowed=1)
    await query.edit_message_text("✅ Age verified. Adult content unlocked.")


def is_age_verified(user_id):
    user = db.get_user(user_id)
    return user and user.get("age_verified") == 1
