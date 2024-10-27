import re
import logging
import os
from api_requests import api_request
from vectorization import vectorize_query, find_best_match  # Импортируем find_best_match

def initialize_bot(bot, embeddings, iam_token):
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        bot.send_message(message.chat.id, "Здравствуйте. Чем я могу помочь? Напишите свой вопрос.")

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
                    image_path = f"pictures/Рисунок {figure_number}.png"

                    # Проверяем, существует ли файл рисунка
                    if os.path.exists(image_path):
                        with open(image_path, 'rb') as image_file:
                            bot.send_photo(message.chat.id, image_file)
                    else:
                        logging.warning(f"Рисунок {figure_number} не найден в папке pictures.")
            else:
                logging.error("Не удалось получить ответ от YandexGPT.")
                bot.send_message(message.chat.id, "Извините, я не смог обработать ваш запрос.")
        else:
            logging.error("Не удалось векторизовать запрос.")
            bot.send_message(message.chat.id, "Извините, возникла ошибка при обработке вашего запроса.")
