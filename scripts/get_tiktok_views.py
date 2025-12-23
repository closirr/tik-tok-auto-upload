"""
Скрипт для получения количества просмотров видео TikTok
Использует oEmbed API и парсинг HTML
"""

import asyncio
import aiohttp
import re
import sys
import os

# Добавляем родительскую директорию в путь для импорта config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def format_number(num_str: str) -> str:
    """Форматирует число с суффиксами K, M, B"""
    try:
        num = int(num_str)
        if num >= 1_000_000_000:
            return f"{num / 1_000_000_000:.1f}B"
        elif num >= 1_000_000:
            return f"{num / 1_000_000:.1f}M"
        elif num >= 1_000:
            return f"{num / 1_000:.1f}K"
        return str(num)
    except:
        return num_str


async def get_video_views_oembed(video_url: str) -> dict:
    """
    Получает информацию о видео через oEmbed API TikTok
    """
    result = {
        'url': video_url,
        'views': None,
        'likes': None,
        'comments': None,
        'shares': None,
        'title': None,
        'author': None,
        'error': None
    }
    
    try:
        oembed_url = f"https://www.tiktok.com/oembed?url={video_url}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Accept': 'application/json'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(oembed_url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    data = await response.json()
                    result['title'] = data.get('title', '')
                    result['author'] = data.get('author_name', '')
                    print(f"Автор: {result['author']}")
                    print(f"Название: {result['title']}")
                else:
                    print(f"oEmbed API вернул статус: {response.status}")
                    
    except Exception as e:
        print(f"Ошибка oEmbed: {e}")
    
    return result


async def get_video_views_html(video_url: str) -> dict:
    """
    Получает статистику видео через парсинг HTML страницы
    """
    result = {
        'url': video_url,
        'views': None,
        'likes': None,
        'comments': None,
        'shares': None,
        'error': None
    }
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(video_url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status == 200:
                    html = await response.text()
                    
                    # Ищем JSON данные в SIGI_STATE
                    sigi_match = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>([^<]+)</script>', html)
                    if sigi_match:
                        import json
                        try:
                            data = json.loads(sigi_match.group(1))
                            # Ищем статистику в данных
                            default_scope = data.get('__DEFAULT_SCOPE__', {})
                            video_detail = default_scope.get('webapp.video-detail', {})
                            item_info = video_detail.get('itemInfo', {})
                            item_struct = item_info.get('itemStruct', {})
                            stats = item_struct.get('stats', {})
                            
                            if stats:
                                result['views'] = format_number(str(stats.get('playCount', '')))
                                result['likes'] = format_number(str(stats.get('diggCount', '')))
                                result['comments'] = format_number(str(stats.get('commentCount', '')))
                                result['shares'] = format_number(str(stats.get('shareCount', '')))
                                
                                print(f"Просмотры: {result['views']}")
                                print(f"Лайки: {result['likes']}")
                                print(f"Комментарии: {result['comments']}")
                                print(f"Репосты: {result['shares']}")
                        except json.JSONDecodeError as e:
                            print(f"Ошибка парсинга JSON: {e}")
                    
                    # Альтернативный поиск в мета-тегах
                    if not result['views']:
                        og_desc = re.search(r'<meta[^>]*property="og:description"[^>]*content="([^"]*)"', html)
                        if og_desc:
                            desc = og_desc.group(1)
                            # Ищем паттерн "123 Likes, 45 Comments"
                            likes_match = re.search(r'([\d.]+[KMB]?)\s*(?:Likes|лайк)', desc, re.IGNORECASE)
                            if likes_match:
                                result['likes'] = likes_match.group(1)
                else:
                    result['error'] = f"HTTP статус: {response.status}"
                    
    except Exception as e:
        result['error'] = str(e)
        print(f"Ошибка: {e}")
    
    return result


async def main():
    # URL видео для проверки
    video_url = "https://www.tiktok.com/@tftk007/video/7582089146269748494"
    
    print("=" * 50)
    print("Получение статистики видео TikTok")
    print("=" * 50)
    print(f"URL: {video_url}\n")
    
    # Пробуем получить данные через HTML парсинг
    print("Метод 1: Парсинг HTML...")
    result = await get_video_views_html(video_url)
    
    # Если не получилось, пробуем oEmbed
    if not result['views']:
        print("\nМетод 2: oEmbed API...")
        oembed_result = await get_video_views_oembed(video_url)
        result.update({k: v for k, v in oembed_result.items() if v})
    
    print("\n" + "=" * 50)
    print("РЕЗУЛЬТАТ:")
    print("=" * 50)
    print(f"URL: {result['url']}")
    print(f"Просмотры: {result['views'] or 'Не удалось получить'}")
    print(f"Лайки: {result['likes'] or 'Не удалось получить'}")
    print(f"Комментарии: {result['comments'] or 'Не удалось получить'}")
    print(f"Репосты: {result['shares'] or 'Не удалось получить'}")
    
    if result.get('error'):
        print(f"Ошибка: {result['error']}")


if __name__ == "__main__":
    asyncio.run(main())
