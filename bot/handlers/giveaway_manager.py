import asyncio
from datetime import datetime, timedelta

from config import Config
from loguru import logger

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from pyrogram import Client
from pyrogram.types import Message

from bot.database.requests import (
    db_add_giveaway,
    cleanup_and_collect_giveaways,
    get_giveaway_channels,
    db_dell_giveaway)

# настраиваем логи
logger.add(
    'bot/data/debug.log',
    format="{time:DD-MMM-YYYY HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation='10 MB'
)

scheduler = AsyncIOScheduler()


# Запуск планировщика и очистка старых розыгрышей
async def run_apscheduler():
    await asyncio.sleep(5)
    giveaways_dict = await cleanup_and_collect_giveaways()

    # Для "Для apscheduler"
    if giveaways_dict.get('Для apscheduler'):
        for giveaway in giveaways_dict['Для apscheduler']:
            if giveaway:
                giveaway_id = giveaway['id']
                finish_date = datetime.strptime(giveaway['finish_date'], '%Y-%m-%d %H:%M:%S')
                channels_count = giveaway['channels_count']

                scheduler.add_job(
                    userbot_group_join,
                    name=f'id розыгрыша [{str(giveaway_id)}] - кол-во чатов [{channels_count}]',
                    args=[giveaway_id],
                    trigger='date',
                    run_date=finish_date,
                    id=str(giveaway_id)
                )

                logger.info(f'В apscheduler добавлен розыгрыш под {giveaway_id} id на {finish_date}')

    # Для "Для мгновенного участия"
    giveaway_channels = []

    if giveaways_dict.get('Для мгновенного участия'):
        for item in giveaways_dict['Для мгновенного участия']:
            channels = item['channels_list'].split(', ')
            giveaway_channels.extend(channels)

        if giveaway_channels:
            join_command_text = "/join\n" + "\n".join(giveaway_channels)
            await userbot_group_join(join_command_text=join_command_text)

    logger.info('apscheduler запущен')
    scheduler.print_jobs()
    scheduler.start()


# Вступление userbot`а в группы
async def userbot_group_join(giveaway_id: int = None, join_command_text: str = None):
    giveaway_bot = Client('giveaway_bot_kostil)sorry',
                          api_id=Config.api_id, api_hash=Config.api_hash,
                          bot_token=Config.bot_giveaway_token, in_memory=True)
    bot_command = join_command_text if join_command_text is not None else await get_giveaway_channels(giveaway_id)

    async with giveaway_bot:
        await giveaway_bot.send_message(
            chat_id=Config.chat_id,
            message_thread_id=Config.message_thread_id,
            text=bot_command
        )
    logger.info('Giveaway manager отправил команду /join в чат')

    if giveaway_id is not None:
        await db_dell_giveaway(giveaway_id)
        logger.info(f'apschedule успешно выполнил и удалил из БД розыгрыш под {giveaway_id} id')


# Регистратор новых giveaway`ев
async def register_giveaway(bot: Client, message: Message):
    giveaway_channels = []

    for chat in message.giveaway.chats:
        if chat.username is None:
            giveaway_channels.append(chat.usernames[0].username)
        else:
            giveaway_channels.append(chat.username)

    # если до конца розыгрыша меньше 1 часа, просто выполняем /join по channel_list
    # иначе добавляем в БД и устанавливаем триггер на час до конца
    now = datetime.now()
    time_remaining = message.giveaway.until_date - now

    if time_remaining.seconds / 3600 < 1:
        await message.react('🦄')

        bot_join_cmd = "/join\n" + "\n".join(giveaway_channels)
        await userbot_group_join(join_command_text=bot_join_cmd)


    else:
        giveaway_channels_str = ", ".join(giveaway_channels)

        # проверяем, есть ли такой розыгрыш в БД, если нет - добавляем
        result_dcit = await db_add_giveaway(
            subs_count=message.giveaway.quantity,
            sub_duration_months=message.giveaway.months,
            channels_list=giveaway_channels_str,
            finish_date=str(message.giveaway.until_date),
        )

        if result_dcit:
            await message.react('🦄')
            finish_date = datetime.strptime(result_dcit["giveaway_finish_date"], '%Y-%m-%d %H:%M:%S')

            # устанавливаем data триггер на исполнения /join по channel_list за один час до конца розыгрыша
            scheduler.add_job(
                userbot_group_join,
                name=f'id розыгрыша [{str(result_dcit["giveaway_id"])}] - кол-во чатов [{len(giveaway_channels)}]',
                args=[result_dcit["giveaway_id"]],
                trigger='date',
                run_date=finish_date,
                id=str(result_dcit["giveaway_id"])
            )
            await asyncio.sleep(1)

            logger.info(f'Розыгрыш {message.giveaway.quantity}x{message.giveaway.months} '
                        f'добавлен в планировщик и БД! [{finish_date}]')

            scheduler.print_jobs()

        else:
            await message.react('🤬')