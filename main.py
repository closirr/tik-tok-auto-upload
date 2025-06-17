import asyncio
from tiktok_manager import TikTokManager
from tiktok_cookies_loader import CookiesLoader

async def main():
    print("Запуск TikTok Auto Upload")
    print("=" * 50)
    
    # Создаем экземпляр менеджера TikTok
    manager = TikTokManager()
    
    # Создаем экземпляр загрузчика cookies
    cookies_loader = CookiesLoader()
    
    # Получаем список файлов с куками для обработки
    cookie_files = cookies_loader.get_cookie_files()
    
    if not cookie_files:
        print("Не найдено файлов с куками для обработки")
        return
    
    print(f"Найдено {len(cookie_files)} файлов с куками для обработки")
    
    # Обрабатываем каждый файл с куками
    for cookie_file in cookie_files:
        print(f"Обработка {cookie_file}...")
        await manager.process_account(cookie_file)
        print(f"Обработка {cookie_file} завершена")
    
    print("=" * 50)
    print("Обработка всех файлов с куками завершена")


if __name__ == "__main__":
    asyncio.run(main()) 