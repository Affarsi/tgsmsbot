import asyncio
import aiohttp
import os

from loguru import logger
from config import Config, dp, userbot_manager_bot

from pyrogram import Client, filters, compose
from pyrogram.handlers import MessageHandler

from bot.database.database import create_db
from bot.database.requests import db_get_proxy

from bot.handlers.aiobot_commands import auth_router
from bot.handlers.userbot_handlers import (
    exiting_the_chat,
    joining_the_chat,
    simulate_user_activity,
    chat_and_gift_handler)
from bot.handlers.giveaway_manager import register_giveaway, run_apscheduler

# настраиваем логи
logger.add(
    'bot/data/debug.log',
    format="{time:DD-MMM-YYYY HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation='10 MB'
)

# определение словаря проверенных прокси, списка с клиентами и списка с session_string
checked_proxies_dict = {}
clients_list = []
clients_session_strings = []


# подготавливаем 100 фраз для прогрева аккаунтов
with open(r"bot/data/100saying_phrases.txt", encoding='utf-8') as file:
    progrev_phrases = file.readlines()


async def check_proxy(proxy_str: str) -> bool:
    # Проверяем, был ли уже проверен данный прокси
    if proxy_str in checked_proxies_dict:
        return checked_proxies_dict[proxy_str]

    try:
        # Разбиваем строку прокси на части
        credentials, host_data = proxy_str.split('@')
        login, password = credentials.split(':')
        ip, port = host_data.split(':')

        # Формируем URL прокси
        proxy_url = f'http://{login}:{password}@{ip}:{port}'

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(r"https://api.telegram.org:443", proxy=proxy_url, timeout=20) as response:
                    if response.status == 302 or response.status == 200:
                        # Сохраняем результат проверки в словарь
                        checked_proxies_dict[proxy_str] = True
                        return True
                    else:
                        logger.error(f"Прокси {proxy_str} вернул код состояния {response.status}")
                        checked_proxies_dict[proxy_str] = False
                        return False
            except aiohttp.ClientError as e:
                logger.error(f"Ошибка при проверке прокси {proxy_str}: {e, type(e)}")
                checked_proxies_dict[proxy_str] = False
                return False

    except ValueError:
        logger.error(f"Неверный формат строки прокси: {proxy_str}")
        checked_proxies_dict[proxy_str] = False
        return False
    except Exception as e:
        logger.error('не хендлится: ', e, type(e))
        checked_proxies_dict[proxy_str] = False
        return False


async def run_pyrogram_and_apscheduler():
    start_message_text = 'Аккаунты:\n\n'
    all_accounts_good_key = True
    serial_number_acc = 0

    # from_user_777000 = filters.create(lambda _, __, message: message.from_user.id == 777000)
    userbots_session_files = [f for f in os.listdir(Config.userbot_sessions_dir) if f.endswith(".session")]
    for userbot_session_file in userbots_session_files:
        session_path = os.path.join(Config.userbot_sessions_dir, userbot_session_file)
        session_name = userbot_session_file.split(".")[0]

        proxy = None
        proxy_str = await db_get_proxy(session_name)
        if proxy_str is not None and proxy_str.strip().lower() != 'none':
            credentials, host_data = proxy_str.split('@')
            ip, port = host_data.split(':')
            login, password = credentials.split(':')
            proxy = {"scheme": "http",
                     "hostname": ip,
                     "port": int(port),
                     "username": login,
                     "password": password
                     }
            logger.info(f'Начинаю чек {proxy_str}')
            is_proxy_check = await check_proxy(proxy_str)
            if is_proxy_check is False:
                await userbot_manager_bot.send_message(chat_id=Config.chat_id,
                                       message_thread_id=Config.message_thread_id,
                                       text=f'Прокси {proxy_str} отлетели, аккаунт: {session_name} (407?)')
                await asyncio.sleep(0.2)
                continue
            logger.info('Прокси прошли чек')

        with open(session_path) as file:
            userbot_session_string = file.read().strip()

            clients_session_strings.append(userbot_session_string)

        userbot = Client(session_name,
                         api_id=Config.api_id,
                         api_hash=Config.api_hash,
                         session_string=userbot_session_string,
                         proxy=proxy)
        try:
            await userbot.connect()

            client_data = await userbot.get_me()
            await userbot.disconnect()
            # all is good!

            serial_number_acc += 1
            start_message_text += f'{serial_number_acc}) {client_data.username} - <code>{session_name}</code>\n'
            clients_list.append(userbot)

            userbot.add_handler(
                MessageHandler(chat_and_gift_handler, filters.gift_code or filters.private and ~filters.me))
            userbot.add_handler(
                MessageHandler(joining_the_chat, filters.command("join") & filters.chat(Config.chat_id)))
            userbot.add_handler(
                MessageHandler(exiting_the_chat, filters.command("leave") & filters.chat(Config.chat_id)))
            userbot.add_handler(
                MessageHandler(simulate_user_activity, filters.command("progrev") & filters.chat(Config.chat_id)))

            logger.info(f'[{session_name}] запущен')
        except OverflowError:
            await userbot_manager_bot.send_message(chat_id=Config.chat_id,
                                   message_thread_id=Config.message_thread_id,
                                   text=f'Прокси {proxy_str} отлетели, аккаунт: {session_name}')
        except Exception as e:
            logger.error(f'[{session_name}] при запуске вызвал ошибку: {e, type(e)}')
            all_accounts_good_key = False
            await userbot_manager_bot.send_message(chat_id=Config.chat_id,
                                   message_thread_id=Config.message_thread_id,
                                   text=f'{session_name} либо умер, либо выкинуло')
            # db_delete(session_name)
            # os.remove(session_path)

    # запускаем giveaway manager
    giveaway_bot = Client('bot/data/giveaway_bot')
    giveaway_bot.add_handler(
        MessageHandler(register_giveaway, filters.chat(Config.chat_id) & filters.giveaway)
    )
    clients_list.append(giveaway_bot)
    logger.info(r'Started "Giveaway Manager"')

    logger.info(r'Started "Userbot Service"')
    if all_accounts_good_key and len(clients_list) > 0:
        await userbot_manager_bot.send_message(chat_id=Config.chat_id,
                               message_thread_id=Config.message_thread_id,
                               text='🤖 Бот активирован')

    await userbot_manager_bot.send_message(chat_id=Config.chat_id,
                           message_thread_id=Config.message_thread_id,
                           text=start_message_text)

    await run_apscheduler() # запускаем планировщик
    await compose(clients_list)


async def run_aiogram():
    dp.include_router(auth_router)
    await dp.start_polling(userbot_manager_bot, allowed_updates=dp.resolve_used_update_types())


async def main():
    await create_db()

    task1 = asyncio.create_task(run_pyrogram_and_apscheduler())
    task2 = asyncio.create_task(run_aiogram())
    await asyncio.gather(task1, task2)


if __name__ == '__main__':
    asyncio.run(main())