#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Чекер прокси Webshare.io
Проверяет список прокси на работоспособность
"""

import asyncio
import aiohttp
import time
from urllib.parse import urlparse
import json

# Список прокси для проверки
PROXIES = [
    'http://emaschipx-rotate:emaschipx@p.webshare.io:80/',
    'http://proxooo4-rotate:proxooo4@p.webshare.io:80/',
    'http://fabiorealdebrid-rotate:MammamiaHF1@p.webshare.io:80/',
    'http://proxoooo-rotate:proxoooo@p.webshare.io:80/',
    'http://teststremio-rotate:teststremio@p.webshare.io:80/',
    'http://mammapro-rotate:mammapro@p.webshare.io:80/',
    'http://iuhcxjzk-rotate:b3oqk3q40awp@p.webshare.io:80/',
    'http://zmjoluhu-rotate:ej6ddw3ily90@p.webshare.io:80/',
    'http://kkuafwyh-rotate:kl6esmu21js3@p.webshare.io:80/',
    'http://stzaxffz-rotate:ax92ravj1pmm@p.webshare.io:80/',
    'http://nfokjhhu-rotate:ez248bgee4z9@p.webshare.io:80/',
    'http://fiupzkjx-rotate:0zlrd2in3mrh@p.webshare.io:80/',
    'http://tpnvndgp-rotate:xjp0ux1wwc7n@p.webshare.io:80/',
    'http://tmglotxc-rotate:stlrhx17nhqj@p.webshare.io:80/',
]

# URL для проверки IP
CHECK_IP_URLS = [
    'http://httpbin.org/ip',
    'https://api.ipify.org?format=json',
    'http://ip-api.com/json'
]

class ProxyChecker:
    def __init__(self, timeout=10):
        self.timeout = timeout
        self.results = []
    
    def parse_proxy_url(self, proxy_url):
        """Парсит URL прокси и возвращает компоненты"""
        parsed = urlparse(proxy_url.rstrip('/'))
        return {
            'host': parsed.hostname,
            'port': parsed.port,
            'username': parsed.username,
            'password': parsed.password,
            'scheme': parsed.scheme
        }
    
    async def check_single_proxy(self, proxy_url, session):
        """Проверяет один прокси"""
        proxy_info = self.parse_proxy_url(proxy_url)
        proxy_name = proxy_info['username']
        
        print(f"🔍 Проверяю прокси: {proxy_name}")
        
        result = {
            'proxy_url': proxy_url,
            'proxy_name': proxy_name,
            'status': 'failed',
            'ip': None,
            'location': None,
            'response_time': None,
            'error': None
        }
        
        try:
            start_time = time.time()
            
            # Пробуем разные URL для проверки IP
            for check_url in CHECK_IP_URLS:
                try:
                    async with session.get(
                        check_url,
                        proxy=proxy_url,
                        timeout=aiohttp.ClientTimeout(total=self.timeout)
                    ) as response:
                        if response.status == 200:
                            response_time = round(time.time() - start_time, 2)
                            data = await response.json()
                            
                            # Извлекаем IP из разных форматов ответа
                            if 'origin' in data:
                                ip = data['origin']
                            elif 'ip' in data:
                                ip = data['ip']
                            elif 'query' in data:
                                ip = data['query']
                            else:
                                ip = str(data)
                            
                            result.update({
                                'status': 'working',
                                'ip': ip,
                                'response_time': response_time,
                                'check_url': check_url
                            })
                            
                            # Если это ip-api.com, получаем дополнительную информацию
                            if 'ip-api.com' in check_url and 'country' in data:
                                result['location'] = f"{data.get('country', '')}, {data.get('city', '')}"
                            
                            print(f"✅ {proxy_name}: IP {ip} ({response_time}s)")
                            break
                            
                except Exception as e:
                    continue
            
            if result['status'] == 'failed':
                print(f"❌ {proxy_name}: Не работает")
                result['error'] = "Все проверки не прошли"
                
        except Exception as e:
            result['error'] = str(e)
            print(f"❌ {proxy_name}: Ошибка - {e}")
        
        return result
    
    async def check_all_proxies(self):
        """Проверяет все прокси асинхронно"""
        print(f"🚀 Начинаю проверку {len(PROXIES)} прокси...")
        print("-" * 60)
        
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        timeout = aiohttp.ClientTimeout(total=self.timeout)
        
        async with aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        ) as session:
            
            tasks = [
                self.check_single_proxy(proxy, session) 
                for proxy in PROXIES
            ]
            
            self.results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Обрабатываем исключения
        processed_results = []
        for i, result in enumerate(self.results):
            if isinstance(result, Exception):
                processed_results.append({
                    'proxy_url': PROXIES[i],
                    'proxy_name': self.parse_proxy_url(PROXIES[i])['username'],
                    'status': 'failed',
                    'error': str(result)
                })
            else:
                processed_results.append(result)
        
        self.results = processed_results
    
    def print_summary(self):
        """Выводит сводку результатов"""
        print("\n" + "=" * 60)
        print("📊 СВОДКА РЕЗУЛЬТАТОВ")
        print("=" * 60)
        
        working = [r for r in self.results if r['status'] == 'working']
        failed = [r for r in self.results if r['status'] == 'failed']
        
        print(f"✅ Рабочих прокси: {len(working)}")
        print(f"❌ Нерабочих прокси: {len(failed)}")
        print(f"📈 Процент успеха: {len(working)/len(self.results)*100:.1f}%")
        
        if working:
            print(f"\n🚀 РАБОЧИЕ ПРОКСИ:")
            for result in working:
                location = f" ({result['location']})" if result.get('location') else ""
                print(f"  • {result['proxy_name']}: {result['ip']}{location} - {result['response_time']}s")
        
        if failed:
            print(f"\n💥 НЕРАБОЧИЕ ПРОКСИ:")
            for result in failed:
                error = f" - {result['error']}" if result.get('error') else ""
                print(f"  • {result['proxy_name']}{error}")
    
    def save_results(self, filename='proxy_check_results.json'):
        """Сохраняет результаты в JSON файл"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_proxies': len(self.results),
                'working_count': len([r for r in self.results if r['status'] == 'working']),
                'results': self.results
            }, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 Результаты сохранены в {filename}")

async def main():
    """Основная функция"""
    checker = ProxyChecker(timeout=15)
    
    try:
        await checker.check_all_proxies()
        checker.print_summary()
        checker.save_results('scripts/proxy_check_results.json')
        
    except KeyboardInterrupt:
        print("\n⏹️ Проверка прервана пользователем")
    except Exception as e:
        print(f"\n💥 Ошибка: {e}")

if __name__ == "__main__":
    asyncio.run(main())