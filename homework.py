import requests
import os
import logging
import sys
import time

from logging.handlers import StreamHandler
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s - %(name)s',
    level=logging.DEBUG,
    filename='main.log',
    filemode='w'
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(sys.stdout)
logger.addHandler(handler)

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляет сообщения в Телеграм."""
    try:
        logger.info(f'Бот отправил сообщение {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logger.error(f'Ошибка при отправке сообщения. {error}')


def get_api_answer(current_timestamp):
    """Получает ответ от API об изменениях домашней работы."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if homework_statuses.raise_for_status() != 200:
            logging.error('Ошибка API')
            raise Exception('Эндпоинт недоступен')
        return homework_statuses.json()
    except requests.exceptions.RequestException:
        error_message = 'Не удалось получить доступ к API'
        logging.error(
            error_message,
            exc_info=True
        )


def check_response(response):
    """Проверяет если есть обновление, возвращает библиотеку."""
    try:
        homework_list = response.get('homeworks')
    except KeyError as error:
        if response.get('homeworks') not in response:
            error_message = f'Словаре отсутствует ключ "homeworks" {error}'
            logging.error(error_message)
    else:
        homework = homework_list[0]
        return homework


def parse_status(homework):
    """Готовит ответ об измненении статуса."""
    try:
        homework_name = homework.get('homework_name')
    except KeyError as error:
        error_message = f'В словаре нет ключа homework_name {error}'
        logging.error(error_message)
    try:
        homework_status = homework.get('status')
    except KeyError as error:
        error_message = f'В словаре нет ключа status {error}'
        logging.error(error_message)
    if homework_status not in HOMEWORK_STATUSES:
        error_message = 'Получен неизвестный статус'
        logging.error(error_message)
        raise Exception(error_message)
    else:
        verdict = HOMEWORK_STATUSES.get(homework_status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие токенов."""
    return all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit()
    bot = Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    errors = True
    while True:
        try:
            response = get_api_answer(current_timestamp)
            response_checked = check_response(response)
            if response_checked:
                message = parse_status(response_checked)
                send_message(bot, message)
            time.sleep(RETRY_TIME)
            current_timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if errors:
                errors = True
                send_message(bot, message)
            logging.error(message, exc_info=True)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
