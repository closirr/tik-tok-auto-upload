import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

# Настройки прокси из .env
PROXY = {
    'server': os.getenv('PROXY_SERVER'),
    'username': os.getenv('PROXY_USERNAME'),
    'password': os.getenv('PROXY_PASSWORD')
}

# URL для обновления IP прокси из .env
PROXY_REFRESH_URL = os.getenv('PROXY_REFRESH_URL')

# Другие конфигурации
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
DEFAULT_LOCALE = 'ru-RU'

# Директории по умолчанию
DEFAULT_COOKIES_DIR = 'cookies'
DEFAULT_VIDEOS_DIR = 'videos'
DEFAULT_SCREENSHOTS_DIR = 'screenshots' 