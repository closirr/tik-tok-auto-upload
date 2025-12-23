#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование TikTokManager с бесплатными прокси
"""

import asyncio
from tiktok_manager import TikTokManager
import config

async def test_tiktok_manager_initialization():
    """Тестирование инициализации TikTokManager"""
    print("=== Тестирование инициализации TikTokManager ===")
    
    try:
        manager = TikTokManager()
        
        print(f"✅ TikTokManager создан")
        print(f"   Режим прокси: {'Бесплатные' if manager.use_free_proxy else 'Платные'}")
        print(f"   Ротация прокси: {'Включена' if manager.use_proxy_rotation else 'Выключена'}")
        
        if manager.use_free_proxy:
            print(f"   Менеджер прокси: {'Инициализирован' if manager.proxy_manager else 'Не инициализирован'}")
        
        return manager
        
    except Exception as e:
        print(f"❌ Ошибка инициализации TikTokManager: {e}")
        return None

async def test_proxy_refresh():
    """Тестирование обновления прокси"""
    print("\n=== Тестирование обновления прокси ===")
    
    manager = TikTokManager()
    
    try:
        # Тестируем обновление прокси
        result = await manager.refresh_proxy_ip()
        
        if result:
            print("✅ Прокси успешно обновлен")
            if manager.proxy:
                print(f"   Текущий прокси: {manager.proxy['server']}")
            return True
        else:
            print("❌ Не удалось обновить прокси")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка при обновлении прокси: {e}")
        return False

async def test_proxy_configuration():
    """Тестирование конфигурации прокси"""
    print("\n=== Тестирование конфигурации прокси ===")
    
    manager = TikTokManager()
    
    # Получаем прокси для сессии
    if manager.use_free_proxy and not manager.proxy:
        print("🔍 Получение прокси для тестирования...")
        from free_proxy_integration import get_primary_proxy
        manager.proxy = await get_primary_proxy()
    
    if manager.proxy:
        print("✅ Прокси настроен:")
        print(f"   Сервер: {manager.proxy['server']}")
        print(f"   Логин: {manager.proxy.get('username', 'Не требуется')}")
        print(f"   Пароль: {'Есть' if manager.proxy.get('password') else 'Не требуется'}")
        
        # Проверяем формат для Playwright
        proxy_config = {k: v for k, v in manager.proxy.items() if v is not None}
        print(f"   Конфигурация для Playwright: {proxy_config}")
        
        return True
    else:
        print("❌ Прокси не настроен")
        return False

async def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование TikTokManager с бесплатными прокси")
    
    # Проверяем конфигурацию
    print(f"Режим прокси в конфигурации: {config.PROXY_MODE}")
    print(f"Использовать бесплатные прокси: {config.USE_FREE_PROXY}")
    
    if not config.USE_FREE_PROXY:
        print("\n⚠️  Бесплатные прокси отключены в конфигурации")
        print("   Установите PROXY_MODE=free в .env файле для тестирования")
        return
    
    # Тестируем инициализацию
    manager = await test_tiktok_manager_initialization()
    if not manager:
        print("❌ Не удалось инициализировать TikTokManager")
        return
    
    # Тестируем обновление прокси
    success = await test_proxy_refresh()
    if not success:
        print("❌ Тестирование обновления прокси провалено")
        return
    
    # Тестируем конфигурацию прокси
    success = await test_proxy_configuration()
    if not success:
        print("❌ Тестирование конфигурации прокси провалено")
        return
    
    print("\n✅ Все тесты TikTokManager пройдены успешно!")
    print("🎯 TikTokManager готов к работе с бесплатными прокси")
    print("\n📝 Для полного тестирования:")
    print("   1. Добавьте файлы с куками в папку 'cookies/'")
    print("   2. Добавьте видео в папку 'videos/'")
    print("   3. Запустите 'python main.py'")

if __name__ == "__main__":
    asyncio.run(main())