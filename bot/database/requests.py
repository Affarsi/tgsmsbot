import random

from loguru import logger
from datetime import datetime, timedelta
from sqlalchemy import select, update

from bot.database.database import async_session
from bot.database.models import Account, Giveaway

# настраиваем логи
logger.add(
    'data/debug.log',
    format="{time:DD-MMM-YYYY HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation='10 MB'
)


async def db_add_account(client_name: str, proxy: str):
    async with async_session() as session:
        account = Account(client_name=client_name, proxy=proxy)
        session.add(account)
        session.commit()


async def db_get_proxy(client_name: str) -> str:
    async with async_session() as session:
        result = await session.execute(select(Account.proxy).where(Account.client_name == client_name))
        proxy = result.fetchone()
        if proxy is not None:
            return proxy[0]
        else:
            return None


async def db_delete(client_name: str):
    async with async_session() as session:
        result = await session.execute(select(Account).where(Account.client_name == client_name))
        account = result.scalar_one_or_none()
        if account:
            await session.delete(account)
            await session.commit()



async def db_update_proxy(client_name: str, proxy: str) -> bool:
    async with async_session() as session:
        result = await session.execute(select(Account).where(Account.client_name == client_name))
        account = result.scalar_one_or_none()

        if account:
            account.proxy = proxy
            await session.commit()
            return True
        else:
            return False


async def db_add_giveaway(
    subs_count: int,
    sub_duration_months: int,
    channels_list: str,
    finish_date: str,
) -> dict or bool:
    async with async_session() as session:
        finish_datetime = datetime.strptime(finish_date, '%Y-%m-%d %H:%M:%S')

        # Добавляем рандомное количество минут от 1 до 60
        random_minutes = random.randint(1, 60)
        finish_datetime += timedelta(minutes=random_minutes)
        finish_datetime -= timedelta(hours=1.5)
        finish_date = finish_datetime.strftime('%Y-%m-%d %H:%M:%S')

        # Добавляем новый розыгрыш
        giveaway = Giveaway(
            subs_count=subs_count,
            sub_duration_months=sub_duration_months,
            channels_list=channels_list,
            finish_date=finish_date,
            is_used='1'
        )

        session.add(giveaway)
        await session.flush()
        await session.refresh(giveaway)
        giveaway_id = giveaway.id
        giveaway_finish_date = giveaway.finish_date

        await session.commit()

        return {
            'giveaway_id': giveaway_id,
            'giveaway_finish_date': giveaway_finish_date
        }


async def cleanup_and_collect_giveaways():
    async with async_session() as session:
        # Обновляем строки, устанавливаем is_used на "0", если finish_date меньше настоящего времени
        await session.execute(
            update(Giveaway).where(Giveaway.finish_date < datetime.now()).values(is_used="0")
        )
        await session.commit()

        # Получаем все актуальные розыгрыши
        result = await session.execute(
            select(Giveaway).where(Giveaway.is_used == "1")
        )
        giveaways = result.scalars().all()

        # Создаем словарь с розыгрышами
        giveaways_dict = {
            "Для apscheduler": [],
            "Для мгновенного участия": []
        }

        for giveaway in giveaways:
            finish_time = datetime.fromisoformat(giveaway.finish_date)
            time_remaining = finish_time - datetime.now()

            if time_remaining.total_seconds() > 3600:
                giveaways_dict["Для apscheduler"].append({
                    "id": giveaway.id,
                    "finish_date": giveaway.finish_date,
                    'channels_count': len(giveaway.channels_list.split(', '))
                })
            elif time_remaining.total_seconds() <= 3600:
                giveaways_dict["Для мгновенного участия"].append({
                    "channels_list": giveaway.channels_list
                })

        return giveaways_dict


async def get_giveaway_channels(giveaway_id: int) -> str:
    async with async_session() as session:
        result = await session.execute(select(Giveaway.channels_list).where(Giveaway.id == giveaway_id))
        channels_list = result.scalar_one_or_none()

        channels = channels_list.split(', ')
        join_command_text = "/join\n" + "\n".join(channels)
        return join_command_text


async def db_dell_giveaway(giveaway_id):
    async with async_session() as session:
        await session.execute(
            update(Giveaway).where(Giveaway.id == giveaway_id).values(is_used="0")
        )
        await session.commit()