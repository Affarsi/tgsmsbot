import subprocess
import time

from loguru import logger

# настраиваем логи
logger.add(
    'bot/data/debug.log',
    format="{time:DD-MMM-YYYY HH:mm:ss.SSS} | {level} | {name}:{function}:{line} - {message}",
    level="DEBUG",
    rotation='10 MB'
)


def run_main():
    process = subprocess.Popen(['python3', 'main.py'])
    process.wait()
    if process.returncode != 0:
        logger.error(f"main.py завершился с ошибкой, return_code = {process.returncode}")
        run_main()

while True:
    run_main()
    time.sleep(1)  # Пауза между проверками
