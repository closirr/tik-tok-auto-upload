import asyncio
from playwright.async_api import async_playwright
import config
import os
import json

async def check_proxy_detailed():
    """Проверяет работу прокси с детальным выводом информации"""
    print("Детальная проверка прокси...")
    print(f"Настройки прокси из конфигурации:")
    print(f"- Сервер: {config.PROXY['server']}")
    print(f"- Логин: {config.PROXY['username']}")
    print(f"- Пароль: {'*' * len(config.PROXY['password'])}")
    print(f"- Режим ротации: {'Включен' if config.USE_PROXY_ROTATION else 'Выключен'}")
    
    # Создаем директорию для скриншотов, если её нет
    if not os.path.exists('proxy_check_detailed'):
        os.makedirs('proxy_check_detailed')
    
    try:
        async with async_playwright() as p:
            # Запускаем браузер
            browser = await p.firefox.launch(headless=False)
            
            # Проверка без прокси
            print("\n=== Проверка без прокси ===")
            context_no_proxy = await browser.new_context()
            page_no_proxy = await context_no_proxy.new_page()
            
            try:
                # Проверяем IP через ipinfo.io
                await page_no_proxy.goto("https://ipinfo.io/json", wait_until='load', timeout=30000)
                content = await page_no_proxy.content()
                # Извлекаем JSON из содержимого страницы
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                if json_start >= 0 and json_end > json_start:
                    ip_info = json.loads(content[json_start:json_end])
                    print("IP без прокси:")
                    print(f"- IP: {ip_info.get('ip', 'Неизвестно')}")
                    print(f"- Город: {ip_info.get('city', 'Неизвестно')}")
                    print(f"- Регион: {ip_info.get('region', 'Неизвестно')}")
                    print(f"- Страна: {ip_info.get('country', 'Неизвестно')}")
                    print(f"- Организация: {ip_info.get('org', 'Неизвестно')}")
                else:
                    print("Не удалось получить информацию об IP")
                
                # Делаем скриншот
                await page_no_proxy.screenshot(path="proxy_check_detailed/no_proxy.png")
                
                # Проверяем через whoer.com
                await page_no_proxy.goto("https://whoer.com", wait_until='load', timeout=30000)
                await page_no_proxy.wait_for_timeout(5000)  # Ждем загрузку страницы
                await page_no_proxy.screenshot(path="proxy_check_detailed/no_proxy_whoer.png")
                
            except Exception as e:
                print(f"Ошибка при проверке без прокси: {str(e)}")
            
            await context_no_proxy.close()
            
            # Проверка с прокси
            print("\n=== Проверка с прокси ===")
            
            # Создаем контекст с прокси
            try:
                context_with_proxy = await browser.new_context(
                    proxy=config.PROXY,
                    locale=config.DEFAULT_LOCALE,
                    user_agent=config.DEFAULT_USER_AGENT
                )
                
                page_with_proxy = await context_with_proxy.new_page()
                
                try:
                    # Проверяем IP через ipinfo.io
                    await page_with_proxy.goto("https://ipinfo.io/json", wait_until='load', timeout=30000)
                    content = await page_with_proxy.content()
                    # Извлекаем JSON из содержимого страницы
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        ip_info = json.loads(content[json_start:json_end])
                        print("IP с прокси:")
                        print(f"- IP: {ip_info.get('ip', 'Неизвестно')}")
                        print(f"- Город: {ip_info.get('city', 'Неизвестно')}")
                        print(f"- Регион: {ip_info.get('region', 'Неизвестно')}")
                        print(f"- Страна: {ip_info.get('country', 'Неизвестно')}")
                        print(f"- Организация: {ip_info.get('org', 'Неизвестно')}")
                    else:
                        print("Не удалось получить информацию об IP")
                    
                    # Делаем скриншот
                    await page_with_proxy.screenshot(path="proxy_check_detailed/with_proxy.png")
                    
                    # Проверяем через whoer.com
                    await page_with_proxy.goto("https://whoer.com", wait_until='load', timeout=30000)
                    await page_with_proxy.wait_for_timeout(5000)  # Ждем загрузку страницы
                    await page_with_proxy.screenshot(path="proxy_check_detailed/with_proxy_whoer.png")
                    
                    # Проверяем через другие сервисы
                    await page_with_proxy.goto("https://www.whatismyip.com/", wait_until='load', timeout=30000)
                    await page_with_proxy.wait_for_timeout(5000)
                    await page_with_proxy.screenshot(path="proxy_check_detailed/with_proxy_whatismyip.png")
                    
                except Exception as e:
                    print(f"Ошибка при проверке с прокси: {str(e)}")
                
                await context_with_proxy.close()
                
            except Exception as e:
                print(f"Ошибка при создании контекста с прокси: {str(e)}")
            
            # Проверяем альтернативный формат прокси
            print("\n=== Проверка с альтернативным форматом прокси ===")
            
            alt_proxy = {
                'server': f"socks5://{os.getenv('PROXY_SERVER')}:{os.getenv('PROXY_PORT')}",
                'username': os.getenv('PROXY_USERNAME'),
                'password': os.getenv('PROXY_PASSWORD')
            }
            
            print(f"Альтернативные настройки прокси:")
            print(f"- Сервер: {alt_proxy['server']}")
            print(f"- Логин: {alt_proxy['username']}")
            print(f"- Пароль: {'*' * len(alt_proxy['password'])}")
            
            try:
                context_alt_proxy = await browser.new_context(
                    proxy=alt_proxy,
                    locale=config.DEFAULT_LOCALE,
                    user_agent=config.DEFAULT_USER_AGENT
                )
                
                page_alt_proxy = await context_alt_proxy.new_page()
                
                try:
                    # Проверяем IP через ipinfo.io
                    await page_alt_proxy.goto("https://ipinfo.io/json", wait_until='load', timeout=30000)
                    content = await page_alt_proxy.content()
                    # Извлекаем JSON из содержимого страницы
                    json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    if json_start >= 0 and json_end > json_start:
                        ip_info = json.loads(content[json_start:json_end])
                        print("IP с альтернативным прокси:")
                        print(f"- IP: {ip_info.get('ip', 'Неизвестно')}")
                        print(f"- Город: {ip_info.get('city', 'Неизвестно')}")
                        print(f"- Регион: {ip_info.get('region', 'Неизвестно')}")
                        print(f"- Страна: {ip_info.get('country', 'Неизвестно')}")
                        print(f"- Организация: {ip_info.get('org', 'Неизвестно')}")
                    else:
                        print("Не удалось получить информацию об IP")
                    
                    # Делаем скриншот
                    await page_alt_proxy.screenshot(path="proxy_check_detailed/with_alt_proxy.png")
                    
                except Exception as e:
                    print(f"Ошибка при проверке с альтернативным прокси: {str(e)}")
                
                await context_alt_proxy.close()
                
            except Exception as e:
                print(f"Ошибка при создании контекста с альтернативным прокси: {str(e)}")
            
            # Ждем некоторое время перед закрытием браузера
            print("\nПроверка завершена. Браузер останется открытым для 10 секунд.")
            await asyncio.sleep(10)
            
    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_proxy_detailed()) 