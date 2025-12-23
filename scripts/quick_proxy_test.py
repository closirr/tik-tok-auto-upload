#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Быстрая проверка одного прокси
Использование: python quick_proxy_test.py <proxy_url>
"""

import asyncio
import aiohttp
import sys
import time
from urllib.parse import urlparse

async def test_proxy(proxy_url):
    """Быстрая проверка одного прокси"""
    print(f"🔍 Тестирую прокси: {proxy_url}")
    
    try:
        start_time = time.time()
        
        connector = aiohttp.TCPConnector(limit=1)
        timeout = aiohttp.ClientTimeout(total=10)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        ) as session:
            
            # Проверяем IP
            async with session.get(
                'http://httpbin.org/ip',
                proxy=proxy_url
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    response_time = round(time.time() - start_time, 2)
                    ip = data.get('origin', 'Unknown')
                    
                    print(f"✅ Прокси работает!")
                    print(f"   IP: {ip}")
                    print(f"   Время ответа: {response_time}s")
                    
                    # Дополнительная проверка через ip-api
                    try:
                        async with session.get(
                            f'http://ip-api.com/json/{ip}',
                            proxy=proxy_url
                        ) as geo_response:
                            if geo_response.status == 200:
                                geo_data = await geo_response.json()
                                if geo_data.get('status') == 'success':
                                    location = f"{geo_data.get('country', '')}, {geo_data.get('city', '')}"
                                    print(f"   Локация: {location}")
                    except:
                        pass
                    
                    return True
                else:
                    print(f"❌ Ошибка HTTP: {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def main():
    """Основная функция"""
    if len(sys.argv) != 2:
        print("Использование: python quick_proxy_test.py <proxy_url>")
        print("Пример: python quick_proxy_test.py http://user:pass@proxy.com:8080")
        return
    
    proxy_url = sys.argv[1]
    
    # Проверяем формат URL
    try:
        parsed = urlparse(proxy_url)
        if not all([parsed.scheme, parsed.hostname, parsed.port]):
            print("❌ Неверный формат прокси URL")
            return
    except Exception as e:
        print(f"❌ Ошибка парсинга URL: {e}")
        return
    
    # Запускаем тест
    result = asyncio.run(test_proxy(proxy_url))
    
    if result:
        print("\n🎉 Прокси готов к использованию!")
    else:
        print("\n💥 Прокси не работает")

if __name__ == "__main__":
    main()