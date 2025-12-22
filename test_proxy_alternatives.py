import asyncio
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

async def test_proxy_protocol(protocol, browser_type='firefox'):
    """Тестирует работу прокси с указанным протоколом"""
    print(f"\n=== Тестирование прокси с протоколом {protocol} в браузере {browser_type} ===")
    
    proxy_server = os.getenv('PROXY_SERVER')
    proxy_port = os.getenv('PROXY_PORT')
    proxy_username = os.getenv('PROXY_USERNAME')
    proxy_password = os.getenv('PROXY_PASSWORD')
    
    # Формируем настройки прокси
    proxy_config = {
        'server': f"{protocol}://{proxy_server}:{proxy_port}",
        'username': proxy_username,
        'password': proxy_password
    }
    
    print(f"Настройки прокси:")
    print(f"- Сервер: {proxy_config['server']}")
    print(f"- Логин: {proxy_config['username']}")
    print(f"- Пароль: {'*' * len(proxy_config['password'])}")
    
    # Создаем директорию для скриншотов, если её нет
    if not os.path.exists('proxy_alternatives'):
        os.makedirs('proxy_alternatives')
    
    try:
        async with async_playwright() as p:
            # Выбираем тип браузера
            if browser_type == 'chromium':
                browser_factory = p.chromium
            elif browser_type == 'webkit':
                browser_factory = p.webkit
            else:
                browser_factory = p.firefox
            
            # Запускаем браузер
            browser = await browser_factory.launch(headless=False)
            
            # Создаем контекст с прокси
            try:
                context = await browser.new_context(
                    proxy=proxy_config,
                    locale='ru-RU',
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
                )
                
                page = await context.new_page()
                
                try:
                    # Проверяем IP через api.ipify.org
                    await page.goto("https://api.ipify.org", wait_until='load', timeout=30000)
                    ip_text = await page.content()
                    print(f"IP с прокси: {ip_text}")
                    
                    # Делаем скриншот
                    screenshot_path = f"proxy_alternatives/{protocol}_{browser_type}_ipify.png"
                    await page.screenshot(path=screenshot_path)
                    print(f"Скриншот сохранен: {screenshot_path}")
                    
                    # Проверяем через whoer.com
                    await page.goto("https://whoer.com", wait_until='load', timeout=30000)
                    await page.wait_for_timeout(5000)  # Ждем загрузку страницы
                    screenshot_path = f"proxy_alternatives/{protocol}_{browser_type}_whoer.png"
                    await page.screenshot(path=screenshot_path)
                    print(f"Скриншот сохранен: {screenshot_path}")
                    
                    return True
                    
                except Exception as e:
                    print(f"Ошибка при проверке с прокси: {str(e)}")
                    return False
                
                finally:
                    await context.close()
                
            except Exception as e:
                print(f"Ошибка при создании контекста с прокси: {str(e)}")
                return False
            
            finally:
                await browser.close()
            
    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")
        return False

async def main():
    """Тестирует разные протоколы прокси"""
    print("Тестирование разных протоколов прокси...")
    
    # Список протоколов для тестирования
    protocols = ['http', 'https', 'socks5']
    
    # Список браузеров для тестирования
    browsers = ['firefox', 'chromium']
    
    results = {}
    
    # Тестируем каждую комбинацию протокола и браузера
    for protocol in protocols:
        results[protocol] = {}
        for browser in browsers:
            result = await test_proxy_protocol(protocol, browser)
            results[protocol][browser] = result
            # Ждем между тестами
            await asyncio.sleep(3)
    
    # Выводим результаты
    print("\n=== Результаты тестирования ===")
    for protocol in protocols:
        for browser in browsers:
            status = "✅ Работает" if results[protocol][browser] else "❌ Не работает"
            print(f"Протокол {protocol} в браузере {browser}: {status}")

if __name__ == "__main__":
    asyncio.run(main()) 