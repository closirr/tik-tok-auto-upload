import asyncio
import os
import re
import traceback
import datetime
from playwright.async_api import async_playwright
import aiohttp
from instagram_cookies_loader import InstagramCookiesLoader
import config

class InstagramManager:
    def __init__(self, cookies_dir='instagram_cookies', screenshots_dir='instagram_screenshots'):
        self.cookies_dir = cookies_dir
        self.screenshots_dir = screenshots_dir
        self.cookies_loader = InstagramCookiesLoader(cookies_dir)
        self.current_screenshot_dir = None
        self.proxy = config.PROXY
        self.proxy_refresh_url = config.PROXY_REFRESH_URL
        self.use_proxy_rotation = config.USE_PROXY_ROTATION
        
        for directory in [cookies_dir, screenshots_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
            
    def prepare_screenshot_directory(self, cookie_file):
        """Создает директорию для скриншотов текущей сессии"""
        cookie_name = os.path.basename(cookie_file).split('.')[0]
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        screenshot_dir = os.path.join(self.screenshots_dir, f"{cookie_name}_{timestamp}")
        os.makedirs(screenshot_dir, exist_ok=True)
        self.current_screenshot_dir = screenshot_dir
        print(f"Создана директория для скриншотов: {screenshot_dir}")
        return screenshot_dir
    
    def mark_screenshot_directory(self, cookie_file, is_valid):
        """Переименовывает директорию скриншотов со статусом"""
        if not self.current_screenshot_dir or not os.path.exists(self.current_screenshot_dir):
            return
        
        base_dir = os.path.dirname(self.current_screenshot_dir)
        current_dir_name = os.path.basename(self.current_screenshot_dir)
        
        if is_valid is None:
            status = "skipped"
        else:
            status = "valid" if is_valid else "invalid"
            
        new_dir_name = f"{status}_{current_dir_name}"
        new_dir_path = os.path.join(base_dir, new_dir_name)
        
        try:
            os.rename(self.current_screenshot_dir, new_dir_path)
            self.current_screenshot_dir = new_dir_path
            print(f"Директория скриншотов помечена как {status}")
        except Exception as e:
            print(f"Ошибка при переименовании директории: {str(e)}")
    
    async def take_screenshot(self, page, filename):
        """Делает скриншот страницы"""
        if not self.current_screenshot_dir:
            return None
        
        screenshot_path = os.path.join(self.current_screenshot_dir, filename)
        try:
            await page.screenshot(path=screenshot_path)
            print(f"Скриншот сохранен: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            print(f"Ошибка при сохранении скриншота: {str(e)}")
            return None
    
    async def refresh_proxy_ip(self):
        """Обновляет IP-адрес прокси"""
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
                            
                            if session_id and login:
                                self.proxy['username'] = login
                            return True
                    return False
        except Exception as e:
            print(f"Ошибка при обновлении IP прокси: {str(e)}")
            return False
    
    async def handle_cookie_consent(self, page):
        """Обрабатывает диалог согласия на cookie"""
        try:
            consent_selectors = [
                'button:has-text("Allow all cookies")',
                'button:has-text("Allow essential and optional cookies")',
                'button:has-text("Accept")',
                'button:has-text("Accept All")',
                'button:has-text("Принять")',
                'button:has-text("Разрешить")',
                '[data-testid="cookie-policy-manage-dialog-accept-button"]',
            ]
            
            for selector in consent_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        await button.click()
                        print(f"Нажата кнопка согласия на cookie: {selector}")
                        await page.wait_for_timeout(1000)
                        return True
                except:
                    continue
            return False
        except Exception as e:
            print(f"Ошибка при обработке cookie consent: {str(e)}")
            return False

    async def check_authentication(self, page):
        """Проверяет, авторизован ли пользователь на Instagram"""
        try:
            print("Проверка авторизации на Instagram...")
            
            # Переходим на главную страницу Instagram
            await page.goto("https://www.instagram.com/", wait_until='domcontentloaded', timeout=60000)
            
            print("Ожидание загрузки страницы...")
            await page.wait_for_timeout(5000)
            
            await self.take_screenshot(page, "instagram_main_page.png")
            
            # Обрабатываем cookie consent
            await self.handle_cookie_consent(page)
            await page.wait_for_timeout(2000)
            
            current_url = page.url
            
            # Проверка на страницу подтверждения пароля (сессия валидна, но требует подтверждения)
            password_confirm_selectors = [
                'input[name="password"]:not([name="username"])',  # Только поле пароля без username
                'button:has-text("Confirm")',
                'button:has-text("Подтвердить")',
            ]
            
            # Проверяем URL на признаки подтверждения (challenge, verify, confirm)
            is_password_confirm = any(x in current_url for x in ['/challenge/', '/verify/', '/confirm', 'suspicious'])
            
            # Проверяем наличие только поля пароля (без username) - признак подтверждения
            has_password_only = False
            password_field = await page.query_selector('input[name="password"]')
            username_field = await page.query_selector('input[name="username"]')
            if password_field and not username_field:
                has_password_only = True
                print("Обнаружена форма подтверждения пароля (сессия валидна)")
                is_password_confirm = True
            
            if is_password_confirm:
                print("Сессия валидна, но требует подтверждения пароля")
                await self.take_screenshot(page, "instagram_password_confirm.png")
                return True  # Считаем валидным - сессия есть, просто нужно подтверждение
            
            # Селекторы признаков авторизации
            auth_selectors = [
                'svg[aria-label="Home"]',
                'svg[aria-label="Главная"]',
                'a[href="/direct/inbox/"]',
                'svg[aria-label="New post"]',
                'svg[aria-label="Новая публикация"]',
                'svg[aria-label="Search"]',
                'span[aria-label="Profile"]',
                'img[data-testid="user-avatar"]',
                'a[href*="/accounts/edit/"]',
            ]
            
            # Селекторы формы входа (признак отсутствия авторизации - есть И username И password)
            login_form_indicators = [
                'input[name="username"]',
            ]
            
            # Проверяем признаки авторизации
            is_authenticated = False
            for selector in auth_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        print(f"Найден элемент авторизации: {selector}")
                        is_authenticated = True
                        break
                except:
                    continue
            
            # Проверяем наличие полной формы входа (username + password)
            has_login_form = False
            if username_field and password_field:
                print("Найдена полная форма входа (username + password)")
                has_login_form = True
            
            # Дополнительная проверка через URL
            if '/accounts/login' in current_url:
                print("Перенаправлены на страницу входа")
                has_login_form = True
                is_authenticated = False
            
            # Проверка через HTML контент
            page_content = await page.content()
            auth_indicators = [
                '"viewer":{',
                '"isLoggedIn":true',
                'viewerId',
            ]
            
            for indicator in auth_indicators:
                if indicator in page_content:
                    print(f"Найден признак авторизации в HTML: {indicator}")
                    is_authenticated = True
                    break
            
            # Финальное решение
            if is_authenticated and not has_login_form:
                print("Пользователь авторизован на Instagram")
                await self.take_screenshot(page, "instagram_authenticated.png")
                return True
            else:
                print("Пользователь НЕ авторизован на Instagram")
                await self.take_screenshot(page, "instagram_not_authenticated.png")
                return False
                
        except Exception as e:
            print(f"Ошибка при проверке авторизации: {str(e)}")
            traceback.print_exc()
            await self.take_screenshot(page, "instagram_auth_error.png")
            return False
    
    async def process_account(self, cookie_file):
        """Обрабатывает один файл с куками - только проверка авторизации"""
        print(f"\n{'='*50}")
        print(f"Обработка файла: {cookie_file}")
        print(f"{'='*50}")
        
        self.prepare_screenshot_directory(cookie_file)
        
        # Загружаем куки
        cookies = self.cookies_loader.load_cookies(cookie_file)
        if not cookies:
            print(f"Не удалось загрузить куки из файла {cookie_file}")
            self.cookies_loader.mark_cookie_as_invalid(cookie_file)
            self.mark_screenshot_directory(cookie_file, False)
            return False
        
        print(f"Настройки прокси: {self.proxy['server']}")
        
        try:
            async with async_playwright() as p:
                browser = await p.firefox.launch(headless=False)
                
                context = await browser.new_context(
                    proxy=self.proxy,
                    locale=config.DEFAULT_LOCALE,
                    user_agent=config.DEFAULT_USER_AGENT
                )
                
                # Устанавливаем cookies
                await context.add_cookies(cookies)
                page = await context.new_page()
                
                # Проверяем авторизацию
                is_authenticated = await self.check_authentication(page)
                
                # Закрываем браузер
                await browser.close()
                
                # Помечаем файл
                if is_authenticated:
                    self.cookies_loader.mark_cookie_as_valid(cookie_file)
                    self.mark_screenshot_directory(cookie_file, True)
                    print("Результат: ВАЛИДНЫЙ")
                    return True
                else:
                    self.cookies_loader.mark_cookie_as_invalid(cookie_file)
                    self.mark_screenshot_directory(cookie_file, False)
                    print("Результат: НЕВАЛИДНЫЙ")
                    return False
        
        except Exception as e:
            error_text = str(e).lower()
            
            if any(err in error_text for err in ['ssl_error', 'ssl error', 'proxy', 'connection', 'timeout']):
                print(f"Ошибка соединения: {e}")
                print("Пропускаем - ошибка не связана с валидностью куки")
                self.mark_screenshot_directory(cookie_file, None)
                return False
            else:
                print(f"Ошибка при обработке: {str(e)}")
                traceback.print_exc()
                self.cookies_loader.mark_cookie_as_invalid(cookie_file)
                self.mark_screenshot_directory(cookie_file, False)
                return False
