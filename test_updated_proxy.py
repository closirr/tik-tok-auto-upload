import asyncio
import aiohttp
from playwright.async_api import async_playwright
import config
import os

async def refresh_proxy_ip():
    """Обновляет IP-адрес прокси"""
    try:
        print("Обновление IP-адреса прокси...")
        async with aiohttp.ClientSession() as session:
            async with session.get(config.PROXY_REFRESH_URL) as response:
                if response.status == 200:
                    response_data = await response.json()
                    if response_data.get("success"):
                        session_id = response_data.get("session")
                        login = response_data.get("login")
                        print(f"IP прокси успешно обновлен. Сессия: {session_id}")
                        
                        # Обновляем логин прокси с новой сессией
                        if session_id and login:
                            updated_proxy = {
                                'server': f"http://{os.getenv('PROXY_SERVER')}",
                                'username': login,
                                'password': os.getenv('PROXY_PASSWORD')
                            }
                            print(f"Обновлен логин прокси: {login}")
                            return updated_proxy
                        else:
                            print("Ошибка: не удалось получить логин или сессию")
                            return None
                    else:
                        print("Ошибка при обновлении IP: сервер вернул успех=false")
                        return None
                else:
                    print(f"Ошибка при обновлении IP прокси. Код ответа: {response.status}")
                    return None
    except Exception as e:
        print(f"Ошибка при обновлении IP прокси: {str(e)}")
        return None

async def test_proxy(proxy_config):
    """Тестирует прокси"""
    print(f"Тестирование прокси: {proxy_config}")
    
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
                        print("✅ Прокси работает! IP-адреса отличаются.")
                        return True
                    else:
                        print("❌ Прокси не работает! IP-адреса одинаковые.")
                        return False
                except Exception as e:
                    print(f"❌ Ошибка при проверке IP с прокси: {str(e)}")
                    return False
            except Exception as e:
                print(f"❌ Ошибка при создании контекста с прокси: {str(e)}")
                return False
            
            # Ждем некоторое время перед закрытием браузера
            await asyncio.sleep(5)
    except Exception as e:
        print(f"Критическая ошибка: {str(e)}")
        return False

async def main():
    """Тестирует прокси с обновленными учетными данными"""
    print("Тестирование прокси с обновленными учетными данными...")
    
    # Сначала тестируем с исходными настройками
    print("\n=== Тестирование с исходными настройками прокси ===")
    await test_proxy(config.PROXY)
    
    # Обновляем IP прокси
    print("\n=== Обновление IP прокси ===")
    updated_proxy = await refresh_proxy_ip()
    
    if updated_proxy:
        # Тестируем с обновленными настройками
        print("\n=== Тестирование с обновленными настройками прокси ===")
        await test_proxy(updated_proxy)
    else:
        print("Не удалось обновить IP прокси")
    
    print("\nТестирование завершено.")

if __name__ == "__main__":
    asyncio.run(main()) 