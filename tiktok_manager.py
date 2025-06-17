import asyncio
import json
import os
import re
import traceback
import shutil
from playwright.async_api import async_playwright
import glob
from tiktok_cookies_loader import CookiesLoader

class TikTokManager:
    def __init__(self, cookies_dir='cookies', videos_dir='videos'):
        self.cookies_dir = cookies_dir
        self.videos_dir = videos_dir
        self.cookies_loader = CookiesLoader(cookies_dir)
        self.proxy = {
            'server': 'http://109.236.82.42:9999',
            'username': 'xefrudrjaz-corp.res-country-GB-hold-session-session-6850a0db0a053',
            'password': '8tnmD7aIgSbBHSmD'
        }
        
        # Создаем директории, если они не существуют
        if not os.path.exists(videos_dir):
            os.makedirs(videos_dir)
            
    def get_first_video(self):
        """Получает путь к первому видео в указанной папке."""
        video_files = glob.glob(os.path.join(self.videos_dir, '*.*'))
        video_formats = ['.mp4', '.mov', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
        
        # Фильтрация только видео файлов
        video_files = [f for f in video_files if os.path.splitext(f)[1].lower() in video_formats]
        
        if not video_files:
            print(f"В папке {self.videos_dir} не найдено видео файлов.")
            return None
        
        # Сортировка по имени и выбор первого файла
        video_files.sort()
        return video_files[0]
    
    async def upload_video(self, page, video_path):
        """
        Загружает видео на TikTok Studio.
        
        Args:
            page: Объект страницы Playwright
            video_path: Путь к видеофайлу для загрузки
        
        Returns:
            bool: True, если загрузка запущена успешно, False в случае ошибки
        """
        try:
            # Найдем input для загрузки файла
            file_input = await page.query_selector('input[type="file"]')
            
            if file_input:
                # Используем абсолютный путь к видео
                abs_video_path = os.path.abspath(video_path)
                print(f"Загружаем видео: {abs_video_path}")
                
                # Устанавливаем файл в поле ввода
                await file_input.set_input_files(abs_video_path)
                
                print("Видео выбрано для загрузки")
                
                # Делаем скриншот после выбора файла
                await page.wait_for_timeout(2000)
                await page.screenshot(path="tiktok_file_selected.png")
                
                # Ждем достаточное время для завершения загрузки и обработки
                await page.wait_for_timeout(30000)  # 30 секунд
                return True
                
            else:
                print("Не удалось найти поле для загрузки файла")
                return False
        
        except Exception as e:
            print(f"Ошибка при загрузке видео: {str(e)}")
            await page.screenshot(path="tiktok_upload_error.png")
            return False
    
    async def process_account(self, cookie_file):
        """Обрабатывает один файл с куками"""
        print(f"Обработка файла с куками: {cookie_file}")
        
        # Загружаем куки из файла
        cookies = self.cookies_loader.load_cookies(cookie_file)
        if not cookies:
            print(f"Не удалось загрузить куки из файла {cookie_file}")
            self.cookies_loader.mark_cookie_as_invalid(cookie_file)
            return False
        
        # Получаем путь к первому видео
        video_path = self.get_first_video()
        if not video_path:
            print("Не удалось найти видео для загрузки. Убедитесь, что в папке videos есть видео файлы.")
            return False
        
        try:
            async with async_playwright() as p:
                browser = await p.firefox.launch(headless=False)
                
                context = await browser.new_context(
                    proxy=self.proxy,
                    locale='ru-RU',
                    user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36'
                )
                
                # Установить cookies
                await context.add_cookies(cookies)
                page = await context.new_page()
                await page.goto("https://tiktok.com", wait_until='load')
                await page.wait_for_timeout(5000)  # Ждем 5 секунд для загрузки страницы
                
                # Проверяем, авторизованы ли мы
                is_authenticated = await self.check_authentication(page)
                
                if is_authenticated:
                    # Переходим на страницу загрузки
                    await page.goto("https://www.tiktok.com/tiktokstudio/upload", wait_until='load')
                    await page.wait_for_timeout(5000)  # Ждем 5 секунд для загрузки страницы
                    
                    # Делаем скриншот страницы загрузки
                    await page.screenshot(path="tiktok_upload_page.png")
                    
                    # Загружаем видео
                    upload_success = await self.upload_video(page, video_path)
                    
                    if upload_success:
                        print("Загрузка видео запущена успешно")
                        self.cookies_loader.mark_cookie_as_valid(cookie_file)
                        # Ждем некоторое время перед закрытием браузера
                        await page.wait_for_timeout(10000)  # 10 секунд
                        return True
                    else:
                        print("Не удалось запустить загрузку видео")
                        self.cookies_loader.mark_cookie_as_invalid(cookie_file)
                        return False
                else:
                    print("Не удалось авторизоваться с данными куками")
                    self.cookies_loader.mark_cookie_as_invalid(cookie_file)
                    return False
        
        except Exception as e:
            print(f"Ошибка при обработке куков {cookie_file}: {str(e)}")
            traceback.print_exc()
            self.cookies_loader.mark_cookie_as_invalid(cookie_file)
            return False
    
    async def check_authentication(self, page):
        """Проверяет, авторизован ли пользователь на странице TikTok"""
        try:
            # Делаем скриншот для проверки
            await page.screenshot(path="tiktok_auth_check.png")
            
            # Проверяем наличие элементов, которые обычно видны только авторизованным пользователям
            # Например, иконка профиля или другие элементы интерфейса
            profile_icon = await page.query_selector('[data-e2e="profile-icon"]')
            if profile_icon:
                print("Пользователь авторизован")
                return True
            
            # Дополнительные проверки - можно настроить в зависимости от интерфейса TikTok
            login_button = await page.query_selector('[data-e2e="top-login-button"]')
            if login_button:
                print("Пользователь не авторизован, найдена кнопка логина")
                return False
                
            # Если не нашли явных признаков авторизации или ее отсутствия, проверяем URL
            current_url = page.url
            if '/login' in current_url:
                print("Перенаправлено на страницу логина")
                return False
                
            # Дополнительная проверка - пробуем перейти на страницу, доступную только авторизованным пользователям
            await page.goto("https://www.tiktok.com/tiktokstudio", wait_until='load')
            await page.wait_for_timeout(3000)
            
            # Если URL содержит /login, значит нас перенаправили на страницу логина
            if '/login' in page.url:
                print("При переходе на TikTok Studio перенаправлено на страницу логина")
                return False
                
            print("Успешный переход на TikTok Studio, пользователь авторизован")
            return True
            
        except Exception as e:
            print(f"Ошибка при проверке авторизации: {str(e)}")
            return False 