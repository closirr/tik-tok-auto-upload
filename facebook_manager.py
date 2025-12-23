import asyncio
import os
import re
import traceback
import datetime
from playwright.async_api import async_playwright
import aiohttp
from facebook_cookies_loader import FacebookCookiesLoader
import config

class FacebookManager:
    def __init__(self, cookies_dir='facebook_cookies', screenshots_dir='facebook_screenshots'):
        self.cookies_dir = cookies_dir
        self.screenshots_dir = screenshots_dir
        self.cookies_loader = FacebookCookiesLoader(cookies_dir)
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
    
    def mark_screenshot_directory(self, cookie_file, status):
        """Переименовывает директорию скриншотов со статусом"""
        if not self.current_screenshot_dir or not os.path.exists(self.current_screenshot_dir):
            return
        
        base_dir = os.path.dirname(self.current_screenshot_dir)
        current_dir_name = os.path.basename(self.current_screenshot_dir)
        
        if status is None:
            status_str = "skipped"
        elif status == "password":
            status_str = "password"
        elif status is True:
            status_str = "valid"
        else:
            status_str = "invalid"
            
        new_dir_name = f"{status_str}_{current_dir_name}"
        new_dir_path = os.path.join(base_dir, new_dir_name)
        
        try:
            os.rename(self.current_screenshot_dir, new_dir_path)
            self.current_screenshot_dir = new_dir_path
            print(f"Директория скриншотов помечена как {status_str}")
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
    
    async def get_ip_info_via_aiohttp(self):
        """Получает информацию об IP через ipinfo.io API с использованием aiohttp"""
        try:
            url = "https://ipinfo.io/json"
            headers = {
                'Authorization': f'Bearer {config.IPINFO_TOKEN}'
            }
            
            proxy_url = None
            proxy_auth = None
            if self.proxy and self.proxy.get('server'):
                proxy_url = self.proxy['server']
                if self.proxy.get('username') and self.proxy.get('password'):
                    proxy_auth = aiohttp.BasicAuth(
                        self.proxy['username'],
                        self.proxy['password']
                    )
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, 
                    headers=headers, 
                    proxy=proxy_url,
                    proxy_auth=proxy_auth,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        print(f"Ошибка ipinfo.io API: статус {response.status}")
                        return None
                        
        except Exception as e:
            print(f"Ошибка при запросе к ipinfo.io: {str(e)}")
            return None
    
    async def check_proxy_connection(self):
        """Проверяет работу прокси через ipinfo.io API"""
        try:
            print("Проверка работы прокси через ipinfo.io...")
            
            ip_info = await self.get_ip_info_via_aiohttp()
            
            if ip_info:
                ip = ip_info.get('ip')
                country = ip_info.get('country', 'Неизвестно')
                city = ip_info.get('city', 'Неизвестно')
                org = ip_info.get('org', 'Неизвестно')
                
                print(f"IP через прокси: {ip}")
                print(f"Страна: {country}, Город: {city}")
                print(f"Организация: {org}")
                
                if ip:
                    return True, ip_info
            
            print("Не удалось получить IP-адрес через прокси")
            return False, None
                
        except Exception as e:
            print(f"Ошибка при проверке прокси: {str(e)}")
            return False, None
    
    async def handle_cookie_consent(self, page):
        """Обрабатывает диалог согласия на cookie"""
        try:
            consent_selectors = [
                'button[data-cookiebanner="accept_button"]',
                'button:has-text("Allow all cookies")',
                'button:has-text("Allow essential and optional cookies")',
                'button:has-text("Accept All")',
                'button:has-text("Accept")',
                'button:has-text("Принять все")',
                'button:has-text("Разрешить все")',
                'button:has-text("Разрешить")',
                '[data-testid="cookie-policy-manage-dialog-accept-button"]',
                'button[title="Allow all cookies"]',
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
        """Проверяет, авторизован ли пользователь на Facebook
        Возвращает: 'valid', 'invalid', или 'password'
        """
        try:
            print("Проверка авторизации на Facebook...")
            
            # Переходим на главную страницу Facebook
            await page.goto("https://www.facebook.com/", wait_until='domcontentloaded', timeout=60000)
            
            print("Ожидание загрузки страницы...")
            await page.wait_for_timeout(5000)
            
            await self.take_screenshot(page, "facebook_main_page.png")
            
            # Обрабатываем cookie consent
            await self.handle_cookie_consent(page)
            await page.wait_for_timeout(2000)
            
            current_url = page.url
            page_content = await page.content()
            
            # Проверка на страницу checkpoint/подтверждения
            checkpoint_indicators = ['/checkpoint/', '/login/identify', 'checkpoint', 'confirm_identity']
            is_checkpoint = any(x in current_url for x in checkpoint_indicators)
            
            if is_checkpoint:
                print("Обнаружена страница проверки безопасности (checkpoint)")
                await self.take_screenshot(page, "facebook_checkpoint.png")
                return 'valid'
            
            # === ПРОВЕРКА НА СТРАНИЦУ С ЗАПРОСОМ ПАРОЛЯ ===
            # Признаки: есть фото/имя пользователя + поле только для пароля (без email)
            
            # Селекторы для страницы "Недавние входы" с запросом пароля
            password_page_selectors = [
                # Модальное окно с запросом пароля (второй скриншот)
                'div[role="dialog"] input[type="password"]',
                # Страница с недавними входами
                'div[data-testid="royal_login_form"]',
            ]
            
            # Проверяем наличие поля пароля БЕЗ поля email (признак страницы подтверждения)
            has_password_only = False
            password_field = await page.query_selector('input[type="password"], input[name="pass"]')
            email_field = await page.query_selector('input[name="email"]')
            
            if password_field:
                password_visible = await password_field.is_visible()
                email_visible = False
                if email_field:
                    email_visible = await email_field.is_visible()
                
                # Если есть видимое поле пароля, но нет видимого поля email
                if password_visible and not email_visible:
                    has_password_only = True
                    print("Обнаружено поле пароля без поля email")
            
            # Проверяем наличие аватара/фото пользователя на странице входа
            user_avatar_selectors = [
                'img[data-testid="royal_login_profile_pic"]',
                'div[data-testid="royal_login_form"] img',
                'div[role="dialog"] img[src*="profile"]',
                'img[alt][src*="scontent"]',  # Фото профиля Facebook
            ]
            
            has_user_avatar = False
            for selector in user_avatar_selectors:
                try:
                    avatar = await page.query_selector(selector)
                    if avatar:
                        is_visible = await avatar.is_visible()
                        if is_visible:
                            has_user_avatar = True
                            print(f"Найден аватар пользователя: {selector}")
                            break
                except:
                    continue
            
            # === СНАЧАЛА ПРОВЕРЯЕМ ПОЛНУЮ ФОРМУ ВХОДА (email + password) ===
            # Это означает что сессия НЕ распознана вообще = invalid
            has_full_login_form = False
            if email_field and password_field:
                email_visible = await email_field.is_visible()
                password_visible = await password_field.is_visible()
                if email_visible and password_visible:
                    print("Найдена полная форма входа (email + password) - сессия не распознана")
                    await self.take_screenshot(page, "facebook_not_authenticated.png")
                    return 'invalid'
            
            # Проверка через URL на страницу входа
            if '/login' in current_url or 'login.php' in current_url:
                # Проверяем, есть ли полная форма входа
                if email_field:
                    email_visible = await email_field.is_visible() if email_field else False
                    if email_visible:
                        print("Перенаправлены на страницу входа с полной формой")
                        await self.take_screenshot(page, "facebook_not_authenticated.png")
                        return 'invalid'
            
            # === ТЕПЕРЬ ПРОВЕРЯЕМ СТРАНИЦУ С ЗАПРОСОМ ТОЛЬКО ПАРОЛЯ ===
            # Если есть аватар + поле пароля без email = требуется пароль (сессия частично распознана)
            if has_user_avatar and has_password_only:
                print("Сессия распознана, но требуется ввод пароля")
                await self.take_screenshot(page, "facebook_password_required.png")
                return 'password'
            
            # Проверяем текст "Недавние входы" (без "Забыли пароль?" - он есть на всех страницах)
            recent_login_indicators = [
                'Недавние входы',
                'Recent logins',
            ]
            
            has_recent_login_text = any(text in page_content for text in recent_login_indicators)
            
            # Если есть текст "Недавние входы" + поле только пароля = требуется пароль
            if has_recent_login_text and has_password_only:
                print("Страница недавних входов - требуется пароль")
                await self.take_screenshot(page, "facebook_password_required.png")
                return 'password'
            
            # === ПРОВЕРКА ПОЛНОЙ АВТОРИЗАЦИИ ===
            
            # Селекторы признаков авторизации на Facebook
            auth_selectors = [
                'div[role="navigation"]',
                'a[href="/me/"]',
                'a[aria-label="Home"]',
                'a[aria-label="Главная"]',
                'div[aria-label="Your profile"]',
                'div[aria-label="Ваш профиль"]',
                'svg[aria-label="Your profile"]',
                'a[href*="/friends"]',
                'a[href="/marketplace/"]',
                'a[href="/watch/"]',
                'a[href="/groups/"]',
                'div[aria-label="Messenger"]',
                'div[aria-label="Notifications"]',
                'div[aria-label="Уведомления"]',
                'div[aria-label="Account"]',
                'div[aria-label="Аккаунт"]',
                'input[placeholder="Search Facebook"]',
                'input[placeholder="Поиск на Facebook"]',
                'div[data-pagelet="LeftRail"]',
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
            
            # Проверка через HTML контент
            auth_html_indicators = [
                '"USER_ID":"',
                '"actorID":"',
                '"viewerID":',
            ]
            
            for indicator in auth_html_indicators:
                if indicator in page_content:
                    print(f"Найден признак авторизации в HTML: {indicator}")
                    is_authenticated = True
                    break
            
            # Финальное решение
            if is_authenticated:
                print("Пользователь авторизован на Facebook")
                await self.take_screenshot(page, "facebook_authenticated.png")
                return 'valid'
            else:
                print("Пользователь НЕ авторизован на Facebook")
                await self.take_screenshot(page, "facebook_not_authenticated.png")
                return 'invalid'
                
        except Exception as e:
            print(f"Ошибка при проверке авторизации: {str(e)}")
            traceback.print_exc()
            await self.take_screenshot(page, "facebook_auth_error.png")
            return 'invalid'

    async def process_account(self, cookie_file):
        """Обрабатывает один файл с куками - только проверка авторизации"""
        print(f"\n{'='*50}")
        print(f"Обработка файла: {cookie_file}")
        print(f"{'='*50}")
        
        self.prepare_screenshot_directory(cookie_file)
        
        # Проверяем IP через прокси в начале
        print("\n--- Проверка IP в начале сессии ---")
        proxy_ok, ip_info = await self.check_proxy_connection()
        if proxy_ok and ip_info:
            # Сохраняем отчет о прокси
            report_path = os.path.join(self.current_screenshot_dir, "proxy_report.txt")
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write(f"IP: {ip_info.get('ip')}\n")
                f.write(f"Страна: {ip_info.get('country', 'Неизвестно')}\n")
                f.write(f"Город: {ip_info.get('city', 'Неизвестно')}\n")
                f.write(f"Организация: {ip_info.get('org', 'Неизвестно')}\n")
            print(f"Отчет о прокси сохранен: {report_path}")
        else:
            print("ВНИМАНИЕ: Не удалось проверить IP прокси")
        
        # Загружаем куки
        cookies = self.cookies_loader.load_cookies(cookie_file)
        if not cookies:
            print(f"Не удалось загрузить куки из файла {cookie_file}")
            self.cookies_loader.mark_cookie_as_invalid(cookie_file)
            self.mark_screenshot_directory(cookie_file, False)
            return 'invalid'
        
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
                auth_result = await self.check_authentication(page)
                
                # Закрываем браузер
                await browser.close()
                
                # Помечаем файл в зависимости от результата
                if auth_result == 'valid':
                    self.cookies_loader.mark_cookie_as_valid(cookie_file)
                    self.mark_screenshot_directory(cookie_file, True)
                    print("Результат: ВАЛИДНЫЙ")
                    return 'valid'
                elif auth_result == 'password':
                    self.cookies_loader.mark_cookie_as_password(cookie_file)
                    self.mark_screenshot_directory(cookie_file, "password")
                    print("Результат: ТРЕБУЕТСЯ ПАРОЛЬ")
                    return 'password'
                else:
                    self.cookies_loader.mark_cookie_as_invalid(cookie_file)
                    self.mark_screenshot_directory(cookie_file, False)
                    print("Результат: НЕВАЛИДНЫЙ")
                    return 'invalid'
        
        except Exception as e:
            error_text = str(e).lower()
            
            if any(err in error_text for err in ['ssl_error', 'ssl error', 'proxy', 'connection', 'timeout']):
                print(f"Ошибка соединения: {e}")
                print("Пропускаем - ошибка не связана с валидностью куки")
                self.mark_screenshot_directory(cookie_file, None)
                return 'skipped'
            else:
                print(f"Ошибка при обработке: {str(e)}")
                traceback.print_exc()
                self.cookies_loader.mark_cookie_as_invalid(cookie_file)
                self.mark_screenshot_directory(cookie_file, False)
                return 'invalid'
