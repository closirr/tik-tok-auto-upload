#!/usr/bin/env python3
"""
Исследование готовых библиотек для тестирования прокси
"""

import requests
import json
import time

def search_pypi_packages():
    """Поиск пакетов на PyPI связанных с прокси"""
    
    search_terms = [
        "proxy checker",
        "proxy validator", 
        "proxy pool",
        "proxy tester",
        "proxy manager",
        "async proxy"
    ]
    
    results = {}
    
    for term in search_terms:
        try:
            print(f"\n🔍 Поиск: '{term}'")
            
            # PyPI search API
            url = f"https://pypi.org/search/?q={term.replace(' ', '+')}"
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            
            # Альтернативный поиск через libraries.io API
            libraries_url = f"https://libraries.io/api/search?q={term.replace(' ', '+')}&platforms=pypi"
            
            try:
                resp = requests.get(libraries_url, headers=headers, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    for pkg in data[:5]:  # Топ 5 результатов
                        name = pkg.get('name', 'Unknown')
                        description = pkg.get('description', 'No description')
                        stars = pkg.get('stars', 0)
                        print(f"  📦 {name} (⭐{stars})")
                        print(f"     {description[:100]}...")
                        
                        results[name] = {
                            'description': description,
                            'stars': stars,
                            'search_term': term
                        }
            except:
                pass
                
            time.sleep(1)  # Не спамим API
            
        except Exception as e:
            print(f"  ❌ Ошибка поиска '{term}': {e}")
    
    return results

def check_popular_proxy_libraries():
    """Проверяем популярные библиотеки для работы с прокси"""
    
    known_libraries = [
        "aiohttp-proxy",
        "proxy-checker", 
        "proxybroker",
        "proxy-pool",
        "rotating-proxies",
        "proxy-rotator",
        "async-proxy-pool",
        "proxy-validator",
        "proxyscrape",
        "proxy-harvester",
        "proxy-tester",
        "free-proxy",
        "proxy-requests"
    ]
    
    print("\n🔍 Проверка известных библиотек:")
    
    for lib in known_libraries:
        try:
            # Проверяем существование на PyPI
            url = f"https://pypi.org/pypi/{lib}/json"
            resp = requests.get(url, timeout=5)
            
            if resp.status_code == 200:
                data = resp.json()
                info = data['info']
                
                print(f"\n📦 {lib}")
                print(f"   Описание: {info.get('summary', 'Нет описания')}")
                print(f"   Версия: {info.get('version', 'Unknown')}")
                print(f"   Автор: {info.get('author', 'Unknown')}")
                print(f"   Последнее обновление: {info.get('upload_time', 'Unknown')}")
                
                # Проверяем популярность через GitHub если есть ссылка
                home_page = info.get('home_page', '')
                if 'github.com' in home_page:
                    print(f"   GitHub: {home_page}")
                    
        except Exception as e:
            print(f"❌ {lib}: не найден или ошибка")
            
        time.sleep(0.5)

def research_github_repos():
    """Исследуем репозитории на GitHub"""
    
    print("\n🔍 Поиск репозиториев на GitHub:")
    
    # Популярные поисковые запросы
    github_searches = [
        "proxy checker python",
        "proxy pool python async", 
        "proxy validator python",
        "proxy tester asyncio",
        "free proxy python"
    ]
    
    for search in github_searches:
        print(f"\n🔍 GitHub поиск: '{search}'")
        
        # Известные репозитории (без API, просто список)
        known_repos = [
            "constverum/ProxyBroker",
            "clarketm/proxy-list", 
            "fate0/proxylist",
            "stamparm/fetch-some-proxies",
            "TheSpeedX/PROXY-List",
            "jetkai/proxy-list",
            "monosans/proxy-list",
            "sunny9577/proxy-scraper",
            "rly0nheart/proxify"
        ]
        
        print("   Известные репозитории:")
        for repo in known_repos:
            print(f"     🔗 https://github.com/{repo}")

if __name__ == "__main__":
    print("🚀 Исследование библиотек для работы с прокси")
    print("=" * 50)
    
    # Поиск на PyPI
    try:
        results = search_pypi_packages()
        print(f"\n📊 Найдено {len(results)} пакетов")
    except Exception as e:
        print(f"❌ Ошибка поиска на PyPI: {e}")
    
    # Проверка известных библиотек
    try:
        check_popular_proxy_libraries()
    except Exception as e:
        print(f"❌ Ошибка проверки библиотек: {e}")
    
    # GitHub репозитории
    research_github_repos()
    
    print("\n" + "=" * 50)
    print("✅ Исследование завершено")