from aiogram import Bot, Dispatcher, F
from aiogram.filters.command import Command
from aiogram.types import ReplyKeyboardRemove, KeyboardButton, Message, ReplyKeyboardMarkup
from config import BOT_TOKEN
import logging
import asyncio


logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


@dp.message(Command("start"))
async def process_start_command(msg: Message):
    kb = [[KeyboardButton(text="Создать персонажа"), KeyboardButton(text="Погнали сразу в приключение")]]
    keyboard = ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True,
                                         input_field_placeholder="Выбери, че будешь делать")
    await msg.reply("Здарова, го в днд", reply_markup=keyboard)


@dp.message(F.text.lower() == "создать персонажа")
async def with_puree(msg: Message):
    await msg.reply("Создадим же легенду Фаэруна", reply_markup=ReplyKeyboardRemove())

@dp.message(F.text.lower() == "Погнали сразу в приключение")
async def without_puree(msg: Message):
    await msg.reply("Ладно, будешь играть за орка", reply_markup=ReplyKeyboardRemove())


@dp.message(F.text)
async def echo_message(msg: Message):
    await msg.answer("По кнопкам тыкай, или напиши /start")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
