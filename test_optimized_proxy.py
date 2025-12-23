#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Тест оптимизированной логики поиска прокси
"""

import asyncio
import time
from free_proxy_integration import get_primary_proxy, get_proxy_pool_for_batch, get_proxy_manager

async def test_optimized_proxy_search():
    """Тестирует оптимизированный поиск прокси"""
    print("🚀 Тестирование оптимизированного поиска прокси")
    print("=" * 50)
    
    # Тест 1: Получение одного прокси
    print("\n📋 Тест 1: Получение одного прокси")
    start_time = time.time()
    
    proxy = await get_primary_proxy()
    
    elapsed = time.time() - start_time
    
    if proxy:
        print(f"✅ Прокси получен за {elapsed:.2f} секунд")
        print(f"   Сервер: {proxy['server']}")
    else:
        print(f"❌ Не удалось получить прокси за {elapsed:.2f} секунд")
    
    # Тест 2: Повторное получение (должно использовать кэш)
    print("\n📋 Тест 2: Повторное получение (кэш)")
    start_time = time.time()
    
    proxy2 = await get_primary_proxy()
    
    elapsed = time.time() - start_time
    
    if proxy2:
        print(f"✅ Прокси получен за {elapsed:.2f} секунд (из кэша)")
        print(f"   Сервер: {proxy2['server']}")
        if proxy and proxy2['server'] == proxy['server']:
            print("   ✅ Используется кэшированный прокси")
    else:
        print(f"❌ Не удалось получить прокси за {elapsed:.2f} секунд")
    
    # Тест 3: Создание пула прокси
    print("\n📋 Тест 3: Создание пула прокси")
    start_time = time.time()
    
    proxy_pool = await get_proxy_pool_for_batch()
    
    elapsed = time.time() - start_time
    
    if proxy_pool:
        print(f"✅ Пул из {len(proxy_pool)} прокси создан за {elapsed:.2f} секунд")
        for i, p in enumerate(proxy_pool, 1):
            print(f"   {i}. {p['server']}")
    else:
        print(f"❌ Не удалось создать пул прокси за {elapsed:.2f} секунд")
    
    # Тест 4: Статистика менеджера
    print("\n📋 Тест 4: Статистика менеджера")
    manager = get_proxy_manager()
    
    print(f"   Протестированных прокси: {len(manager.tested_proxies)}")
    print(f"   Неработающих прокси: {len(manager.failed_proxies)}")
    
    if manager.tested_proxies:
        print("   Последние рабочие прокси:")
        for proxy_info in manager.tested_proxies[-3:]:  # Показываем последние 3
            age = time.time() - proxy_info['tested_at']
            print(f"     - {proxy_info['url']} (возраст: {age:.0f}с)")

async def test_proxy_performance():
    """Тестирует производительность поиска прокси"""
    print("\n🏃 Тест производительности")
    print("=" * 30)
    
    # Очищаем кэш для чистого теста
    manager = get_proxy_manager()
    manager.clear_cache()
    
    # Тестируем получение 5 прокси подряд
    total_time = 0
    successful_proxies = 0
    
    for i in range(1, 6):
        print(f"\nПопытка {i}/5:")
        start_time = time.time()
        
        proxy = await get_primary_proxy()
        
        elapsed = time.time() - start_time
        total_time += elapsed
        
        if proxy:
            successful_proxies += 1
            print(f"  ✅ Получен за {elapsed:.2f}с: {proxy['server']}")
        else:
            print(f"  ❌ Не получен за {elapsed:.2f}с")
        
        # Небольшая пауза между запросами
        await asyncio.sleep(0.5)
    
    print(f"\n📊 Результаты:")
    print(f"   Успешных запросов: {successful_proxies}/5")
    print(f"   Общее время: {total_time:.2f}с")
    print(f"   Среднее время на прокси: {total_time/5:.2f}с")

async def main():
    """Основная функция тестирования"""
    try:
        await test_optimized_proxy_search()
        await test_proxy_performance()
        
        print("\n🎉 Тестирование завершено!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")

if __name__ == "__main__":
    asyncio.run(main())