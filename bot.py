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

# photo prompts per character — progressive reveal system
PHOTO_PROMPTS = {
    "kriti": {
        "sfw": [
            "beautiful indian woman 23, wearing elegant silk saree, blouse, bindi, long black hair, smiling softly, mumbai apartment balcony, golden hour light",
            "pretty indian girl in salwar kameez, dupatta draped, natural makeup, standing near window, soft sunlight, candid home photo",
            "indian girl in stylish kurti and jeans, hair open, laughing candid, coffee shop background, warm lighting",
            "beautiful indian woman in western crop top and high waist jeans, mall background, confident pose, natural face",
            "indian girl in floral sundress, outdoor park, hair blowing in wind, natural smile, golden hour",
            "pretty indian girl in lehenga choli, traditional jewellery, living room, diwali lights background, festive look",
            "indian woman in office formal blazer and trousers, professional but pretty, natural makeup, confident",
            "indian girl in cozy oversized hoodie and shorts, bedroom, messy hair, cute morning look, warm light",
        ],
        "teasing": [
            "beautiful indian woman in saree with pallu slightly slipping off shoulder, bedroom, seductive soft smile, warm lamp light",
            "indian girl in deep neck kurti, sitting on bed, hair open, slight cleavage, natural seductive look, dim warm light",
            "pretty indian woman in crop top sitting on floor, midriff showing, candid home photo, natural light",
            "indian girl in spaghetti strap top and shorts, standing near window, wind blowing hair, natural skin, real photo",
            "beautiful indian woman in off shoulder top, slight cleavage, mirror selfie, natural makeup, warm bedroom light",
            "indian girl in tight jeans and fitted top, lying on bed reading phone, candid real photo, natural lighting",
        ],
        "bikini": [
            "beautiful indian woman in red bikini, goa beach, wet hair, sun kissed brown skin, waves behind, real candid photo",
            "sexy indian girl in black bikini by hotel pool, confident pose, golden hour, water droplets on skin",
            "indian woman in yellow two piece swimsuit, beach selfie, natural smile, real skin, sunny day",
            "beautiful indian girl in floral bikini, lying on beach towel, reading, candid real photo, tanned skin",
        ],
        "lingerie": [
            "beautiful indian woman in black lace bra and panty, sitting on bed edge, looking at camera softly, warm lamp bedroom",
            "sexy indian girl in red lingerie set, mirror selfie, dim bedroom, real skin texture, seductive look",
            "indian woman in white lace lingerie, lying on white bedsheet, soft morning light, natural real photo",
            "pretty indian girl in pink lingerie, standing near window, curtain blowing, natural light, real skin",
            "indian girl just removed top wearing only bra, holding shirt in hand, surprised candid look, bedroom",
            "beautiful indian woman pressing her own boobs in black bra, seductive expression, bedroom mirror selfie",
        ],
        "nude": [
            "beautiful indian woman topless, hands covering chest, shy seductive smile, soft bedroom lighting, real skin",
            "sexy indian girl fully nude lying on bed, legs crossed, real skin texture, soft lamp light, tasteful artistic",
            "beautiful indian woman nude in shower, water running, eyes closed, steam, real skin, artistic photo",
            "indian girl nude selfie in mirror, wet hair, post shower, bathroom, natural real skin, soft light",
            "beautiful indian woman nude, sitting on bed sending flying kiss to camera, playful seductive look",
            "sexy indian girl nude, lying sideways on bed, hair spread, real skin pores, cinematic soft light",
        ]
    },
    "naina": {
        "sfw": [
            "pretty delhi college girl in jeans and crop top, university campus, candid photo, natural light",
            "indian college girl in casual kurti, canteen background, laughing with phone, real candid photo",
            "cute indian girl in hoodie and joggers, college corridor, morning look, natural face, real photo",
            "delhi girl in stylish co-ord set, mall background, shopping bags, confident smile, real photo",
            "indian college girl in saree for college fest, traditional makeup, excited smile, real candid",
        ],
        "teasing": [
            "delhi college girl in tight crop top and low waist jeans, sitting on college wall, midriff showing, candid",
            "indian girl in fitted tank top, bedroom, hair open, natural seductive look, warm afternoon light",
            "pretty indian girl in short shorts and spaghetti top, home, lying on couch, real candid photo",
        ],
        "bikini": [
            "pretty delhi college girl in bikini, goa trip, beach, natural body, real candid photo, friends trip vibe",
            "indian college girl in swimsuit by hostel pool, selfie, natural smile, real skin, sunny",
        ],
        "lingerie": [
            "pretty indian college girl in pink lingerie, hostel room, mirror selfie, real skin, seductive smile",
            "delhi girl in black bra and panty, sitting on study table, playful look, warm room light",
            "indian girl in lace lingerie, lying on bed, phone in hand, candid bedroom photo, real skin",
        ],
        "nude": [
            "pretty indian college girl topless, hands covering chest coyly, real skin, soft bedroom light, shy smile",
            "delhi girl fully nude, sitting on bed, knees up, hair messy, real skin texture, soft warm light",
            "indian girl nude selfie in hostel bathroom mirror, post shower, wet body, natural real skin",
        ]
    },
    "sara": {
        "sfw": [
            "confident beautiful indian woman 25 in power blazer and trousers, office background, bold pose, real photo",
            "sexy indian girl in gym outfit, sports bra and leggings, gym mirror selfie, toned body, real photo",
            "confident indian woman in western bodycon dress, restaurant background, wine glass, classy real photo",
            "sara in casual jeans and fitted tshirt, home terrace, golden hour, hair open, real candid photo",
        ],
        "teasing": [
            "confident indian woman in deep neck bodycon dress, slight cleavage, party background, bold seductive look",
            "indian girl in sports bra only working out, toned midriff, gym, real sweaty candid photo",
            "dominant indian woman in silk robe slightly open, bedroom, bold eye contact, real photo",
        ],
        "bikini": [
            "dominant confident indian woman in black bikini, luxury hotel pool, bold pose, real photo",
            "sara in red bikini, beach, bold confident pose, sun kissed skin, real candid photo",
        ],
        "lingerie": [
            "confident indian woman in black lace lingerie, luxury bedroom, dominant seductive look, real photo",
            "sara in red lingerie set, bold mirror selfie, confident expression, real skin, warm light",
            "dominant indian girl pressing her boobs in black bra, bold seductive expression, luxury bedroom",
        ],
        "nude": [
            "confident beautiful indian woman topless, bold direct eye contact, luxury bedroom, real skin, artistic",
            "sara fully nude, dominant bold pose on bed, real skin texture, cinematic dramatic lighting",
            "indian woman nude in shower, bold confident expression, water running, steam, real skin, artistic",
        ]
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


# track how many photos each user has received for progressive reveal
user_photo_count = {}


def _get_photo_category(user_id, user, explicit_requested=False):
    is_paid = user["tier"] != "free"
    nsfw = is_paid and int(user.get("nsfw_allowed", 0)) == 1
    count = user_photo_count.get(user_id, 0)

    if not is_paid:
        return "sfw"
    if not nsfw:
        return random.choice(["sfw", "sfw", "teasing"])  # mostly sfw with rare tease

    # paid + nsfw: progressive reveal based on photo count
    if explicit_requested:
        if count < 2:
            return "teasing"       # first 2 explicit requests: still teasing
        elif count < 4:
            return "bikini"        # then bikini
        elif count < 6:
            return "lingerie"      # then lingerie
        else:
            return "nude"          # only after 6 photos: full explicit
    else:
        if count < 3:
            return "sfw"           # first 3 auto photos: fully clothed
        elif count < 5:
            return "teasing"       # then teasing
        else:
            return random.choice(["bikini", "lingerie"])  # then spicy


async def send_photo_to_user(bot, user_id, active_char, user, caption):
    category = _get_photo_category(user_id, user, explicit_requested=False)
    prompts = PHOTO_PROMPTS.get(active_char, PHOTO_PROMPTS["kriti"])
    if category not in prompts:
        category = "sfw"
    prompt = random.choice(prompts[category])
    try:
        img_bytes = await image_gen.generate_image(prompt, nsfw=(category in ["lingerie", "nude"]))
        await bot.send_photo(chat_id=user_id, photo=img_bytes, caption=caption)
        user_photo_count[user_id] = user_photo_count.get(user_id, 0) + 1
    except:
        pass


async def send_photo_on_request(update, user_id, active_char, user):
    is_paid = user["tier"] != "free"
    if not is_paid:
        return
    category = _get_photo_category(user_id, user, explicit_requested=True)
    prompts = PHOTO_PROMPTS.get(active_char, PHOTO_PROMPTS["kriti"])
    if category not in prompts:
        category = "sfw"
    prompt = random.choice(prompts[category])
    captions = [
        "sirf tumhare liye 💋",
        "lo jaan 😈",
        "kaisa laga? 😏",
        "iske baad kuch bolna hai? 🔥",
        "abhi khush? 😘",
        "ye toh bas jhalak hai 🙈",
        "aur chahiye? 😉",
    ]
    try:
        img_bytes = await image_gen.generate_image(prompt, nsfw=(category in ["lingerie", "nude"]))
        await update.message.reply_photo(photo=img_bytes, caption=random.choice(captions))
        user_photo_count[user_id] = user_photo_count.get(user_id, 0) + 1
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
