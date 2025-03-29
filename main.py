from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from config import BOT_TOKEN
import logging
import asyncio


logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def process_start_command(msg: types.Message):
    await msg.reply("Привет!\nНапиши мне что-нибудь!")


@dp.message()
async def echo_message(msg: types.Message):
    await bot.send_message(msg.from_user.id, "Все говорят \"" + msg.text + "\", а ты купи слона")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
