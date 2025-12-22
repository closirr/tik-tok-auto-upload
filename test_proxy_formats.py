import asyncio
from playwright.async_api import async_playwright
import config
import os
from dotenv import load_dotenv

# Загружаем переменные окружения из файла .env
load_dotenv()

async def test_proxy_format(proxy_config, name):
    """Тестирует конкретный формат прокси"""
    print(f"\n=== Тестирование формата прокси {name} ===")
    print(f"Конфигурация: {proxy_config}")
    
    try:
        async with async_playwright() as p:
            browser = await p.firefox.launch(headless=False)
            
            # Создаем контекст без прокси для сравнения
            print("Проверка без прокси:")
            context_no_proxy = await browser.new_context()
            page_no_proxy = await context_no_proxy.new_page()
            
            try:
                await page_no_proxy.goto("https://api.ipify.org", wait_until='load', timeout=10000)
                ip_text = await page_no_proxy.content()
                print(f"IP без прокси: {ip_text}")
            except Exception as e:
                print(f"Ошибка при проверке IP без прокси: {str(e)}")
                ip_text = "неизвестно"
            
            # Создаем контекст с прокси
            print("\nПроверка с прокси:")
            try:
                context_with_proxy = await browser.new_context(
                    proxy=proxy_config,
                    locale=config.DEFAULT_LOCALE,
                    user_agent=config.DEFAULT_USER_AGENT
                )
                page_with_proxy = await context_with_proxy.new_page()
                
                try:
                    await page_with_proxy.goto("https://api.ipify.org", wait_until='load', timeout=10000)
                    proxy_ip_text = await page_with_proxy.content()
                    print(f"IP с прокси: {proxy_ip_text}")
                    
                    if ip_text != proxy_ip_text:
                        print(f"✅ Прокси {name} работает! IP-адреса отличаются.")
                        return True
                    else:
                        print(f"❌ Прокси {name} не работает! IP-адреса одинаковые.")
                        return False
                except Exception as e:
                    print(f"❌ Ошибка при проверке IP с прокси {name}: {str(e)}")
                    return False
            except Exception as e:
                print(f"❌ Ошибка при создании контекста с прокси {name}: {str(e)}")
                return False
            
            # Ждем некоторое время перед закрытием браузера
            await asyncio.sleep(2)
    except Exception as e:
        print(f"Критическая ошибка при тестировании {name}: {str(e)}")
        return False

async def main():
    """Тестирует разные форматы прокси"""
    print("Запуск тестирования разных форматов прокси...")
    
    # Тестируем формат из config.py
    await test_proxy_format(config.PROXY, "PROXY из config.py")
    
    # Тестируем альтернативный формат из config.py
    await test_proxy_format(config.PROXY_ALT, "PROXY_ALT из config.py")
    
    # Тестируем формат с явным указанием протокола http
    proxy_http = {
        'server': f"http://{os.getenv('PROXY_SERVER')}",
        'username': os.getenv('PROXY_USERNAME'),
        'password': os.getenv('PROXY_PASSWORD')
    }
    await test_proxy_format(proxy_http, "HTTP")
    
    # Тестируем формат с явным указанием протокола https
    proxy_https = {
        'server': f"https://{os.getenv('PROXY_SERVER')}",
        'username': os.getenv('PROXY_USERNAME'),
        'password': os.getenv('PROXY_PASSWORD')
    }
    await test_proxy_format(proxy_https, "HTTPS")
    
    # Тестируем формат с явным указанием протокола socks5
    proxy_socks5 = {
        'server': f"socks5://{os.getenv('PROXY_SERVER')}",
        'username': os.getenv('PROXY_USERNAME'),
        'password': os.getenv('PROXY_PASSWORD')
    }
    await test_proxy_format(proxy_socks5, "SOCKS5")
    
    # Тестируем формат без протокола
    proxy_no_protocol = {
        'server': os.getenv('PROXY_SERVER'),
        'username': os.getenv('PROXY_USERNAME'),
        'password': os.getenv('PROXY_PASSWORD')
    }
    await test_proxy_format(proxy_no_protocol, "Без протокола")
    
    print("\nТестирование завершено.")

if __name__ == "__main__":
    asyncio.run(main()) 