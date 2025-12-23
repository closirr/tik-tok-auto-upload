#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест логики повторных попыток с прокси
"""

import asyncio
from tiktok_manager import TikTokManager
import config

async def test_proxy_retry():
    """Тестирует логику повторных попыток получения прокси"""
    print("🧪 Тестирование логики повторных попыток с прокси")
    print("=" * 50)
    
    # Создаем менеджер
    manager = TikTokManager()
    
    # Проверяем, что используются бесплатные прокси
    if not manager.use_free_proxy:
        print("❌ Тест работает только с бесплатными прокси")
        print("   Установите PROXY_MODE=free в .env файле")
        return
    
    print("✅ Используются бесплатные прокси")
    print(f"   Настройки: {config.FREE_PROXY_CONFIG}")
    
    # Тестируем получение прокси
    print("\n📋 Тест получения прокси...")
    
    # Сбрасываем текущий прокси
    manager.proxy = None
    
    # Пытаемся получить прокси (как в process_account)
    if manager.use_free_proxy:
        if not manager.proxy:
            print("🔍 Получение бесплатного прокси для сессии...")
            max_proxy_attempts = 5
            proxy_attempt = 0
            
            while proxy_attempt < max_proxy_attempts:
                proxy_attempt += 1
                print(f"🔄 Попытка {proxy_attempt}/{max_proxy_attempts} получения прокси...")
                
                from free_proxy_integration import get_primary_proxy
                manager.proxy = await get_primary_proxy()
                if manager.proxy:
                    print(f"✅ Получен прокси: {manager.proxy['server']}")
                    break
                else:
                    print(f"❌ Не удалось получить прокси на попытке {proxy_attempt}")
                
                # Небольшая пауза между попытками
                if proxy_attempt < max_proxy_attempts:
                    await asyncio.sleep(1)
            
            if manager.proxy:
                print(f"🎉 Успешно получен прокси: {manager.proxy['server']}")
            else:
                print("❌ Не удалось получить прокси после всех попыток")
    
    print("\n✅ Тест завершен")

async def test_error_detection():
    """Тестирует определение ошибок прокси"""
    print("\n🔍 Тестирование определения ошибок прокси")
    print("=" * 40)
    
    # Список тестовых ошибок
    test_errors = [
        "NS_ERROR_UNKNOWN_HOST",
        "Connection refused",
        "SSL_ERROR_SYSCALL", 
        "Timeout error",
        "Network error",
        "DNS resolution failed",
        "Invalid cookie format",  # Это НЕ ошибка прокси
        "Authentication failed"   # Это НЕ ошибка прокси
    ]
    
    # Список ключевых слов для определения ошибок прокси
    proxy_error_keywords = [
        'ssl_error', 'ssl error', 'proxy', 'connection', 'timeout', 'connect',
        'ns_error_unknown_host', 'network error', 'dns', 'host not found',
        'connection refused', 'connection reset', 'connection aborted'
    ]
    
    for error in test_errors:
        error_text = error.lower()
        is_proxy_error = any(err in error_text for err in proxy_error_keywords)
        
        status = "🔗 ПРОКСИ" if is_proxy_error else "🍪 КУКИ"
        print(f"   {status}: {error}")
    
    print("\n✅ Тест определения ошибок завершен")

async def main():
    """Основная функция тестирования"""
    try:
        await test_proxy_retry()
        await test_error_detection()
        
    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")

if __name__ == "__main__":
    asyncio.run(main())