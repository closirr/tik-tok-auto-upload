#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pre-validated Proxy Pool Manager
Фоновый менеджер пула прокси с постоянной валидацией
"""

import asyncio
import aiohttp
import json
import time
import random
import threading
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
from fp.fp import FreeProxy
import config

logger = logging.getLogger(__name__)

@dataclass
class ProxyInfo:
    """Информация о прокси"""
    server: str
    country: str
    response_time: float
    last_tested: float
    success_rate: float
    total_tests: int
    consecutive_failures: int
    source: str  # 'free-proxy-list', 'proxy-list', 'sslproxies' и т.д.

class ProxyPoolManager:
    """
    Менеджер пула прокси с фоновой валидацией
    
    Особенности:
    - Постоянно тестирует прокси в фоне
    - Поддерживает пул готовых к использованию прокси
    - Мгновенная выдача проверенных прокси
    - Автоматическое удаление мертвых прокси
    - Приоритизация по скорости и надежности
    """
    
    def __init__(self, 
                 target_pool_size: int = 10,
                 max_pool_size: int = 50,
                 test_interval: float = 30.0,
                 max_response_time: float = 8.0,
                 min_success_rate: float = 0.7):
        
        self.target_pool_size = target_pool_size  # Целевой размер пула
        self.max_pool_size = max_pool_size        # Максимальный размер пула
        self.test_interval = test_interval        # Интервал тестирования (сек)
        self.max_response_time = max_response_time # Максимальное время ответа
        self.min_success_rate = min_success_rate  # Минимальный процент успеха
        
        # Пулы прокси
        self.validated_pool: Dict[str, ProxyInfo] = {}  # Проверенные рабочие прокси
        self.testing_queue: List[str] = []              # Очередь на тестирование
        self.blacklist: Set[str] = set()                # Черный список
        
        # Статистика
        self.stats = {
            'total_tested': 0,
            'total_working': 0,
            'total_failed': 0,
            'last_refresh': 0,
            'pool_refreshes': 0
        }
        
        # Флаги управления
        self.running = False
        self.background_task = None
        
        # Источники прокси
        self.proxy_sources = [
            self._fetch_from_free_proxy_list,
            self._fetch_from_ssl_proxies,
            self._fetch_from_proxy_list_download,
        ]
        
        print("🏊 ProxyPoolManager инициализирован")
        print(f"   Целевой размер пула: {target_pool_size}")
        print(f"   Максимальный размер: {max_pool_size}")
        print(f"   Интервал тестирования: {test_interval}с")
    
    async def start(self):
        """Запуск фонового процесса управления пулом"""
        if self.running:
            print("⚠️  ProxyPoolManager уже запущен")
            return
        
        self.running = True
        print("🚀 Запуск фонового менеджера пула прокси...")
        
        # Запускаем фоновую задачу
        self.background_task = asyncio.create_task(self._background_worker())
        
        # Первоначальная загрузка прокси
        await self._initial_pool_fill()
    
    async def stop(self):
        """Остановка фонового процесса"""
        if not self.running:
            return
        
        print("🛑 Остановка ProxyPoolManager...")
        self.running = False
        
        if self.background_task:
            self.background_task.cancel()
            try:
                await self.background_task
            except asyncio.CancelledError:
                pass
        
        print("✅ ProxyPoolManager остановлен")
    
    async def get_best_proxy(self) -> Optional[Dict]:
        """
        Получить лучший прокси из пула (мгновенно)
        
        Returns:
            Конфигурация прокси для Playwright или None
        """
        if not self.validated_pool:
            print("⚠️  Пул прокси пуст, ждем заполнения...")
            # Ждем до 10 секунд пока пул заполнится
            for _ in range(20):
                await asyncio.sleep(0.5)
                if self.validated_pool:
                    break
            else:
                print("❌ Не удалось получить прокси из пула")
                return None
        
        # Сортируем прокси по качеству (скорость + надежность)
        sorted_proxies = sorted(
            self.validated_pool.values(),
            key=lambda p: (p.success_rate, -p.response_time, -p.consecutive_failures),
            reverse=True
        )
        
        if sorted_proxies:
            best_proxy = sorted_proxies[0]
            print(f"⚡ Выдан лучший прокси: {best_proxy.server}")
            print(f"   Скорость: {best_proxy.response_time:.2f}с, Надежность: {best_proxy.success_rate:.1%}")
            
            return {
                'server': f"http://{best_proxy.server}",
                'username': None,
                'password': None
            }
        
        return None
    
    async def get_random_proxy(self) -> Optional[Dict]:
        """Получить случайный прокси из пула"""
        if not self.validated_pool:
            return await self.get_best_proxy()
        
        proxy_info = random.choice(list(self.validated_pool.values()))
        print(f"🎲 Выдан случайный прокси: {proxy_info.server}")
        
        return {
            'server': f"http://{proxy_info.server}",
            'username': None,
            'password': None
        }
    
    async def report_proxy_failure(self, proxy_server: str):
        """Сообщить о неработающем прокси"""
        # Убираем http:// если есть
        clean_server = proxy_server.replace('http://', '').replace('https://', '')
        
        if clean_server in self.validated_pool:
            proxy_info = self.validated_pool[clean_server]
            proxy_info.consecutive_failures += 1
            
            # Если много неудач подряд - удаляем из пула
            if proxy_info.consecutive_failures >= 3:
                print(f"🗑️ Удаляем ненадежный прокси: {clean_server}")
                del self.validated_pool[clean_server]
                self.blacklist.add(clean_server)
    
    def get_pool_status(self) -> Dict:
        """Получить статус пула"""
        return {
            'validated_count': len(self.validated_pool),
            'testing_queue_count': len(self.testing_queue),
            'blacklist_count': len(self.blacklist),
            'target_size': self.target_pool_size,
            'is_running': self.running,
            'stats': self.stats.copy()
        }
    
    async def _background_worker(self):
        """Фоновый воркер для управления пулом"""
        print("🔄 Фоновый воркер запущен")
        
        while self.running:
            try:
                # Проверяем размер пула
                current_size = len(self.validated_pool)
                
                if current_size < self.target_pool_size:
                    print(f"📈 Пул мал ({current_size}/{self.target_pool_size}), пополняем...")
                    await self._refill_pool()
                
                # Тестируем существующие прокси
                await self._test_existing_proxies()
                
                # Тестируем новые прокси из очереди
                await self._test_queued_proxies()
                
                # Очищаем старые прокси
                await self._cleanup_old_proxies()
                
                # Ждем до следующего цикла
                await asyncio.sleep(self.test_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Ошибка в фоновом воркере: {e}")
                await asyncio.sleep(5)
        
        print("🔄 Фоновый воркер остановлен")
    
    async def _initial_pool_fill(self):
        """Первоначальное заполнение пула"""
        print("🏊 Первоначальное заполнение пула...")
        
        # Загружаем прокси из всех источников
        await self._load_proxies_from_sources()
        
        # Тестируем первую партию
        await self._test_queued_proxies(max_tests=self.target_pool_size * 2)
        
        pool_size = len(self.validated_pool)
        print(f"✅ Первоначальное заполнение завершено: {pool_size} прокси в пуле")
    
    async def _refill_pool(self):
        """Пополнение пула новыми прокси"""
        needed = self.target_pool_size - len(self.validated_pool)
        
        if len(self.testing_queue) < needed * 2:
            await self._load_proxies_from_sources()
        
        await self._test_queued_proxies(max_tests=needed * 3)
    
    async def _load_proxies_from_sources(self):
        """Загрузка прокси из всех источников"""
        print("📥 Загрузка прокси из источников...")
        
        new_proxies = []
        
        for source_func in self.proxy_sources:
            try:
                proxies = await source_func()
                new_proxies.extend(proxies)
                print(f"   {source_func.__name__}: +{len(proxies)} прокси")
            except Exception as e:
                print(f"   {source_func.__name__}: ошибка - {e}")
        
        # Фильтруем новые прокси
        filtered_proxies = []
        for proxy in new_proxies:
            if (proxy not in self.blacklist and 
                proxy not in self.validated_pool and 
                proxy not in self.testing_queue):
                filtered_proxies.append(proxy)
        
        # Перемешиваем и добавляем в очередь
        random.shuffle(filtered_proxies)
        self.testing_queue.extend(filtered_proxies[:100])  # Максимум 100 за раз
        
        print(f"📋 Добавлено в очередь тестирования: {len(filtered_proxies)} новых прокси")
    
    async def _test_queued_proxies(self, max_tests: int = 10):
        """Тестирование прокси из очереди"""
        if not self.testing_queue:
            return
        
        tests_count = min(max_tests, len(self.testing_queue))
        print(f"🧪 Тестируем {tests_count} прокси из очереди...")
        
        # Тестируем параллельно для скорости
        semaphore = asyncio.Semaphore(5)  # Максимум 5 одновременно
        
        async def test_single_proxy(proxy_address):
            async with semaphore:
                return await self._test_proxy_detailed(proxy_address)
        
        # Берем прокси для тестирования
        proxies_to_test = []
        for _ in range(tests_count):
            if self.testing_queue:
                proxies_to_test.append(self.testing_queue.pop(0))
        
        # Запускаем тестирование
        tasks = [test_single_proxy(proxy) for proxy in proxies_to_test]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем результаты
        working_count = 0
        for proxy_address, result in zip(proxies_to_test, results):
            if isinstance(result, ProxyInfo):
                self.validated_pool[proxy_address] = result
                working_count += 1
                self.stats['total_working'] += 1
            else:
                self.blacklist.add(proxy_address)
                self.stats['total_failed'] += 1
            
            self.stats['total_tested'] += 1
        
        print(f"✅ Тестирование завершено: {working_count}/{tests_count} рабочих")
    
    async def _test_existing_proxies(self):
        """Повторное тестирование существующих прокси"""
        if not self.validated_pool:
            return
        
        # Тестируем только старые прокси (старше 5 минут)
        current_time = time.time()
        old_proxies = [
            (addr, info) for addr, info in self.validated_pool.items()
            if current_time - info.last_tested > 300  # 5 минут
        ]
        
        if not old_proxies:
            return
        
        print(f"🔄 Повторное тестирование {len(old_proxies)} старых прокси...")
        
        # Тестируем по одному чтобы не нагружать
        for proxy_address, old_info in old_proxies[:3]:  # Максимум 3 за раз
            try:
                new_info = await self._test_proxy_detailed(proxy_address)
                if new_info:
                    # Обновляем информацию
                    new_info.total_tests = old_info.total_tests + 1
                    new_info.success_rate = (old_info.success_rate * old_info.total_tests + 1) / new_info.total_tests
                    self.validated_pool[proxy_address] = new_info
                else:
                    # Прокси перестал работать
                    print(f"💀 Прокси перестал работать: {proxy_address}")
                    del self.validated_pool[proxy_address]
                    self.blacklist.add(proxy_address)
            except Exception as e:
                print(f"❌ Ошибка при повторном тестировании {proxy_address}: {e}")
    
    async def _cleanup_old_proxies(self):
        """Очистка старых и ненадежных прокси"""
        current_time = time.time()
        to_remove = []
        
        for proxy_address, proxy_info in self.validated_pool.items():
            # Удаляем очень старые прокси (старше 1 часа)
            if current_time - proxy_info.last_tested > 3600:
                to_remove.append(proxy_address)
            # Удаляем ненадежные прокси
            elif proxy_info.success_rate < self.min_success_rate:
                to_remove.append(proxy_address)
            # Удаляем медленные прокси
            elif proxy_info.response_time > self.max_response_time:
                to_remove.append(proxy_address)
        
        for proxy_address in to_remove:
            print(f"🧹 Удаляем старый/ненадежный прокси: {proxy_address}")
            del self.validated_pool[proxy_address]
    
    async def _test_proxy_detailed(self, proxy_address: str) -> Optional[ProxyInfo]:
        """
        Детальное тестирование прокси с замером времени
        
        Args:
            proxy_address: Адрес прокси в формате ip:port
            
        Returns:
            ProxyInfo если прокси работает, None если нет
        """
        proxy_url = f"http://{proxy_address}"
        
        try:
            start_time = time.time()
            
            # Тестируем с коротким таймаутом
            timeout = aiohttp.ClientTimeout(total=6, connect=3)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    "http://httpbin.org/ip",
                    proxy=proxy_url
                ) as response:
                    if response.status == 200:
                        response_time = time.time() - start_time
                        data = await response.json()
                        proxy_ip = data.get('origin', 'unknown')
                        
                        # Определяем страну (упрощенно)
                        country = 'Unknown'
                        
                        return ProxyInfo(
                            server=proxy_address,
                            country=country,
                            response_time=response_time,
                            last_tested=time.time(),
                            success_rate=1.0,  # Начальное значение
                            total_tests=1,
                            consecutive_failures=0,
                            source='mixed'
                        )
        
        except Exception:
            pass  # Тихо игнорируем ошибки
        
        return None
    
    # Источники прокси
    async def _fetch_from_free_proxy_list(self) -> List[str]:
        """Загрузка из free-proxy-list.net"""
        try:
            fp = FreeProxy(
                country_id=['US', 'GB', 'DE', 'CA', 'AU', 'NL', 'FR'],
                timeout=3,
                rand=True,
                anonym=True
            )
            return fp.get_proxy_list(repeat=False)
        except:
            return []
    
    async def _fetch_from_ssl_proxies(self) -> List[str]:
        """Загрузка из sslproxies.org"""
        try:
            fp = FreeProxy(
                country_id=['US', 'GB', 'DE'],
                timeout=3,
                rand=True,
                https=False
            )
            return fp.get_proxy_list(repeat=True)
        except:
            return []
    
    async def _fetch_from_proxy_list_download(self) -> List[str]:
        """Загрузка из proxy-list.download API"""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get("https://www.proxy-list.download/api/v1/get?type=http") as response:
                    if response.status == 200:
                        text = await response.text()
                        proxies = [line.strip() for line in text.strip().split('\n') if ':' in line]
                        return proxies[:50]  # Максимум 50
        except:
            pass
        return []

# Глобальный экземпляр менеджера
_pool_manager = None

async def get_pool_manager() -> ProxyPoolManager:
    """Получить глобальный экземпляр менеджера пула"""
    global _pool_manager
    if _pool_manager is None:
        _pool_manager = ProxyPoolManager(
            target_pool_size=config.FREE_PROXY_CONFIG.get('pool_size', 5),
            test_interval=20.0,  # Тестируем каждые 20 секунд
            max_response_time=8.0
        )
        await _pool_manager.start()
    return _pool_manager

async def get_instant_proxy() -> Optional[Dict]:
    """Мгновенно получить лучший прокси из пула"""
    manager = await get_pool_manager()
    return await manager.get_best_proxy()

async def get_random_proxy_from_pool() -> Optional[Dict]:
    """Получить случайный прокси из пула"""
    manager = await get_pool_manager()
    return await manager.get_random_proxy()

async def report_bad_proxy(proxy_server: str):
    """Сообщить о плохом прокси"""
    manager = await get_pool_manager()
    await manager.report_proxy_failure(proxy_server)

def get_pool_stats() -> Dict:
    """Получить статистику пула"""
    global _pool_manager
    if _pool_manager:
        return _pool_manager.get_pool_status()
    return {'error': 'Pool manager not initialized'}

# Пример использования
async def main():
    """Демонстрация работы ProxyPoolManager"""
    print("🚀 Демонстрация ProxyPoolManager")
    
    # Запускаем менеджер
    manager = await get_pool_manager()
    
    # Ждем заполнения пула
    print("⏳ Ждем заполнения пула...")
    await asyncio.sleep(10)
    
    # Получаем прокси
    for i in range(5):
        proxy = await get_instant_proxy()
        if proxy:
            print(f"✅ Прокси {i+1}: {proxy['server']}")
        else:
            print(f"❌ Не удалось получить прокси {i+1}")
        await asyncio.sleep(1)
    
    # Показываем статистику
    stats = get_pool_stats()
    print(f"\n📊 Статистика пула:")
    print(f"   Рабочих прокси: {stats['validated_count']}")
    print(f"   В очереди: {stats['testing_queue_count']}")
    print(f"   В черном списке: {stats['blacklist_count']}")
    
    # Останавливаем менеджер
    await manager.stop()

if __name__ == "__main__":
    asyncio.run(main())