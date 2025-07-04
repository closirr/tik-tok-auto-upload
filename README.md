# TikTok Auto Upload

Автоматическое загрузка и публикация видео на TikTok с использованием разных аккаунтов (через cookies).

## Описание

Программа автоматически обрабатывает все файлы cookies из папки `cookies`, последовательно:
1. Обновляет IP-адрес прокси перед работой с каждым аккаунтом
2. Загружает cookies из файла
3. Проверяет валидность cookies (успешность авторизации)
4. Загружает видео из папки `videos` на TikTok Studio
5. Автоматически публикует видео, нажимая на кнопку "Опубликовать"
6. Помечает обработанные cookies как `valid_` или `invalid_`

## Требования

- Python 3.8+
- Playwright
- Firefox браузер
- Библиотеки: aiohttp, asyncio

## Установка

1. Установите зависимости:
```bash
pip install -r requirements.txt
playwright install firefox
```

2. Подготовьте файлы:
   - Поместите видео для загрузки в папку `videos/`
   - Поместите файлы с cookies в папку `cookies/`

## Использование

Запустите программу командой:

```bash
python main.py
```

## Структура проекта

- `main.py` - точка входа в программу
- `tiktok_manager.py` - основной класс для управления процессом загрузки и публикации видео
- `tiktok_cookies_loader.py` - класс для работы с cookies файлами
- `cookies/` - папка с файлами cookies
- `videos/` - папка с видео для загрузки

## Функциональность

### Управление cookies
- Поддержка различных форматов cookies (JSON, Netscape, текстовый)
- Автоматическая обработка всех файлов cookies в папке
- Пометка файлов как valid_ или invalid_ в зависимости от результата

### Управление прокси
- Автоматическое обновление IP-адреса прокси перед работой с каждым аккаунтом
- Использование API ASocks для смены IP

### Загрузка и публикация видео
- Автоматическая загрузка видео на TikTok Studio
- Заполнение необходимых полей (описание, хэштеги)
- Автоматическая публикация видео через нажатие кнопки "Опубликовать"
- Проверка успешности публикации

## Примечания

- Обработанные файлы cookies получают префиксы `valid_` или `invalid_`
- При повторном запуске, уже обработанные файлы пропускаются
- Для загрузки используется первое видео из папки `videos/`
- Перед каждым аккаунтом обновляется IP-адрес прокси для безопасности 