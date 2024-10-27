import requests
import logging

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