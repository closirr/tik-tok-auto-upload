import asyncio
from facebook_manager import FacebookManager

async def main():
    print("Запуск проверки Facebook Cookies")
    print("=" * 50)
    
    # Создаем экземпляр менеджера Facebook
    manager = FacebookManager()
    
    # Получаем список файлов с куками для обработки
    cookie_files = manager.cookies_loader.get_cookie_files()
    
    if not cookie_files:
        print("Не найдено файлов с куками для обработки")
        print("Убедитесь, что в папке facebook_cookies есть файлы без префиксов valid_, invalid_ или password_")
        return
    
    print(f"Найдено {len(cookie_files)} файлов с куками для обработки")
    
    valid_count = 0
    invalid_count = 0
    password_count = 0
    skipped_count = 0
    
    # Обрабатываем каждый файл с куками
    for i, cookie_file in enumerate(cookie_files):
        result = await manager.process_account(cookie_file)
        
        if result == 'valid':
            valid_count += 1
        elif result == 'password':
            password_count += 1
        elif result == 'invalid':
            invalid_count += 1
        else:  # skipped
            skipped_count += 1
        
        # Задержка между аккаунтами
        if i < len(cookie_files) - 1:
            delay = 3
            print(f"Ожидание {delay} секунд перед следующим аккаунтом...")
            await asyncio.sleep(delay)
    
    print("\n" + "=" * 50)
    print("ИТОГИ ПРОВЕРКИ:")
    print(f"  Валидных: {valid_count}")
    print(f"  Требуют пароль: {password_count}")
    print(f"  Невалидных: {invalid_count}")
    print(f"  Пропущено (ошибки соединения): {skipped_count}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
