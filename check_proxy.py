import asyncio
from playwright.async_api import async_playwright
import config
import os
import traceback

async def check_proxy():
    """Проверяет работу прокси с помощью Playwright"""
    print("Запуск проверки прокси...")
    print(f"Настройки прокси из конфигурации:")
    print(f"- Сервер: {config.PROXY['server']}")
    print(f"- Логин: {config.PROXY['username']}")
    print(f"- Пароль: {'*' * len(config.PROXY['password'])}")
    
    # Создаем директорию для скриншотов, если её нет
    if not os.path.exists('proxy_check'):
        os.makedirs('proxy_check')
    
    try:
        async with async_playwright() as p:
            print("Запуск браузера...")
            # Запускаем браузер
            browser = await p.firefox.launch(headless=False)
            
            # Создаем контекст без прокси для сравнения
            print("\nПроверка без прокси:")
            context_no_proxy = await browser.new_context()
            page_no_proxy = await context_no_proxy.new_page()
            
            # Проверяем IP без прокси
            print("Загрузка страницы для проверки IP без прокси...")
            try:
                await page_no_proxy.goto("https://api.ipify.org", wait_until='load', timeout=30000)
                ip_text = await page_no_proxy.content()
                print(f"IP без прокси: {ip_text}")
                await page_no_proxy.screenshot(path="proxy_check/no_proxy_ip.png")
            except Exception as e:
                print(f"Ошибка при проверке IP без прокси: {str(e)}")
                ip_text = "неизвестно"
            
            # Создаем контекст с прокси
            print("\nПроверка с прокси:")
            print("Создание контекста с прокси...")
            try:
                context_with_proxy = await browser.new_context(
                    proxy=config.PROXY,
                    locale=config.DEFAULT_LOCALE,
                    user_agent=config.DEFAULT_USER_AGENT
                )
                page_with_proxy = await context_with_proxy.new_page()
                
                # Проверяем IP с прокси
                print("Загрузка страницы для проверки IP с прокси...")
                try:
                    await page_with_proxy.goto("https://api.ipify.org", wait_until='load', timeout=30000)
                    proxy_ip_text = await page_with_proxy.content()
                    print(f"IP с прокси: {proxy_ip_text}")
                    await page_with_proxy.screenshot(path="proxy_check/with_proxy_ip.png")
                    
                    # Проверяем, отличается ли IP
                    if ip_text != proxy_ip_text:
                        print("✅ Прокси работает! IP-адреса отличаются.")
                    else:
                        print("❌ Прокси не работает! IP-адреса одинаковые.")
                    
                    # Проверяем дополнительную информацию о прокси
                    print("Загрузка дополнительной информации о прокси...")
                    try:
                        await page_with_proxy.goto("https://whatismyipaddress.com/", wait_until='load', timeout=30000)
                        await page_with_proxy.wait_for_timeout(3000)
                        await page_with_proxy.screenshot(path="proxy_check/proxy_details.png")
                    except Exception as e:
                        print(f"Ошибка при загрузке дополнительной информации: {str(e)}")
                    
                except Exception as e:
                    print(f"Ошибка при проверке IP с прокси: {str(e)}")
            except Exception as e:
                print(f"Ошибка при создании контекста с прокси: {str(e)}")
            
            # Оставляем браузер открытым для проверки
            print("\nПроверка завершена. Браузер останется открытым для 30 секунд.")
            await asyncio.sleep(30)
    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(check_proxy()) 