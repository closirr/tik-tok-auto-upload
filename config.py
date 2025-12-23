import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

# Настройки прокси из .env
# Playwright требует определенный формат для прокси
# https://playwright.dev/python/docs/api/class-browsertype#browser-type-launch-option-proxy
PROXY = {
    'server': f"http://{os.getenv('PROXY_SERVER')}:{os.getenv('PROXY_PORT')}",
    'username': os.getenv('PROXY_USERNAME'),
    'password': os.getenv('PROXY_PASSWORD')
}

# URL для обновления IP прокси из .env
PROXY_REFRESH_URL = os.getenv('PROXY_REFRESH_URL')

# Флаг использования ротации прокси
# Если True - используется режим ротации (каждый запрос через новый IP)
# Если False - используется обновление IP через API
USE_PROXY_ROTATION_ENV = os.getenv('USE_PROXY_ROTATION', 'true').lower()
USE_PROXY_ROTATION = USE_PROXY_ROTATION_ENV == 'true'

# Другие конфигурации
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
DEFAULT_LOCALE = 'ru-RU'

# Директории по умолчанию
DEFAULT_COOKIES_DIR = 'cookies'
DEFAULT_VIDEOS_DIR = 'videos'
DEFAULT_SCREENSHOTS_DIR = 'screenshots'

# Токен для ipinfo.io API
IPINFO_TOKEN = os.getenv('IPINFO_TOKEN')

# Приоритет обработки файлов с куками
# Если True - сначала обрабатываются файлы с префиксом valid_, потом остальные
# Если False - обрабатываются только необработанные файлы (без префиксов valid_/invalid_)

PROCESS_VALID_FIRST = 'false' 