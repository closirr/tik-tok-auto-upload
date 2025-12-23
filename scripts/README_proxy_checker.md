# Чекер прокси Webshare.io

Набор скриптов для проверки работоспособности прокси серверов Webshare.io.

## Файлы

- `check_webshare_proxies.py` - Основной чекер для массовой проверки всех прокси
- `quick_proxy_test.py` - Быстрая проверка одного прокси
- `proxy_check_results.json` - Результаты последней проверки (создается автоматически)

## Использование

### Массовая проверка всех прокси

```bash
cd scripts
python check_webshare_proxies.py
```

Скрипт проверит все прокси из списка и выведет:
- Статус каждого прокси (работает/не работает)
- IP адрес и время отклика для рабочих прокси
- Геолокацию (если доступно)
- Сводную статистику
- Сохранит результаты в JSON файл

### Быстрая проверка одного прокси

```bash
cd scripts
python quick_proxy_test.py "http://username:password@p.webshare.io:80"
```

Пример:
```bash
python quick_proxy_test.py "http://emaschipx-rotate:emaschipx@p.webshare.io:80"
```

## Особенности

- **Асинхронная проверка** - все прокси проверяются параллельно для скорости
- **Множественные проверки** - использует несколько сервисов для определения IP
- **Геолокация** - показывает страну и город прокси
- **Время отклика** - измеряет скорость прокси
- **Сохранение результатов** - все результаты сохраняются в JSON для анализа

## Требования

```bash
pip install aiohttp
```

## Формат результатов

Результаты сохраняются в `proxy_check_results.json`:

```json
{
  "timestamp": "2025-01-15 14:30:00",
  "total_proxies": 14,
  "working_count": 12,
  "results": [
    {
      "proxy_name": "emaschipx-rotate",
      "status": "working",
      "ip": "192.168.1.1",
      "location": "United States, New York",
      "response_time": 1.23
    }
  ]
}
```

## Интеграция с основным проектом

Рабочие прокси можно использовать в основном проекте через переменные окружения в `.env`:

```
PROXY_SERVER=p.webshare.io
PROXY_PORT=80
PROXY_USERNAME=emaschipx-rotate
PROXY_PASSWORD=emaschipx
```