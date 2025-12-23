"""
Скрипт для запуска браузера с валидным TikTok аккаунтом.
Позволяет выбрать аккаунт из списка валидных и опционально включить прокси.
"""

import asyncio
import os
import sys
import glob

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright
from tiktok_cookies_loader import CookiesLoader
import config


def get_valid_cookie_files(cookies_dir='cookies'):
    """Получает список валидных cookie файлов"""
    pattern = os.path.join(cookies_dir, 'valid_*.txt')
    files = glob.glob(pattern)
    return sorted(files)


def display_accounts(cookie_files):
    """Отображает список аккаунтов для выбора"""
    print("\n" + "=" * 60)
    print("ДОСТУПНЫЕ ВАЛИДНЫЕ АККАУНТЫ TIKTOK")
    print("=" * 60)
    
    for i, file_path in enumerate(cookie_files, 1):
        filename = os.path.basename(file_path)
        # Убираем префикс valid_ и расширение для красивого отображения
        display_name = filename.replace('valid_extracted_', '').replace('.txt', '')
        print(f"  [{i}] {display_name}")
    
    print("=" * 60)
    print(f"  [0] Выход")
    print("=" * 60)


def select_account(cookie_files):
    """Позволяет пользователю выбрать аккаунт"""
    while True:
        try:
            choice = input("\nВведите номер аккаунта: ").strip()
            if choice == '0':
                return None
            
            index = int(choice) - 1
            if 0 <= index < len(cookie_files):
                return cookie_files[index]
            else:
                print(f"Ошибка: введите число от 1 до {len(cookie_files)}")
        except ValueError:
            print("Ошибка: введите корректное число")


def ask_proxy():
    """Спрашивает пользователя о включении прокси"""
    print("\n" + "-" * 40)
    print("ПРОКСИ:")
    print("  [1] Включить прокси")
    print("  [2] Без прокси")
    print("-" * 40)
    
    while True:
        choice = input("Выберите (1/2): ").strip()
        if choice == '1':
            return True
        elif choice == '2':
            return False
        else:
            print("Введите 1 или 2")


async def launch_browser(cookie_file, use_proxy=False):
    """Запускает браузер с указанными куками"""
    print(f"\nЗагрузка куков из: {os.path.basename(cookie_file)}")
    
    # Загружаем куки
    cookies_loader = CookiesLoader()
    cookies = cookies_loader.load_cookies(cookie_file)
    
    if not cookies:
        print("Ошибка: не удалось загрузить куки из файла")
        return
    
    print(f"Загружено {len(cookies)} куков")
    
    # Настройки прокси
    proxy_settings = None
    if use_proxy:
        proxy_settings = config.PROXY
        print(f"\nПрокси включен:")
        print(f"  Сервер: {proxy_settings['server']}")
        print(f"  Логин: {proxy_settings['username']}")
    else:
        print("\nПрокси отключен")
    
    print("\nЗапуск браузера...")
    print("-" * 40)
    print("Браузер будет открыт. Закройте его для завершения скрипта.")
    print("-" * 40)
    
    async with async_playwright() as p:
        # Запускаем Firefox
        browser = await p.firefox.launch(headless=False)
        
        # Создаем контекст с прокси или без
        context_options = {
            'locale': config.DEFAULT_LOCALE,
            'user_agent': config.DEFAULT_USER_AGENT
        }
        
        if use_proxy and proxy_settings:
            context_options['proxy'] = proxy_settings
        
        context = await browser.new_context(**context_options)
        
        # Добавляем куки
        await context.add_cookies(cookies)
        
        # Открываем страницу TikTok
        page = await context.new_page()
        await page.goto('https://www.tiktok.com/')
        
        print("\nБраузер запущен! Вы можете работать с аккаунтом.")
        print("Для завершения закройте окно браузера.")
        
        # Ждем пока браузер не будет закрыт
        try:
            await page.wait_for_event('close', timeout=0)
        except:
            pass
        
        await browser.close()
    
    print("\nБраузер закрыт. До свидания!")


async def main():
    """Главная функция"""
    print("\n" + "=" * 60)
    print("  ЗАПУСК БРАУЗЕРА С TIKTOK АККАУНТОМ")
    print("=" * 60)
    
    # Получаем список валидных аккаунтов
    cookie_files = get_valid_cookie_files()
    
    if not cookie_files:
        print("\nОшибка: не найдено валидных аккаунтов!")
        print("Валидные аккаунты должны находиться в папке 'cookies'")
        print("и иметь префикс 'valid_'")
        return
    
    print(f"\nНайдено валидных аккаунтов: {len(cookie_files)}")
    
    # Показываем список и выбираем аккаунт
    display_accounts(cookie_files)
    selected_file = select_account(cookie_files)
    
    if selected_file is None:
        print("\nВыход из программы.")
        return
    
    # Спрашиваем про прокси
    use_proxy = ask_proxy()
    
    # Запускаем браузер
    await launch_browser(selected_file, use_proxy)


if __name__ == '__main__':
    asyncio.run(main())
