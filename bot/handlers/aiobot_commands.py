from loguru import logger
from typing import Union
from config import Config

from aiogram import types, Router
from aiogram.filters import StateFilter, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import ReplyKeyboardRemove

from pyrogram import Client
from pyrogram.errors import PhoneNumberInvalid, SessionPasswordNeeded

from bot.database.requests import db_add_account, db_update_proxy

# настраиваем логи
logger.add(
    'bot/data/debug.log',
    format="{time:DD-MMM-YYYY HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation='10 MB'
)

auth_router = Router()
new_userbot: Union[Client, None] = None

class UserbotRegistrationFSM(StatesGroup):
    phone_validation = State()
    sms_verification = State()
    two_factor_verification = State()


async def save_userbot_session(phone_number, session_string):
    phone_number = phone_number[1:]

    with open(f"bot/sessions/{phone_number}.session", "w") as f:
        f.write(session_string)


@auth_router.message(Command("start"))
async def start_info_text(message: types.Message):
    await message.reply('/add_acc — добавить аккаунт\n'
                        '/check — restart + перепроверить аккаунты\n'
                        '/proxy "название сессии в скобочках под спойлером" "прокси"\n'
                        '/mem - отправить 3 стикера в раздел мемов\n'
                        '\n'
                        '/join "логин канала, в который надо вступить"\n'
                        '/leave "логин канала, из которого надо выйти"\n'
                        '\n'
                        '/progrev - 5 действий (1 репост, 1 смс и по 1 реакции на 3 последних сообщения)')


@auth_router.message(Command("check"))
async def restart_all_service(message: types.Message):
    await message.bot.send_message(chat_id=Config.chat_id,
                                   message_thread_id=Config.message_thread_id,
                                   text='\U0001f504 Перезапускаем сервис мониторинга')

    exit(0)


@auth_router.message(Command("mem"))
async def send_memes_msg_from_chat(message: types.Message):
    memes_stickers = [
        'CAACAgQAAxkBAAICzmbPem6jhxwcjYfAob4XkuepX8DIAALZCwACxFlYUzE4gsDpoGyHNQQ',
        'CAACAgIAAxkBAAIC0GbPernzsPcJ03r7XHeybRM2K2VtAALjFAACgx1ASLz3p6wXWpCqNQQ',
        'CAACAgIAAxkBAAIC0mbPesIG36CrwhA2438j6yWsaV77AAIxPgACEhLgSaHy15RJGLnXNQQ'
    ]

    await message.delete()

    for sticker in memes_stickers:
        await message.bot.send_sticker(chat_id=Config.chat_id,
                                       message_thread_id=2,
                                       sticker=sticker)


@auth_router.message(Command("proxy"))
async def update_userbot_proxy(message: types.Message):
    msg = message.text.split(' ')
    client_name = msg[1]
    proxy_str = msg[2]

    is_update = await db_update_proxy(client_name, proxy_str)
    if is_update:
        await message.answer('Прокси заменены, для перезахода используй /check')
    else:
        await message.answer('Неправильно введен client_name (он прячется под спойлером)')


@auth_router.message(Command("add_acc"))
async def add_userbot(message: types.Message, state: FSMContext):
    await message.reply("Введите номер телефона в формате +79123456789")

    await state.set_state(UserbotRegistrationFSM.phone_validation)


@auth_router.message(StateFilter(UserbotRegistrationFSM.phone_validation))
async def phone_validation(message: types.Message, state: FSMContext):
    global new_userbot
    phone_number = message.text.replace(" ", "")

    try:
        if new_userbot is None:
            new_userbot = Client("in_memory",
                                 in_memory=True,
                                 api_id=Config.api_id,
                                 api_hash=Config.api_hash
                                 )
        await new_userbot.connect()

        send_code_data = await new_userbot.send_code(phone_number)
        phone_code_hash = send_code_data.phone_code_hash

        await message.reply("Введите код из SMS:",
                            reply_markup=ReplyKeyboardRemove())
        await state.update_data(phone_number=phone_number, phone_code_hash=phone_code_hash)
        await state.set_state(UserbotRegistrationFSM.sms_verification)

    except PhoneNumberInvalid:
        await message.reply("Неверный формат номера телефона. Попробуйте еще раз.",
                            reply_markup=ReplyKeyboardRemove())

        await state.clear()
        new_userbot = None


@auth_router.message(StateFilter(UserbotRegistrationFSM.sms_verification))
async def sms_verification(message: types.Message, state: FSMContext):
    global new_userbot
    code = message.text
    fsm_data = await state.get_data()
    phone_number = fsm_data.get('phone_number')
    phone_code_hash = fsm_data.get('phone_code_hash')

    try:
        signed_in_user = await new_userbot.sign_in(phone_number=phone_number,
                                                   phone_code_hash=phone_code_hash,
                                                   phone_code=code)
        await message.reply(
            f"Успешный вход\n"
            f"Имя: {signed_in_user.first_name} "
            f"Фамилия: {signed_in_user.last_name} "
            f"Username:(@{signed_in_user.username})!")

        session_string = await new_userbot.export_session_string()
        await save_userbot_session(phone_number=phone_number + '_' + str(signed_in_user.username),
                           session_string=session_string)
        await state.update_data(client_name=phone_number[1:] + '_' + str(signed_in_user.username))

        await add_userbot_db(message, state)

    except SessionPasswordNeeded:
        await message.reply('Введите код-пароль:')
        await state.set_state(UserbotRegistrationFSM.two_factor_verification)

    except Exception as e:
        await message.reply(f"Ошибка при входе: {e}")
        await state.clear()
        new_userbot = None


@auth_router.message(StateFilter(UserbotRegistrationFSM.two_factor_verification))
async def two_factor_verification(message: types.Message, state: FSMContext):
    global new_userbot
    password = message.text
    fsm_data = await state.get_data()
    phone_number = fsm_data.get('phone_number')

    try:
        signed_in_user = await new_userbot.check_password(password)

        await message.reply(
            f"\u2705 Успешный вход\n"
            f"Имя: {signed_in_user.first_name}\n"
            f"Фамилия: {signed_in_user.last_name}\n"
            f"Username: @{signed_in_user.username}\n"
            f"Session-name: <code>{phone_number[1:]}_{signed_in_user.username}</code>")

        session_string = await new_userbot.export_session_string()
        await save_userbot_session(phone_number=phone_number + '_' + str(signed_in_user.username),
                           session_string=session_string)

        await state.update_data(client_name=phone_number[1:] + '_' + str(signed_in_user.username))
        await add_userbot_db(message, state)

    except Exception as e:
        await message.reply(f"Ошибка при вводе кода-пароля: {e}")
        await state.clear()
        new_userbot = None


async def add_userbot_db(message: types.Message, state: FSMContext):
    global new_userbot
    fsm_data = await state.get_data()
    client_name = fsm_data.get('client_name')

    await db_add_account(client_name=client_name, proxy='none')
    await message.bot.send_message(chat_id=Config.chat_id,
                                   message_thread_id=Config.message_thread_id,
                                   text=f'Аккаунт сохранен, для перезахода используй /check')

    await state.clear()
    new_userbot = None

