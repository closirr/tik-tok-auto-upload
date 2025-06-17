import asyncio
import json
import os
import re
import traceback
import shutil
from playwright.async_api import async_playwright
import glob
import aiohttp
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
        self.proxy_refresh_url = "https://api.asocks.com/user/port/refresh/ip/fc20ca0b-4b04-11f0-8ac2-bc24114c89e8"
        
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
                print("Ждем загрузку видео...")
                await page.wait_for_timeout(8000)  # 8 секунд
                
                # Проверяем наличие дополнительных форм или шагов
                await self.handle_additional_forms(page)
                
                # Публикуем видео
                publication_result = await self.publish_video(page)
                
                return True
                
            else:
                print("Не удалось найти поле для загрузки файла")
                return False
        
        except Exception as e:
            print(f"Ошибка при загрузке видео: {str(e)}")
            await page.screenshot(path="tiktok_upload_error.png")
            return False
            
    async def publish_video(self, page):
        """Публикует загруженное видео, нажимая на кнопку 'Опубликовать'"""
        try:
            # Нажимаем на кнопку "Опубликовать"
            print("Ищем кнопку 'Опубликовать'...")
            publish_button = await page.query_selector('[data-e2e="post_video_button"]')
            
            if publish_button:
                print("Нажимаем на кнопку 'Опубликовать'")
                await publish_button.click()
                print("Видео отправлено на публикацию")
                await page.wait_for_timeout(5000)  # Ждем 5 секунд после публикации
                await page.screenshot(path="tiktok_published.png")
                
                # Проверяем успешность публикации
                success = await self.check_publication_success(page)
                if success:
                    print("Видео успешно опубликовано")
                    return True
                else:
                    print("Не удалось подтвердить успешность публикации")
                    return False
            else:
                print("Кнопка 'Опубликовать' не найдена")
                # Попробуем найти другие элементы с похожим текстом
                button = await page.query_selector('button:has-text("Опубликовать")')
                if button:
                    print("Найдена кнопка с текстом 'Опубликовать', нажимаем")
                    await button.click()
                    print("Видео отправлено на публикацию")
                    await page.wait_for_timeout(5000)
                    await page.screenshot(path="tiktok_published.png")
                    
                    # Проверяем успешность публикации
                    success = await self.check_publication_success(page)
                    if success:
                        print("Видео успешно опубликовано")
                        return True
                    else:
                        print("Не удалось подтвердить успешность публикации")
                        return False
                else:
                    print("Не удалось найти кнопку публикации")
                    await page.screenshot(path="tiktok_no_publish_button.png")
                    return False
        except Exception as e:
            print(f"Ошибка при публикации видео: {str(e)}")
            await page.screenshot(path="tiktok_publish_error.png")
            return False
    
    async def handle_additional_forms(self, page):
        """Обрабатывает дополнительные формы или шаги публикации, если они есть"""
        try:
            # Проверяем наличие формы описания
            description_field = await page.query_selector('textarea[placeholder*="опис"], textarea[placeholder*="Напиш"]')
            if description_field:
                print("Найдено поле для описания видео, заполняем")
                await description_field.fill("🔥 #viral #trending")
                
            # Проверяем наличие кнопок "Далее" или "Продолжить"
            next_button = await page.query_selector('button:has-text("Далее"), button:has-text("Продолжить"), button:has-text("Next"), [data-e2e="next-button"]')
            if next_button:
                print("Найдена кнопка 'Далее', нажимаем")
                await next_button.click()
                await page.wait_for_timeout(3000)
                
                # Возможно, есть еще шаги - рекурсивно проверяем
                await self.handle_additional_forms(page)
        
        except Exception as e:
            print(f"Ошибка при обработке дополнительных форм: {str(e)}")
            
    async def check_publication_success(self, page):
        """Проверяет успешность публикации видео"""
        try:
            # Ждем, пока появится сообщение об успехе или истечет таймаут
            success_message = None
            try:
                # Ищем разные варианты сообщений об успешной публикации
                success_message = await page.wait_for_selector(
                    'text="успешно", text="опубликовано", text="published", text="success"', 
                    timeout=10000
                )
            except:
                pass
                
            if success_message:
                print("Найдено сообщение об успешной публикации")
                return True
                
            # Проверяем, перенаправились ли мы на страницу со списком видео
            if '/tiktokstudio/content' in page.url or '/creator' in page.url:
                print("Перенаправлены на страницу контента, публикация успешна")
                return True
                
            return False
            
        except Exception as e:
            print(f"Ошибка при проверке успешности публикации: {str(e)}")
            return False
    
    async def refresh_proxy_ip(self):
        """Обновляет IP-адрес прокси перед работой с аккаунтом"""
        try:
            print("Обновление IP-адреса прокси...")
            async with aiohttp.ClientSession() as session:
                async with session.get(self.proxy_refresh_url) as response:
                    if response.status == 200:
                        response_data = await response.json()
                        if response_data.get("success"):
                            session_id = response_data.get("session")
                            login = response_data.get("login")
                            print(f"IP прокси успешно обновлен. Сессия: {session_id}")
                            
                            # Обновляем логин прокси с новой сессией
                            if session_id and login:
                                self.proxy['username'] = login
                                print(f"Обновлен логин прокси: {login}")
                            
                            return True
                        else:
                            print("Ошибка при обновлении IP: сервер вернул успех=false")
                            return False
                    else:
                        print(f"Ошибка при обновлении IP прокси. Код ответа: {response.status}")
                        return False
        except Exception as e:
            print(f"Ошибка при обновлении IP прокси: {str(e)}")
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
        
        # Обновляем IP прокси перед работой с аккаунтом
        proxy_refreshed = await self.refresh_proxy_ip()
        if not proxy_refreshed:
            print("Предупреждение: Не удалось обновить IP прокси, но продолжаем с текущим IP")
        
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
                        print("Загрузка и публикация видео выполнены")
                        self.cookies_loader.mark_cookie_as_valid(cookie_file)
                        # Ждем некоторое время перед закрытием браузера
                        await page.wait_for_timeout(10000)  # 10 секунд
                        return True
                    else:
                        print("Не удалось загрузить или опубликовать видео")
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