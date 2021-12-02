import requests
import os
import logging
import sys
import time
import telegram
from http import HTTPStatus
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
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        homework_statuses = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
        if homework_statuses.status_code != HTTPStatus.OK:
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
    try:
        homeworks_list = response['homeworks']
    except KeyError as error:
        error_message = f'Ошибка доступа по ключу homeworks: {error}'
        logger.error(error_message)
        raise Exception(error_message)
    if homeworks_list is None:
        error_message = 'В ответе API нет словаря с домашками'
        logger.error(error_message)
        raise Exception(error_message)
    if len(homeworks_list) == 0:
        error_message = 'За последнее время нет домашек'
        logger.error(error_message)
        raise Exception(error_message)
    if not isinstance(homeworks_list, list):
        error_message = 'В ответе API домашки представлены не списком'
        logger.error(error_message)
        raise Exception(error_message)
    return homeworks_list


def parse_status(homework):
    """Готовит ответ об измненении статуса."""
    try:
        homework_name = homework.get('homework_name')
    except KeyError as error:
        error_message = f'Ошибка доступа по ключу homework_name: {error}'
        logger.error(error_message)
    try:
        homework_status = homework.get('status')
    except KeyError as error:
        error_message = f'Ошибка доступа по ключу status: {error}'
        logger.error(error_message)

    verdict = HOMEWORK_STATUSES[homework_status]
    if verdict is None:
        error_message = 'Неизвестный статус домашки'
        logger.error(error_message)
        raise Exception(error_message)
    logger.info(f'итоговый результат: {verdict}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяет наличие токенов."""
    return all([TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, PRACTICUM_TOKEN])


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        error_message = 'Отсутствует необходимая переменная среды'
        logger.critical(error_message)
        raise Exception(error_message)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time() - 604800)
    previous_status = None
    previous_error = None
    while True:
        try:
            response = get_api_answer(current_timestamp)
        except Exception as error:
            if str(error) != previous_error:
                previous_error = str(error)
                send_message(bot, error)
            logging.error(error)
            time.sleep(RETRY_TIME)
            continue
        try:
            homeworks = check_response(response)
            hw_status = homeworks[0].get('status')
            if hw_status != previous_status:
                previous_status = hw_status
                message = parse_status(homeworks[0])
                send_message(bot, message)
            else:
                logger.debug('Обновления статуса нет')

            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            if previous_error != str(error):
                previous_error = str(error)
                send_message(bot, message)
            logger.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
