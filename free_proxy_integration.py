#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Интеграция free-proxy с TikTok Auto Upload
Модуль для получения бесплатных прокси в качестве основного источника
"""

import asyncio
import aiohttp
import random
from fp.fp import FreeProxy
from fp.errors import FreeProxyException
from typing import Optional, List, Dict
import logging
import time
import config

logger = logging.getLogger(__name__)

# Глобальный блеклист прокси которые не работают с TikTok
# Эти прокси проходят тест но не грузят TikTok
GLOBAL_PROXY_BLACKLIST = {
    "134.209.29.120",  # DigitalOcean London - не грузит TikTok
}

class FreeProxyManager:
    """Менеджер для работы с бесплатными прокси"""
    
    def __init__(self):
        self.tested_proxies = []  # Кэш протестированных прокси
        self.failed_proxies = set()  # Список неработающих прокси
        self.current_proxy_index = 0  # Индекс для ротации прокси
        self.proxy_list = []  # Полный список прокси из источника
        self.proxy_list_index = 0  # Текущий индекс в списке прокси
        self.last_list_refresh = 0  # Время последнего обновления списка
        self.list_refresh_interval = 300  # Обновлять список каждые 5 минут
        self.total_tested = 0  # Счётчик протестированных прокси (для статистики)
        
        # Добавляем глобальный блеклист в failed_proxies
        for ip in GLOBAL_PROXY_BLACKLIST:
            self.failed_proxies.add(f"http://{ip}:80")
            self.failed_proxies.add(f"http://{ip}:8080")
            self.failed_proxies.add(f"http://{ip}:3128")
        
    async def get_working_proxy(self, 
                               country_id: Optional[List[str]] = None,
                               https: bool = False,
                               anonym: bool = True,
                               timeout: float = 5.0,
                               max_attempts: int = None) -> Optional[Dict]:
        """
        Получить рабочий прокси в формате Playwright
        Ищет бесконечно пока не найдёт рабочий прокси
        
        Args:
            country_id: Список кодов стран ['US', 'GB', 'DE']
            https: Требовать HTTPS прокси
            anonym: Требовать анонимный прокси
            timeout: Таймаут для проверки прокси
            max_attempts: Игнорируется, ищет бесконечно
            
        Returns:
            Словарь с настройками прокси для Playwright
        """
        print(f"🔍 Поиск бесплатного прокси (бесконечный поиск)...")
        
        # Используем настройки из конфигурации
        if country_id is None:
            country_id = config.FREE_PROXY_CONFIG['country_id']
        if not https:
            https = config.FREE_PROXY_CONFIG['https']
        if anonym:
            anonym = config.FREE_PROXY_CONFIG['anonym']
        
        # Бесконечный цикл поиска прокси
        while True:
            # Загружаем или обновляем список прокси
            await self._ensure_proxy_list(country_id, https, anonym, timeout)
            
            if not self.proxy_list:
                print("⚠️  Список прокси пуст, ждём 5 сек и пробуем снова...")
                await asyncio.sleep(5)
                self.last_list_refresh = 0  # Форсируем обновление
                continue
            
            # Выбираем случайный прокси из списка (исключаем блеклист)
            available_proxies = []
            for p in self.proxy_list:
                proxy_url = f"http://{p}"
                proxy_ip = p.split(':')[0]
                # Проверяем что прокси не в failed_proxies и IP не в глобальном блеклисте
                if proxy_url not in self.failed_proxies and proxy_ip not in GLOBAL_PROXY_BLACKLIST:
                    available_proxies.append(p)
            
            if not available_proxies:
                print("🔄 Все прокси в списке проверены, обновляем список...")
                self.proxy_list = []
                self.failed_proxies.clear()  # Очищаем список неработающих для повторной проверки
                self.last_list_refresh = 0
                await asyncio.sleep(2)
                continue
            
            # Выбираем случайный прокси
            proxy_address = random.choice(available_proxies)
            proxy_url = f"http://{proxy_address}"
            
            self.total_tested += 1
            print(f"🔄 Тестируем прокси #{self.total_tested}: {proxy_url}")
            
            # Тестируем прокси
            if await self._test_proxy(proxy_url, timeout=12):
                # Конвертируем в формат Playwright
                proxy_config = {
                    'server': proxy_url,
                    'username': None,
                    'password': None
                }
                
                # Сохраняем в кэш
                self.tested_proxies.append({
                    'config': proxy_config,
                    'url': proxy_url,
                    'tested_at': time.time(),
                    'country': country_id,
                    'https': https
                })
                
                print(f"✅ Прокси {proxy_url} готов к использованию (проверено {self.total_tested} прокси)")
                return proxy_config
            else:
                self.failed_proxies.add(proxy_url)
    
    async def _ensure_proxy_list(self, country_id, https, anonym, timeout):
        """Загружает или обновляет список прокси если нужно"""
        current_time = time.time()
        
        # Обновляем список если он пуст или устарел
        if not self.proxy_list or (current_time - self.last_list_refresh > self.list_refresh_interval):
            print("📥 Загрузка списка прокси из источников...")
            proxy_list = []
            
            # Источник 1: free-proxy библиотека
            try:
                fp = FreeProxy(
                    country_id=country_id,
                    https=https,
                    anonym=anonym,
                    timeout=timeout,
                    rand=True
                )
                
                try:
                    fp_list = fp.get_proxy_list(repeat=False)
                    proxy_list.extend(fp_list)
                    print(f"   free-proxy (основной): {len(fp_list)} прокси")
                except:
                    pass
                
                try:
                    fp_list_alt = fp.get_proxy_list(repeat=True)
                    proxy_list.extend(fp_list_alt)
                    print(f"   free-proxy (альт): {len(fp_list_alt)} прокси")
                except:
                    pass
            except Exception as e:
                print(f"   free-proxy ошибка: {e}")
            
            # Источник 2: proxyscrape.com API (сотни прокси)
            extra_proxies = await self._fetch_extra_proxies()
            if extra_proxies:
                proxy_list.extend(extra_proxies)
            
            # Убираем дубликаты и перемешиваем
            proxy_list = list(set(proxy_list))
            random.shuffle(proxy_list)
            
            if proxy_list:
                self.proxy_list = proxy_list
                self.proxy_list_index = 0
                self.last_list_refresh = current_time
                print(f"✅ Всего загружено {len(self.proxy_list)} уникальных прокси")
            else:
                print("⚠️  Не удалось загрузить прокси из источников")
    
    async def _fetch_extra_proxies(self) -> List[str]:
        """Загружает прокси из дополнительных бесплатных API (только качественные источники)"""
        extra_proxies = []
        
        # Только качественные источники с небольшим количеством прокси
        proxy_apis = [
            # proxy-list.download - ~90 прокси, хорошее качество
            "https://www.proxy-list.download/api/v1/get?type=http",
        ]
        
        client_timeout = aiohttp.ClientTimeout(total=10)
        
        for api_url in proxy_apis:
            try:
                async with aiohttp.ClientSession(timeout=client_timeout) as session:
                    async with session.get(api_url) as response:
                        if response.status == 200:
                            text = await response.text()
                            # Парсим прокси (формат ip:port на каждой строке)
                            lines = text.strip().split('\n')
                            proxies = [line.strip() for line in lines if ':' in line and line.strip()]
                            if proxies:
                                extra_proxies.extend(proxies)
                                api_name = api_url.split('/')[2]
                                print(f"   {api_name}: {len(proxies)} прокси")
            except Exception as e:
                # Тихо пропускаем ошибки - не все API могут быть доступны
                pass
        
        return extra_proxies
    
    def clear_cache(self):
        """Очистить кэш прокси"""
        self.tested_proxies.clear()
        self.failed_proxies.clear()
        self.current_proxy_index = 0
        self.total_tested = 0
        print("🗑️ Кэш прокси очищен")
    
    async def _test_proxy(self, proxy_url: str, test_url: str = "http://httpbin.org/ip", timeout: float = 12) -> bool:
        """
        Оптимизированное тестирование прокси
        
        Args:
            proxy_url: URL прокси для тестирования
            test_url: URL для тестирования прокси
            timeout: Таймаут для тестирования
            
        Returns:
            True если прокси работает
        """
        try:
            # Используем более короткий таймаут для быстрого отсева неработающих прокси
            client_timeout = aiohttp.ClientTimeout(total=timeout, connect=timeout/2)
            
            async with aiohttp.ClientSession(timeout=client_timeout) as session:
                async with session.get(
                    test_url,
                    proxy=proxy_url,
                    timeout=client_timeout
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        proxy_ip = data.get('origin', 'unknown')
                        print(f"✅ Прокси работает! IP: {proxy_ip}")
                        return True
                    else:
                        print(f"❌ Прокси вернул статус: {response.status}")
                        return False
                        
        except asyncio.TimeoutError:
            print(f"⏱️  Таймаут при тестировании прокси {proxy_url}")
            return False
        except Exception as e:
            print(f"❌ Ошибка тестирования прокси {proxy_url}: {e}")
            return False
    
    async def get_proxy_pool(self, count: int = None) -> List[Dict]:
        """
        Получить пул рабочих прокси для ротации
        
        Args:
            count: Количество прокси (по умолчанию из конфигурации)
            
        Returns:
            Список конфигураций прокси для Playwright
        """
        if count is None:
            count = config.FREE_PROXY_CONFIG['pool_size']
            
        print(f"🔍 Создание пула из {count} бесплатных прокси...")
        
        working_proxies = []
        attempts = 0
        max_attempts = count * 3  # Максимум попыток
        
        while len(working_proxies) < count and attempts < max_attempts:
            attempts += 1
            proxy_config = await self.get_working_proxy(timeout=3.0)
            
            if proxy_config and proxy_config not in working_proxies:
                working_proxies.append(proxy_config)
                print(f"✅ Добавлен прокси {len(working_proxies)}/{count}")
            
            # Небольшая пауза между запросами
            await asyncio.sleep(1)
        
        print(f"🎯 Создан пул из {len(working_proxies)} рабочих прокси")
        return working_proxies
    
    def get_cached_proxy(self, max_age: int = None) -> Optional[Dict]:
        """
        Получить прокси из кэша
        
        Args:
            max_age: Максимальный возраст кэша в секундах
            
        Returns:
            Конфигурация прокси для Playwright или None
        """
        if max_age is None:
            max_age = config.FREE_PROXY_CONFIG['cache_time']
            
        current_time = time.time()
        
        for proxy_info in self.tested_proxies:
            if current_time - proxy_info['tested_at'] < max_age:
                print(f"📋 Использую кэшированный прокси: {proxy_info['url']}")
                return proxy_info['config']
        
        return None
    
    def get_next_proxy_from_pool(self, proxy_pool: List[Dict]) -> Optional[Dict]:
        """
        Получить следующий прокси из пула для ротации
        
        Args:
            proxy_pool: Пул прокси
            
        Returns:
            Конфигурация прокси для Playwright
        """
        if not proxy_pool:
            return None
            
        proxy = proxy_pool[self.current_proxy_index % len(proxy_pool)]
        self.current_proxy_index += 1
        
        print(f"🔄 Ротация прокси: {proxy['server']}")
        return proxy
    
    def clear_cache(self):
        """Очистить кэш прокси"""
        self.tested_proxies.clear()
        self.failed_proxies.clear()
        self.current_proxy_index = 0
        print("🗑️ Кэш прокси очищен")
    
    def remove_proxy_from_cache(self, proxy_server: str):
        """Удалить конкретный прокси из кэша (когда он перестал работать)"""
        for proxy_info in self.tested_proxies[:]:  # Копия списка для безопасного удаления
            if proxy_info['config']['server'] == proxy_server or proxy_info['url'] == proxy_server:
                self.tested_proxies.remove(proxy_info)
                self.failed_proxies.add(proxy_info['url'])
                print(f"🗑️ Прокси {proxy_server} удалён из кэша и добавлен в чёрный список")
                return True
        return False

# Глобальный экземпляр менеджера
_proxy_manager = None

def get_proxy_manager() -> FreeProxyManager:
    """Получить глобальный экземпляр менеджера прокси"""
    global _proxy_manager
    if _proxy_manager is None:
        _proxy_manager = FreeProxyManager()
    return _proxy_manager

# Функции для интеграции с TikTokManager
async def get_primary_proxy() -> Optional[Dict]:
    """
    Получить прокси для использования в TikTokManager
    Ищет бесконечно пока не найдёт рабочий прокси
    
    Returns:
        Конфигурация прокси для Playwright
    """
    manager = get_proxy_manager()
    
    # Если есть прокси в кэше — берём следующий по очереди (ротация)
    if manager.tested_proxies:
        proxy_info = manager.tested_proxies[manager.current_proxy_index % len(manager.tested_proxies)]
        manager.current_proxy_index += 1
        
        # Проверяем не истёк ли прокси
        cache_time = config.FREE_PROXY_CONFIG.get('cache_time', 120)
        if time.time() - proxy_info['tested_at'] < cache_time:
            print(f"🔄 Ротация прокси [{manager.current_proxy_index % len(manager.tested_proxies) + 1}/{len(manager.tested_proxies)}]: {proxy_info['url']}")
            return proxy_info['config']
        else:
            # Прокси истёк — удаляем из кэша
            print(f"⏰ Прокси {proxy_info['url']} истёк, удаляем из кэша")
            manager.tested_proxies.remove(proxy_info)
    
    # Если кэш пуст или все истекли — получаем новый прокси (бесконечный поиск)
    print("🔄 Получение нового бесплатного прокси...")
    return await manager.get_working_proxy()

async def refresh_proxy() -> Optional[Dict]:
    """
    Обновить прокси (аналог refresh_proxy_ip для бесплатных прокси)
    
    Returns:
        Новая конфигурация прокси для Playwright
    """
    print("🔄 Обновление бесплатного прокси...")
    manager = get_proxy_manager()
    
    # Очищаем кэш и получаем новый прокси
    manager.clear_cache()
    return await manager.get_working_proxy()

async def get_proxy_pool_for_batch() -> List[Dict]:
    """
    Создать пул прокси для пакетной обработки аккаунтов
    Полезно когда нужно обработать много аккаунтов подряд
    
    Returns:
        Список конфигураций прокси для Playwright
    """
    manager = get_proxy_manager()
    print("🏊 Создание пула прокси для пакетной обработки...")
    
    # Создаем небольшой пул из 3-5 прокси
    proxy_pool = await manager.get_proxy_pool(count=3)
    
    if proxy_pool:
        print(f"✅ Создан пул из {len(proxy_pool)} прокси для пакетной обработки")
        return proxy_pool
    else:
        print("❌ Не удалось создать пул прокси")
        return []

async def get_proxy_for_rotation() -> Optional[Dict]:
    """
    Получить прокси для ротации
    
    Returns:
        Конфигурация прокси для Playwright
    """
    manager = get_proxy_manager()
    
    # Если есть пул прокси, используем ротацию
    if hasattr(manager, '_proxy_pool') and manager._proxy_pool:
        return manager.get_next_proxy_from_pool(manager._proxy_pool)
    
    # Иначе получаем новый прокси
    return await get_primary_proxy()

# Пример использования
async def main():
    """Пример использования FreeProxyManager"""
    print("🚀 Тестирование FreeProxyManager для TikTok")
    
    manager = FreeProxyManager()
    
    # Получаем основной прокси
    proxy = await manager.get_working_proxy()
    if proxy:
        print(f"✅ Получен прокси: {proxy}")
    
    # Создаем пул прокси
    proxy_pool = await manager.get_proxy_pool(count=3)
    print(f"✅ Создан пул из {len(proxy_pool)} прокси")
    
    # Тестируем ротацию
    for i in range(5):
        rotated_proxy = manager.get_next_proxy_from_pool(proxy_pool)
        if rotated_proxy:
            print(f"🔄 Ротация {i+1}: {rotated_proxy['server']}")

if __name__ == "__main__":
    asyncio.run(main())