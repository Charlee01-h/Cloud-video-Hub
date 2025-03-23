import os
import asyncio
import logging
import aiohttp
from aiogram.client.default import DefaultBotProperties
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, FSInputFile
from aiogram.fsm.storage.memory import MemoryStorage
from database import Database
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # Bot admin ID

# Initialize bot and dispatcher
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())
db = Database()

# ✅ Start command
@dp.message(Command("start"))
async def start_command(message: Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if user is None:
        db.add_user(user_id)
        await message.answer("👋 Welcome! You are on the Free Plan (5 videos/day).")
    else:
        plan_status = "Paid" if user["is_premium"] else "Free (5 videos/day)"
        await message.answer(f"👋 Welcome back! Your current plan: {plan_status}")

# ✅ Check remaining limit
@dp.message(Command("mylimit"))
async def my_limit(message: Message):
    user_id = message.from_user.id
    limit = db.get_user_limit(user_id)
    await message.answer(f"🎥 Your remaining free video limit today: {limit}/5")

# ✅ Payment details with QR code
@dp.message(Command("buy"))
async def buy_subscription(message: Message):
    payment_text = (
        "💰 To upgrade, send payment to:\n\n"
        "📌 UPI ID: cloudvideohub@ibl\n"
        "📌 After payment, send the confirmation code to the admin."
    )
    qr_path = "payments.jpeg"  # QR code image path
    
    if os.path.exists(qr_path):
        qr_file = FSInputFile(qr_path)
        await message.answer_photo(qr_file, caption=payment_text)
    else:
        await message.answer(payment_text)
        logging.error(f"QR Code image not found: {qr_path}")

# ✅ Bot info & commands list
@dp.message(Command("info"))
async def info_command(message: Message):
    info_text = (
        "ℹ️ <b>Available Commands:</b>\n"
        "\n✅ /start - Check your subscription status"
        "\n✅ /mylimit - Check your remaining free video limit"
        "\n✅ /buy - Get payment details for subscription"
        "\n✅ /expiry - Check your subscription expiry date"
        "\n✅ /get <terabox_link> - Fetch and receive a video from Terabox"
    )
    await message.answer(info_text)

# ✅ Fetch and send videos from Terabox
@dp.message(Command("get"))
async def get_video(message: Message):
    user_id = message.from_user.id
    if db.check_limit_exceeded(user_id):
        return await message.answer("⛔ You have reached your daily limit. Upgrade to a premium plan to continue.")
    
    try:
        _, terabox_link = message.text.split()
        
        # Fetch video URL using Terabox API or scraping
        video_url = fetch_video(terabox_link)  # Function needs implementation
        if not video_url:
            return await message.answer("❌ Unable to fetch video. Check the link and try again.")
        
        # Download the video to server
        file_path = f"downloads/{user_id}.mp4"
        os.makedirs("downloads", exist_ok=True)
        downloaded_file = await download_video(video_url, file_path)
        
        if downloaded_file:
            # Send the video to the user
            video_file = FSInputFile(downloaded_file)
            await bot.send_video(user_id, video_file, caption="🎥 Here is your video!")
            
            db.decrease_limit(user_id)  # Decrease limit for free users
            os.remove(downloaded_file)  # Clean up file after sending
        else:
            await message.answer("❌ Video download failed. Please try again later.")
    except Exception as e:
        await message.answer("❌ Invalid format. Use: /get <terabox_link>")
        logging.error(f"Error: {e}")

# ✅ Start polling
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
