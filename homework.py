import requests
import os
import logging
import sys
import time

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
handler = logging.StreamHandler(sys.stdout)
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
        if homework_statuses.status_code != 200:
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
    """Проверяет ответ на корректность."""
    homeworks = response['homeworks']
    if not homeworks:
        logger.error('задание отсутствует')
    for homework in homeworks:
        status = homework.get('status')
        if status in HOMEWORK_STATUSES:
            return homework
        else:
            error_message = 'В словаре отсутствует ключ "homeworks"'
            logger.error(error_message)
            raise Exception(error_message)
    return []


def parse_status(homework):
    """Готовит ответ об измненении статуса."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    verdict = HOMEWORK_STATUSES[homework_status]
    if verdict is None:
        error_message = 'Неизвестный статус домашки'
        logger.error(error_message)
        raise Exception(error_message)
    logger.info(f'итоговый результат: {verdict}')
    return f'Изменился статус проверки работы “{homework_name}“. {verdict}'


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
