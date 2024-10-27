import os
import telebot
import logging
from background import keep_alive
from document_handler import extract_text_from_docx
from vectorization import vectorize_text, vectorize_query, find_best_match
from api_requests import api_request
from bot_handler import initialize_bot
import pictures

pictures.main()
# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота
bot = telebot.TeleBot('8003897796:AAE8G42hzy8kL6UOYxENjzoWYma3pwsMcHQ')

# Путь к вашему DOCX файлу
docx_path = r"data.docx"
text_to_vectorize = extract_text_from_docx(docx_path)

if text_to_vectorize:
    # URL для получения IAM токена
    url_token = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'
    data_token = {
        "yandexPassportOauthToken": "y0_AgAAAABEeWftAATuwQAAAAEV6zpNAABgLB6qHaBLyJtPaCxem9CH05uS_A"
    }

    # Получение IAM токена
    token_response = api_request(url_token, {}, data_token)
    iam_token = token_response.get('iamToken') if token_response else None

    if iam_token:
        # Векторизация текста
        embeddings = vectorize_text(text_to_vectorize, iam_token)
        logging.info("Полученные эмбеддинги: %s", embeddings)

        # Инициализация бота
        initialize_bot(bot, embeddings, iam_token)

    else:
        logging.error("Не удалось получить IAM токен.")
else:
    logging.error("Не удалось извлечь текст из файла.")

# Запуск Flask-сервера
keep_alive()

# Запуск опроса
bot.polling(non_stop=True, interval=0)
