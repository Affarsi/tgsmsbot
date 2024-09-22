import random
import asyncio
import time

from config import Config
from loguru import logger

from pyrogram import Client
from pyrogram.types import Message
from pyrogram.enums import ChatAction

# настраиваем логи
logger.add(
    'bot/data/debug.log',
    format="{time:DD-MMM-YYYY HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation='10 MB'
)

# Выход userbot`а из чатов
async def exiting_the_chat(userbot: Client, message: Message):
    start_time = time.time()
    channels_for_exit = message.command[1:]

    for channel in channels_for_exit:
        await asyncio.sleep(random.uniform(15, 60))
        await userbot.leave_chat(channel)
        await userbot.leave_chat(channel)
        logger.info(f"[{userbot.name}] отписался от @{channel}")

    await message.react(emoji='👍')
    elapsed_time = round(time.time() - start_time, 2)
    logger.info(f"{userbot.name} успешно закончил отписку за {elapsed_time} секунд!")


# Вступление userbot`а в чаты
async def joining_the_chat(userbot: Client, message: Message):
    start_time = time.time()
    channels_for_join = message.command[1:]

    for channel in channels_for_join:
        await asyncio.sleep(random.uniform(15, 60))
        await userbot.join_chat(channel)
        await userbot.join_chat(channel)
        logger.info(f"[{userbot.name}] подписался на @{channel}")
    await userbot.archive_chats(channels_for_join)

    await message.react(emoji='👍')
    elapsed_time = round(time.time() - start_time, 2)  # Вычисляем время в секундах
    logger.info(f"[{userbot.name}] успешно закончил подписку за {elapsed_time} секунд!")


# Обработка входящих сообщений и гифт кодов userbot`а
async def chat_and_gift_handler(userbot: Client, message: Message):
    if message.giveaway is not None:
        await userbot.send_message(
            chat_id=Config.chat_id,
            message_thread_id=Config.message_thread_id,
            text=f'Я выиграл подписку на {message.giveaway.months} месяца(ев)!'
        )
    elif message.from_user.id == 777000:
        await userbot.send_message(
            chat_id=Config.chat_id,
            message_thread_id=Config.message_thread_id,
            text=f'Мне пришло сообщение от Telegram!'
        )
    else:
        await userbot.send_message(
            chat_id=Config.chat_id,
            message_thread_id=Config.message_thread_id,
            text=f'Мне пришло сообщение от @{message.from_user.username}\n'
                 f'Его содержание:\n'
                 f'{message.text}'
        )


# Симуляция userbot`ом действия рядового пользователя
async def simulate_user_activity(userbot: Client, message: Message):
    start_time = time.time()
    lust_message_ids = []

    logger.info(f"[{userbot.name}] начал прогрев")

    # Получаем 3 последних сообщения
    async for lust_msg in userbot.get_chat_history(Config.chat_id, limit=4):
        lust_message_ids.append(lust_msg.id)
    lust_message_ids = lust_message_ids[1:]

    # Прогрев через реакции
    for message_id in lust_message_ids:
        await asyncio.sleep(delay=random.randint(15, 35))
        await userbot.send_reaction(chat_id=Config.chat_id,
                                   message_id=message_id,
                                   emoji=random.choice(
                                       ["❤️", "🔥", "😁", "😍", "🥰", "👍", "🎉", "🤗", "⚡️"]
                                   ))

    # Прогрев через перессылку смс
    await asyncio.sleep(delay=random.randint(5, 15))
    await userbot.forward_messages(
        chat_id='me',
        from_chat_id=Config.chat_id,
        message_ids=random.choice(lust_message_ids)
    )

    # Прогрев через чат
    from main import progrev_phrases  # импортируем список фраз

    await userbot.send_chat_action(Config.chat_id, ChatAction.TYPING) # пользователь печатает...
    await asyncio.sleep(delay=random.randint(15, 35))
    await message.reply(random.choice(progrev_phrases).strip()) # отправка фразы
    await asyncio.sleep(delay=random.randint(15, 35))

    # Конец прогрева
    await message.react(emoji='👍')
    elapsed_time = round(time.time() - start_time, 2)  # Вычисляем время в секундах
    logger.info(f"[{userbot.name}] успешно закончил прогрев за {elapsed_time} секунд!")
