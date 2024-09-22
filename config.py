from dataclasses import dataclass

from aiogram.fsm.storage.memory import MemoryStorage
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from pyrogram import Client


@dataclass
class Config:
    api_id: int = 23988290
    api_hash: str = '62b3cc11b049d4e2f5d4a1de5636df06'
    bot_token: str = '7523702500:AAFypFVfEtj0O0vOP-HeBbiRRmY71C0HS3g'
    bot_giveaway_token: str = '7521695859:AAH2PXqJpK_jrsh7UE6_RmqgnBpuPUfZ3Zk'
    admin_id: int = 902966420
    chat_id: int = -1002103524325
    message_thread_id: int = 4
    userbot_sessions_dir = "bot/sessions"


userbot_manager_bot = Bot(token=Config.bot_token,default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher(storage=MemoryStorage())

SQLALCHEMY_URL='sqlite+aiosqlite:///bot/database/db.sqlite3'