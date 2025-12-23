#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Утилита для сброса счетчиков неудачных попыток прокси
"""

import asyncio
from free_proxy_integration import get_proxy_manager

def reset_proxy_counters():
    """Сбрасывает счетчики неудачных попыток прокси"""
    
    print("🔄 Сброс счетчиков прокси")
    print("=" * 30)
    
    manager = get_proxy_manager()
    
    # Показываем текущую статистику
    stats = manager.get_failure_stats()
    print(f"📊 Текущая статистика:")
    print(f"   Всего неудач: {stats['total_failed']}/{stats['max_total']}")
    print(f"   Подряд неудач: {stats['consecutive_failed']}/{stats['max_consecutive']}")
    print(f"   Заблокирован: {'Да' if stats['is_blocked'] else 'Нет'}")
    
    if not stats['is_blocked'] and stats['total_failed'] == 0:
        print("✅ Счетчики уже сброшены")
        return
    
    print(f"\n🔄 Сброс счетчиков...")
    
    # Сбрасываем счетчики
    manager.total_failed_attempts = 0
    manager.consecutive_failures = 0
    
    # Очищаем список неудачных прокси для свежего старта
    failed_count = len(manager.failed_proxies)
    manager.failed_proxies.clear()
    
    # Очищаем кэш для получения новых прокси
    cached_count = len(manager.tested_proxies)
    manager.tested_proxies.clear()
    
    print(f"✅ Счетчики сброшены:")
    print(f"   - Общие неудачи: 0")
    print(f"   - Подряд неудачи: 0")
    print(f"   - Очищено неудачных прокси: {failed_count}")
    print(f"   - Очищено кэшированных прокси: {cached_count}")
    
    # Показываем новую статистику
    new_stats = manager.get_failure_stats()
    print(f"\n📊 Новая статистика:")
    print(f"   Всего неудач: {new_stats['total_failed']}/{new_stats['max_total']}")
    print(f"   Подряд неудач: {new_stats['consecutive_failed']}/{new_stats['max_consecutive']}")
    print(f"   Заблокирован: {'Да' if new_stats['is_blocked'] else 'Нет'}")
    print(f"   Доступно попыток: {new_stats['remaining_attempts']}")

async def test_proxy_after_reset():
    """Тестирует получение прокси после сброса"""
    
    print(f"\n🧪 Тест получения прокси после сброса")
    print("=" * 40)
    
    from free_proxy_integration import get_primary_proxy
    
    try:
        proxy = await get_primary_proxy()
        if proxy:
            print(f"✅ Успешно получен прокси: {proxy['server']}")
        else:
            print("❌ Не удалось получить прокси")
    except Exception as e:
        print(f"❌ Ошибка при получении прокси: {e}")

async def main():
    """Основная функция"""
    
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Только тест без сброса
        await test_proxy_after_reset()
        return
    
    try:
        reset_proxy_counters()
        
        # Предлагаем протестировать
        response = input("\nПротестировать получение прокси? (y/N): ")
        if response.lower() in ['y', 'yes', 'да']:
            await test_proxy_after_reset()
            
    except KeyboardInterrupt:
        print("\n⏹️  Операция прервана пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())