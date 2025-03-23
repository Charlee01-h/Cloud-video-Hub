import os
import asyncio
import logging
import aiohttp
import ssl
from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InputFile
from database import Database
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # Bot admin ID

# Initialize bot and dispatcher
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher(storage=MemoryStorage())
db = Database()

# Command to check user subscription status
@dp.message(commands=["start"])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    user = db.get_user(user_id)
    
    if user is None:
        db.add_user(user_id)
        await message.answer("\U0001F44B Welcome! You are on the Free Plan (5 videos/day).")
    else:
        plan_status = "Paid" if user["is_premium"] else "Free (5 videos/day)"
        await message.answer(f"\U0001F44B Welcome back! Your current plan: {plan_status}")

# Command to check remaining limit
@dp.message(commands=["mylimit"])
async def my_limit(message: types.Message):
    user_id = message.from_user.id
    limit = db.get_user_limit(user_id)
    await message.answer(f"\U0001F3A5 Your remaining free video limit today: {limit}/5")

# Command to show payment details
@dp.message(commands=["buy"])
async def buy_subscription(message: types.Message):
    qr_code_path = "payment_qr.jpg"  # Add your QR code image path
    payment_details = "\U0001F4B0 To upgrade, send payment to UPI ID: cloudvideohub@ibl and share the confirmation code."
    with open(qr_code_path, "rb") as qr:
        await message.answer_photo(qr, caption=payment_details)

# Command to show payment details with QR code
@dp.message_handler(commands=["buy"])
async def buy_subscription(message: types.Message):
    payment_text = (
        "💰 To upgrade, send payment to:\n\n"
        "📌 UPI ID: cloudvideohub@ibl\n"
        "📌 After payment, send the confirmation code to the admin."
    )
    qr_path = "payments.jpeg"  # QR code image ka path
    
    try:
        with open(qr_path, "rb") as qr:
            await bot.send_photo(message.chat.id, qr, caption=payment_text)
    except Exception as e:
        await message.reply(payment_text)
        logging.error(f"QR Code sending failed: {e}")

# Command to get bot info and available user commands
@dp.message(commands=["info"])
async def info_command(message: types.Message):
    info_text = (
        "\u2139\ufe0f <b>Available Commands:</b>\n"
        "\n\u2705 /start - Check your subscription status"
        "\n\u2705 /mylimit - Check your remaining free video limit"
        "\n\u2705 /buy - Get payment details for subscription"
        "\n\u2705 /expiry - Check your subscription expiry date"
        "\n\u2705 /get <terabox_link> - Fetch and receive a video from Terabox"
    )
    await message.answer(info_text, parse_mode="HTML")

# Command to fetch and send videos from Terabox
@dp.message(commands=["get"])
async def get_video(message: types.Message):
    user_id = message.from_user.id
    if db.check_limit_exceeded(user_id):
        return await message.answer("\U0001F6AB You have reached your daily limit. Upgrade to a premium plan to continue.")
    
    try:
        _, terabox_link = message.text.split()
        
        # Fetch video URL using Terabox API or scraping
        video_url = fetch_video(terabox_link)  # Function needs implementation
        if not video_url:
            return await message.answer("\u274C Unable to fetch video. Check the link and try again.")
        
        # Download the video to server
        file_path = f"downloads/{user_id}.mp4"
        os.makedirs("downloads", exist_ok=True)
        downloaded_file = await download_video(video_url, file_path)
        
        if downloaded_file:
            # Send the video to the user
            with open(downloaded_file, "rb") as video:
                await bot.send_video(user_id, video, caption="\U0001F3A5 Here is your video!")
            
            db.decrease_limit(user_id)  # Decrease limit for free users
            os.remove(downloaded_file)  # Clean up file after sending
        else:
            await message.answer("\u274C Video download failed. Please try again later.")
    except Exception as e:
        await message.answer("\u274C Invalid format. Use: /get <terabox_link>")
        logging.error(f"Error: {e}")

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
