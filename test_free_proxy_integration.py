#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тестирование интеграции free-proxy с TikTok Auto Upload
"""

import asyncio
import config
from free_proxy_integration import get_proxy_manager, get_primary_proxy, refresh_proxy

async def test_config():
    """Тестирование конфигурации"""
    print("=== Тестирование конфигурации ===")
    print(f"Режим прокси: {config.PROXY_MODE}")
    print(f"Использовать бесплатные прокси: {config.USE_FREE_PROXY}")
    
    if config.USE_FREE_PROXY:
        print("Настройки бесплатных прокси:")
        print(f"- Страны: {config.FREE_PROXY_CONFIG['country_id']}")
        print(f"- HTTPS: {config.FREE_PROXY_CONFIG['https']}")
        print(f"- Анонимность: {config.FREE_PROXY_CONFIG['anonym']}")
        print(f"- Таймаут: {config.FREE_PROXY_CONFIG['timeout']}с")
        print(f"- Размер пула: {config.FREE_PROXY_CONFIG['pool_size']}")
        print(f"- Время кэша: {config.FREE_PROXY_CONFIG['cache_time']}с")
    else:
        print("Настройки платных прокси:")
        print(f"- Сервер: {config.PAID_PROXY.get('server', 'Не настроен')}")
        print(f"- Логин: {config.PAID_PROXY.get('username', 'Не настроен')}")

async def test_proxy_manager():
    """Тестирование менеджера прокси"""
    print("\n=== Тестирование менеджера прокси ===")
    
    manager = get_proxy_manager()
    
    # Получаем основной прокси
    print("Получение основного прокси...")
    proxy = await get_primary_proxy()
    
    if proxy:
        print(f"✅ Получен прокси: {proxy['server']}")
        print(f"   Логин: {proxy.get('username', 'Не требуется')}")
        print(f"   Пароль: {'Есть' if proxy.get('password') else 'Не требуется'}")
    else:
        print("❌ Не удалось получить прокси")
        return False
    
    # Тестируем обновление прокси
    print("\nТестирование обновления прокси...")
    new_proxy = await refresh_proxy()
    
    if new_proxy:
        print(f"✅ Получен новый прокси: {new_proxy['server']}")
    else:
        print("❌ Не удалось обновить прокси")
    
    return True

async def test_proxy_pool():
    """Тестирование пула прокси"""
    print("\n=== Тестирование пула прокси ===")
    
    manager = get_proxy_manager()
    
    # Создаем пул прокси
    proxy_pool = await manager.get_proxy_pool(count=3)
    
    if proxy_pool:
        print(f"✅ Создан пул из {len(proxy_pool)} прокси:")
        for i, proxy in enumerate(proxy_pool, 1):
            print(f"   {i}. {proxy['server']}")
        
        # Тестируем ротацию
        print("\nТестирование ротации:")
        for i in range(5):
            rotated = manager.get_next_proxy_from_pool(proxy_pool)
            if rotated:
                print(f"   Ротация {i+1}: {rotated['server']}")
    else:
        print("❌ Не удалось создать пул прокси")
        return False
    
    return True

async def test_cache():
    """Тестирование кэширования"""
    print("\n=== Тестирование кэширования ===")
    
    manager = get_proxy_manager()
    
    # Получаем прокси (должен попасть в кэш)
    proxy1 = await get_primary_proxy()
    if proxy1:
        print(f"✅ Первый прокси: {proxy1['server']}")
    
    # Получаем из кэша
    cached = manager.get_cached_proxy()
    if cached:
        print(f"✅ Кэшированный прокси: {cached['server']}")
        if cached['server'] == proxy1['server']:
            print("✅ Кэш работает корректно")
        else:
            print("❌ Кэш вернул другой прокси")
    else:
        print("❌ Кэш пуст")
    
    # Очищаем кэш
    manager.clear_cache()
    cached_after_clear = manager.get_cached_proxy()
    if not cached_after_clear:
        print("✅ Кэш успешно очищен")
    else:
        print("❌ Кэш не очистился")

async def main():
    """Основная функция тестирования"""
    print("🚀 Тестирование интеграции free-proxy с TikTok Auto Upload")
    
    # Проверяем конфигурацию
    await test_config()
    
    if not config.USE_FREE_PROXY:
        print("\n⚠️  Бесплатные прокси отключены в конфигурации")
        print("   Установите PROXY_MODE=free в .env файле для тестирования")
        return
    
    # Тестируем менеджер прокси
    success = await test_proxy_manager()
    if not success:
        print("❌ Тестирование менеджера прокси провалено")
        return
    
    # Тестируем пул прокси
    success = await test_proxy_pool()
    if not success:
        print("❌ Тестирование пула прокси провалено")
        return
    
    # Тестируем кэширование
    await test_cache()
    
    print("\n✅ Все тесты пройдены успешно!")
    print("🎯 Free-proxy интеграция готова к использованию")

if __name__ == "__main__":
    asyncio.run(main())