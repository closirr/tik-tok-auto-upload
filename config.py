import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

# Флаг отключения прокси (если True - прокси не используется)
PROXY_DISABLED = os.getenv('PROXY_DISABLED', 'false').lower() == 'true'

# Режим прокси: 'free' для бесплатных прокси, 'paid' для платных
PROXY_MODE = os.getenv('PROXY_MODE', 'free').lower()

# Настройки для платных прокси (старая конфигурация)
PAID_PROXY = {
    'server': f"http://{os.getenv('PROXY_SERVER')}:{os.getenv('PROXY_PORT')}" if os.getenv('PROXY_SERVER') else None,
    'username': os.getenv('PROXY_USERNAME'),
    'password': os.getenv('PROXY_PASSWORD')
}

# Настройки для бесплатных прокси (оптимизированные)
FREE_PROXY_CONFIG = {
    'country_id': os.getenv('FREE_PROXY_COUNTRIES', 'US,GB,DE,CA,AU,NL,FR').split(','),  # Больше стран для выбора
    'https': os.getenv('FREE_PROXY_HTTPS', 'false').lower() == 'true',      # Требовать HTTPS
    'anonym': os.getenv('FREE_PROXY_ANONYM', 'true').lower() == 'true',     # Требовать анонимность
    'timeout': float(os.getenv('FREE_PROXY_TIMEOUT', '4.0')),              # Уменьшенный таймаут для быстрого отсева
    'pool_size': int(os.getenv('FREE_PROXY_POOL_SIZE', '3')),              # Меньший пул для экономии времени
    'cache_time': int(os.getenv('FREE_PROXY_CACHE_TIME', '180'))           # Уменьшенное время кэша (3 мин)
}

# Основная конфигурация прокси (выбирается по PROXY_MODE)
if PROXY_DISABLED:
    PROXY = None
    USE_FREE_PROXY = False
elif PROXY_MODE == 'free':
    PROXY = None  # Будет устанавливаться динамически через FreeProxyManager
    USE_FREE_PROXY = True
else:
    PROXY = PAID_PROXY
    USE_FREE_PROXY = False

# URL для обновления IP прокси из .env (только для платных прокси)
PROXY_REFRESH_URL = os.getenv('PROXY_REFRESH_URL')

# Флаг использования ротации прокси
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

PROCESS_VALID_FIRST = False 