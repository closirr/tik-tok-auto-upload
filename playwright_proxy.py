import asyncio
from playwright.async_api import async_playwright
import json
import os
import glob

def load_cookies(filename='cookies.json'):
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

def get_first_video(folder_path='videos'):
    """Получает путь к первому видео в указанной папке."""
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"Папка {folder_path} создана. Пожалуйста, добавьте в неё видео.")
        return None
    
    video_files = glob.glob(os.path.join(folder_path, '*.*'))
    video_formats = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
    
    # Фильтрация только видео файлов
    video_files = [f for f in video_files if os.path.splitext(f)[1].lower() in video_formats]
    
    if not video_files:
        print(f"В папке {folder_path} не найдено видео файлов.")
        return None
    
    # Сортировка по имени и выбор первого файла
    video_files.sort()
    return video_files[0]

async def upload_video(page, video_path):
    """
    Загружает видео на TikTok Studio.
    
    Args:
        page: Объект страницы Playwright
        video_path: Путь к видеофайлу для загрузки
    
    Returns:
        bool: True, если загрузка запущена успешно, False в случае ошибки
    """
    try:
        # Найдем input для загрузки файла
        file_input = await page.query_selector('input[type="file"]')
        
        if file_input:
            # Используем абсолютный путь к видео
            abs_video_path = os.path.abspath(video_path)
            print(f"Загружаем видео: {abs_video_path}")
            
            # Устанавливаем файл в поле ввода
            await file_input.set_input_files(abs_video_path)
            
            print("Видео выбрано для загрузки")
            
            # Делаем скриншот после выбора файла
            await page.wait_for_timeout(2000)
            await page.screenshot(path="tiktok_file_selected.png")
            
            # Ждем достаточное время для завершения загрузки и обработки
            await page.wait_for_timeout(30000)  # 30 секунд
            return True
            
        else:
            print("Не удалось найти поле для загрузки файла")
            return False
    
    except Exception as e:
        print(f"Ошибка при загрузке видео: {str(e)}")
        await page.screenshot(path="tiktok_upload_error.png")
        return False

async def run():
    cookies = load_cookies()
    
    # Получаем путь к первому видео
    video_path = get_first_video()
    if not video_path:
        print("Не удалось найти видео для загрузки. Убедитесь, что в папке videos есть видео файлы.")
        return

    proxy = {
        'server': 'http://109.236.82.42:9999',
        'username': 'xefrudrjaz-corp.res-country-GB-hold-session-session-6850a0db0a053',
        'password': '8tnmD7aIgSbBHSmD'
    }

    async with async_playwright() as p:
        browser = await p.firefox.launch(headless=False)

        context = await browser.new_context(
            proxy=proxy,
            locale='ru-RU',
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
        )

        # Установить cookies сразу после создания контекста
        await context.add_cookies(cookies)
        page = await context.new_page()
        await page.goto("https://tiktok.com", wait_until='load')
        await page.wait_for_timeout(5000)  # Ждем 5 секунд для загрузки страницы
        await page.goto("https://www.tiktok.com/tiktokstudio/upload", wait_until='load')
        await page.wait_for_timeout(5000)  # Ждем 5 секунд для загрузки страницы

        # Скриншот страницы загрузки
        await page.screenshot(path="tiktok_upload_page.png")
        
        # Загружаем видео
        upload_success = await upload_video(page, video_path)
        
        if upload_success:
            print("Загрузка видео запущена успешно")
        else:
            print("Не удалось запустить загрузку видео")
        5
        # Оставляем браузер открытым
        await page.wait_for_timeout(500000)  # 500 секунд

asyncio.run(run())
