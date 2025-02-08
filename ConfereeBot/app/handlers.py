from aiogram import F, Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer_photo(
        photo="https://drive.google.com/drive-viewer/AKGpihZIFWc_PI_Fic0oaXBP1UHxZJMybiyCt8AyElmN6wMIOrWNFFwVMKAj0VEViOq_9XHEL5wbV0iZE4adx1u0xerC1wo-Pu6JSqA=w1920-h935-rw-v1",
        caption=
        f"Привет, {message.from_user.first_name}! 👋\n\n"
        "Я — твой помощник в записи онлайн-конференций Google Meet! 🎥✨\n\n"
        "Просто дай мне ссылку на конференцию, и я позабочусь обо всём остальном. 🕒 📹\n\n"
        "Не важно, совещание это, лекция или другое важное событие — я сохраню всё для тебя! 💾 🔐"
    )


@router.message(Command('help'))
async def cmd_help(message: Message):
    await message.answer('Я бы тебе помог, но у меня лапки')
