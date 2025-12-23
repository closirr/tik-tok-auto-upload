#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Финальный тест интеграции free-proxy
"""

import asyncio
from tiktok_manager import TikTokManager
import config

async def final_test():
    """Финальный тест всей системы"""
    print("🚀 Финальный тест интеграции free-proxy")
    print("=" * 50)
    
    # Проверяем конфигурацию
    print(f"✅ Режим прокси: {config.PROXY_MODE}")
    print(f"✅ Бесплатные прокси: {config.USE_FREE_PROXY}")
    
    if not config.USE_FREE_PROXY:
        print("⚠️  Бесплатные прокси отключены")
        return
    
    # Инициализируем TikTokManager
    print("\n📋 Инициализация TikTokManager...")
    manager = TikTokManager()
    print("✅ TikTokManager создан")
    
    # Тестируем получение прокси
    print("\n🔍 Тестирование получения прокси...")
    result = await manager.refresh_proxy_ip()
    
    if result:
        print("✅ Прокси успешно получен и настроен")
        if manager.proxy:
            print(f"   Сервер: {manager.proxy['server']}")
            print(f"   Тип: Бесплатный")
    else:
        print("❌ Не удалось получить прокси")
        return
    
    print("\n🎯 Система готова к работе!")
    print("=" * 50)
    print("📝 Для полного запуска:")
    print("   1. Добавьте куки в папку 'cookies/'")
    print("   2. Добавьте видео в папку 'videos/'") 
    print("   3. Запустите 'python main.py'")

if __name__ == "__main__":
    asyncio.run(final_test())