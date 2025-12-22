import asyncio
from playwright.async_api import async_playwright
import config
import os

async def check_current_proxy():
    """Проверяет работу прокси с текущими настройками"""
    print("Проверка текущих настроек прокси...")
    print(f"Настройки прокси из конфигурации:")
    print(f"- Сервер: {config.PROXY['server']}")
    print(f"- Логин: {config.PROXY['username']}")
    print(f"- Пароль: {'*' * len(config.PROXY['password'])}")
    print(f"- Режим ротации: {'Включен' if config.USE_PROXY_ROTATION else 'Выключен'}")
    
    # Создаем директорию для скриншотов, если её нет
    if not os.path.exists('proxy_current'):
        os.makedirs('proxy_current')
    
    try:
        async with async_playwright() as p:
            # Запускаем браузер Firefox
            firefox = await p.firefox.launch(headless=False)
            
            # Сначала проверим IP без прокси для сравнения
            print("\n=== Проверка без прокси в Firefox ===")
            context_no_proxy = await firefox.new_context()
            page_no_proxy = await context_no_proxy.new_page()
            
            try:
                await page_no_proxy.goto("https://api.ipify.org", wait_until='load', timeout=30000)
                ip_text = await page_no_proxy.content()
                print(f"IP без прокси (Firefox): {ip_text}")
                await page_no_proxy.screenshot(path="proxy_current/firefox_no_proxy.png")
                
                # Проверяем через whoer.com
                await page_no_proxy.goto("https://whoer.com", wait_until='load', timeout=30000)
                await page_no_proxy.wait_for_timeout(5000)
                await page_no_proxy.screenshot(path="proxy_current/firefox_no_proxy_whoer.png")
            except Exception as e:
                print(f"Ошибка при проверке без прокси (Firefox): {str(e)}")
            
            await context_no_proxy.close()
            
            # Проверка с прокси в Firefox
            print("\n=== Проверка с прокси в Firefox ===")
            try:
                context_with_proxy = await firefox.new_context(
                    proxy=config.PROXY,
                    locale=config.DEFAULT_LOCALE,
                    user_agent=config.DEFAULT_USER_AGENT
                )
                
                page_with_proxy = await context_with_proxy.new_page()
                
                try:
                    await page_with_proxy.goto("https://api.ipify.org", wait_until='load', timeout=30000)
                    ip_text = await page_with_proxy.content()
                    print(f"IP с прокси (Firefox): {ip_text}")
                    await page_with_proxy.screenshot(path="proxy_current/firefox_with_proxy.png")
                    
                    # Проверяем через whoer.com
                    await page_with_proxy.goto("https://whoer.com", wait_until='load', timeout=30000)
                    await page_with_proxy.wait_for_timeout(5000)
                    await page_with_proxy.screenshot(path="proxy_current/firefox_with_proxy_whoer.png")
                except Exception as e:
                    print(f"Ошибка при проверке с прокси (Firefox): {str(e)}")
                
                await context_with_proxy.close()
            except Exception as e:
                print(f"Ошибка при создании контекста с прокси (Firefox): {str(e)}")
            
            await firefox.close()
            
            # Запускаем браузер Chromium
            chromium = await p.chromium.launch(headless=False)
            
            # Сначала проверим IP без прокси для сравнения
            print("\n=== Проверка без прокси в Chromium ===")
            context_no_proxy = await chromium.new_context()
            page_no_proxy = await context_no_proxy.new_page()
            
            try:
                await page_no_proxy.goto("https://api.ipify.org", wait_until='load', timeout=30000)
                ip_text = await page_no_proxy.content()
                print(f"IP без прокси (Chromium): {ip_text}")
                await page_no_proxy.screenshot(path="proxy_current/chromium_no_proxy.png")
                
                # Проверяем через whoer.com
                await page_no_proxy.goto("https://whoer.com", wait_until='load', timeout=30000)
                await page_no_proxy.wait_for_timeout(5000)
                await page_no_proxy.screenshot(path="proxy_current/chromium_no_proxy_whoer.png")
            except Exception as e:
                print(f"Ошибка при проверке без прокси (Chromium): {str(e)}")
            
            await context_no_proxy.close()
            
            # Проверка с прокси в Chromium
            print("\n=== Проверка с прокси в Chromium ===")
            try:
                context_with_proxy = await chromium.new_context(
                    proxy=config.PROXY,
                    locale=config.DEFAULT_LOCALE,
                    user_agent=config.DEFAULT_USER_AGENT
                )
                
                page_with_proxy = await context_with_proxy.new_page()
                
                try:
                    await page_with_proxy.goto("https://api.ipify.org", wait_until='load', timeout=30000)
                    ip_text = await page_with_proxy.content()
                    print(f"IP с прокси (Chromium): {ip_text}")
                    await page_with_proxy.screenshot(path="proxy_current/chromium_with_proxy.png")
                    
                    # Проверяем через whoer.com
                    await page_with_proxy.goto("https://whoer.com", wait_until='load', timeout=30000)
                    await page_with_proxy.wait_for_timeout(5000)
                    await page_with_proxy.screenshot(path="proxy_current/chromium_with_proxy_whoer.png")
                except Exception as e:
                    print(f"Ошибка при проверке с прокси (Chromium): {str(e)}")
                
                await context_with_proxy.close()
            except Exception as e:
                print(f"Ошибка при создании контекста с прокси (Chromium): {str(e)}")
            
            await chromium.close()
            
    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_current_proxy()) 