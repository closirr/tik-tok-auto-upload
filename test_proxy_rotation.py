import asyncio
from playwright.async_api import async_playwright
import config
import os

async def test_proxy_rotation():
    """Тестирует работу прокси в режиме ротации"""
    print("Тестирование прокси в режиме ротации...")
    print(f"Настройки прокси из конфигурации:")
    print(f"- Сервер: {config.PROXY['server']}")
    print(f"- Логин: {config.PROXY['username']}")
    print(f"- Пароль: {'*' * len(config.PROXY['password'])}")
    print(f"- Режим ротации: {'Включен' if config.USE_PROXY_ROTATION else 'Выключен'}")
    
    # Создаем директорию для скриншотов, если её нет
    if not os.path.exists('proxy_rotation_test'):
        os.makedirs('proxy_rotation_test')
    
    try:
        async with async_playwright() as p:
            # Запускаем браузер
            browser = await p.firefox.launch(headless=False)
            
            # Сначала проверим IP без прокси для сравнения
            print("\nПроверка без прокси:")
            context_no_proxy = await browser.new_context()
            page_no_proxy = await context_no_proxy.new_page()
            
            try:
                await page_no_proxy.goto("https://api.ipify.org", wait_until='load', timeout=30000)
                ip_text = await page_no_proxy.content()
                print(f"IP без прокси: {ip_text}")
                await page_no_proxy.screenshot(path="proxy_rotation_test/no_proxy_ip.png")
            except Exception as e:
                print(f"Ошибка при проверке IP без прокси: {str(e)}")
            
            await context_no_proxy.close()
            
            # Делаем несколько запросов подряд, создавая новый контекст для каждого запроса
            for i in range(5):
                print(f"\nЗапрос #{i+1}:")
                
                # Создаем новый контекст с прокси для каждого запроса
                context = await browser.new_context(
                    proxy=config.PROXY,
                    locale=config.DEFAULT_LOCALE,
                    user_agent=config.DEFAULT_USER_AGENT
                )
                
                page = await context.new_page()
                
                try:
                    # Проверяем текущий IP
                    await page.goto("https://api.ipify.org", wait_until='load', timeout=30000)
                    ip_text = await page.content()
                    print(f"IP с прокси: {ip_text}")
                    
                    # Делаем скриншот
                    screenshot_path = f"proxy_rotation_test/ip_check_{i+1}.png"
                    await page.screenshot(path=screenshot_path)
                    print(f"Скриншот сохранен: {screenshot_path}")
                    
                    # Закрываем контекст
                    await context.close()
                    
                    # Ждем немного перед следующим запросом
                    await asyncio.sleep(3)
                    
                except Exception as e:
                    print(f"Ошибка при проверке IP: {str(e)}")
                    await context.close()
            
            # Ждем некоторое время перед закрытием браузера
            print("\nТестирование завершено. Браузер останется открытым для 5 секунд.")
            await asyncio.sleep(5)
            
    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_proxy_rotation()) 