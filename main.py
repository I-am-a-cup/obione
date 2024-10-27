import os
import telebot
import requests
import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from docx import Document
import logging
from flask import Flask
from threading import Thread
import pictures

# Запуск функции main из pictures.py
pictures.main()
# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Функции для работы с документами и API
def extract_text_from_docx(docx_path):
    try:
        doc = Document(docx_path)
        return '\n'.join(paragraph.text for paragraph in doc.paragraphs)
    except Exception as e:
        logging.error(f"Ошибка при извлечении текста: {e}")
        return ""

def split_text_with_overlap(text, chunk_size=2048, overlap_size=512):
    sentences = re.split(r'(?<=[.!?]) +', text)
    chunks, current_chunk = [], ""

    for sentence in sentences:
        if len(current_chunk) + len(sentence) + 1 > chunk_size:
            chunks.append(current_chunk.strip())
            current_chunk = " ".join(current_chunk.split()[-overlap_size:] + [sentence])
        else:
            current_chunk += " " + sentence if current_chunk else sentence

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

def api_request(url, headers, data):
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        logging.error(f"HTTP ошибка: {err}")
        return None
    except Exception as e:
        logging.error(f"Ошибка при выполнении запроса: {e}")
        return None

def vectorize_text(text, iam_token):
    url_embedding = 'https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding'
    headers_embedding = {
        'Authorization': f'Bearer {iam_token}',
        'Content-Type': 'application/json'
    }

    embeddings = []
    chunks = split_text_with_overlap(text)
    for part in chunks:
        if part.strip():
            data_embedding = {
                "modelUri": "emb://b1gjp5vama10h4due384/text-search-doc/latest",
                "text": part
            }
            logging.info("Данные для векторизации: %s", data_embedding)

            result = api_request(url_embedding, headers_embedding, data_embedding)
            if result and 'embedding' in result:
                embeddings.append((result['embedding'], part))
    return embeddings

def vectorize_query(query, iam_token):
    url_embedding = 'https://llm.api.cloud.yandex.net/foundationModels/v1/textEmbedding'
    headers_embedding = {
        'Authorization': f'Bearer {iam_token}',
        'Content-Type': 'application/json'
    }

    data_embedding = {
        "modelUri": "emb://b1gjp5vama10h4due384/text-search-doc/latest",
        "text": query
    }

    result = api_request(url_embedding, headers_embedding, data_embedding)
    return result.get('embedding') if result and 'embedding' in result else None

def find_best_match(query_embedding, embeddings):
    similarities = [
        (cosine_similarity([query_embedding], [embedding])[0][0], text)
        for embedding, text in embeddings
    ]
    similarities.sort(reverse=True, key=lambda x: x[0])
    return similarities[0][1] if similarities else "Нет подходящего ответа."

# Инициализация Flask
app = Flask('')

@app.route('/')
def home():
    return "I'm alive"

def run():
    app.run(host='0.0.0.0', port=80)

def keep_alive():
    t = Thread(target=run)
    t.start()

# Инициализация бота
bot = telebot.TeleBot('8003897796:AAE8G42hzy8kL6UOYxENjzoWYma3pwsMcHQ')  # Замените на свой токен

# Удаление существующего вебхука перед началом опроса
bot.remove_webhook()

# Путь к вашему DOCX файлу
docx_path = r"data.docx"
text_to_vectorize = extract_text_from_docx(docx_path)

if text_to_vectorize:
    # URL для получения IAM токена
    url_token = 'https://iam.api.cloud.yandex.net/iam/v1/tokens'
    data_token = {
        "yandexPassportOauthToken": "y0_AgAAAABEeWftAATuwQAAAAEV6zpNAABgLB6qHaBLyJtPaCxem9CH05uS_A"  # Замените на свой токен
    }

    # Получение IAM токена
    token_response = api_request(url_token, {}, data_token)
    iam_token = token_response.get('iamToken') if token_response else None

    if iam_token:
        # Векторизация текста
        embeddings = vectorize_text(text_to_vectorize, iam_token)
        logging.info("Полученные эмбеддинги: %s", embeddings)

        # Обработчик команды /start
        @bot.message_handler(commands=['start'])
        def send_welcome(message):
            bot.send_message(message.chat.id, "Здравствуйте. Чем я могу помочь? Напишите свой вопрос.")

        # Обработчик текстовых сообщений
        @bot.message_handler(content_types=['text'])
        def get_text_message(message):
            user_query = message.text
            query_embedding = vectorize_query(user_query, iam_token)

            if query_embedding is not None:
                best_match = find_best_match(query_embedding, embeddings)
                logging.info("Лучший ответ: %s", best_match)

                # Подготовка и выполнение запроса к YandexGPT
                url_gpt = 'https://llm.api.cloud.yandex.net/foundationModels/v1/completion'
                headers = {
                    'Authorization': f'Bearer {iam_token}',
                    'Content-Type': 'application/json'
                }

                data_gpt = {
                    "modelUri": "gpt://b1gjp5vama10h4due384/yandexgpt/latest",
                    "completionOptions": {
                        "stream": False,
                        "temperature": 0.6,
                        "maxTokens": 2000
                    },
                    "messages": [
                        {
                            "role": "system",
                            "text": f"Ты — помощник. Ответь на вопрос, опираясь исключительно на предоставленное руководство пользователя: {best_match}. Если в руководстве есть рисунок, укажи его номер в формате Рисунок № [номер]"
                        },
                        {
                            "role": "user",
                            "text": user_query
                        }
                    ]
                }

                response_gpt = api_request(url_gpt, headers, data_gpt)

                # Извлекаем нужный текст
                if response_gpt and 'result' in response_gpt and 'alternatives' in response_gpt['result']:
                    output_text = response_gpt['result']['alternatives'][0]['message']['text']

                    # Удаляем упоминания рисунков и оставшиеся скобки
                    output_text = re.sub(r'\(Рисунок\s*№?\s*\d*\)|Рисунок\s*№?\s*\d*|\(\)', '', output_text).strip()

                    bot.send_message(message.from_user.id, output_text)

                    # Проверка на наличие рисунка в оригинальном тексте
                    match = re.search(r'Рисунок\s*№?\s*(\d+)', response_gpt['result']['alternatives'][0]['message']['text'])
                    if match:
                        figure_number = match.group(1)
                        image_path = os.path.join("pictures", f"Рисунок {figure_number}.png")

                        # Проверяем, существует ли файл рисунка
                        if os.path.exists(image_path):
                            with open(image_path, 'rb') as image_file:
                                bot.send_photo(message.chat.id, image_file)
                        else:
                            logging.warning(f"Рисунок {figure_number} не найден в папке pictures.")
                else:
                    logging.error("Не удалось получить ответ от YandexGPT.")
            else:
                logging.error("Не удалось векторизовать запрос.")

    else:
        logging.error("Не удалось получить IAM токен.")
else:
    logging.error("Не удалось извлечь текст из файла.")

# Запуск Flask-сервера
keep_alive()
# Запуск опроса
bot.polling(non_stop=True, interval=0)
