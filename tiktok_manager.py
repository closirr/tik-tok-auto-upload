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
import datetime
import config  # Импортируем файл конфигурации

class TikTokManager:
    def __init__(self, cookies_dir=config.DEFAULT_COOKIES_DIR, videos_dir=config.DEFAULT_VIDEOS_DIR, screenshots_dir=config.DEFAULT_SCREENSHOTS_DIR):
        self.cookies_dir = cookies_dir
        self.videos_dir = videos_dir
        self.screenshots_dir = screenshots_dir
        self.cookies_loader = CookiesLoader(cookies_dir)
        self.current_screenshot_dir = None
        self.proxy = config.PROXY  # Используем прокси из файла конфигурации
        self.proxy_refresh_url = config.PROXY_REFRESH_URL  # Используем URL для обновления IP из файла конфигурации
        
        # Создаем директории, если они не существуют
        for directory in [videos_dir, cookies_dir, screenshots_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
            
    def prepare_screenshot_directory(self, cookie_file):
        """
        Создает директорию для скриншотов текущей сессии работы с cookie-файлом
        
        Args:
            cookie_file: Имя cookie-файла, для которого создается директория
        
        Returns:
            str: Путь к созданной директории для скриншотов
        """
        # Извлекаем имя файла без расширения
        cookie_name = os.path.basename(cookie_file).split('.')[0]
        
        # Добавляем метку времени для уникальности
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Создаем директорию с именем cookie-файла
        screenshot_dir = os.path.join(self.screenshots_dir, f"{cookie_name}_{timestamp}")
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # Сохраняем путь для последующего использования
        self.current_screenshot_dir = screenshot_dir
        
        print(f"Создана директория для скриншотов: {screenshot_dir}")
        return screenshot_dir
    
    def mark_screenshot_directory(self, cookie_file, is_valid):
        """
        Переименовывает директорию скриншотов, добавляя статус валидности cookie
        
        Args:
            cookie_file: Имя cookie-файла
            is_valid: Флаг валидности cookie (True/False/None)
                      None означает, что проверка была пропущена из-за ошибки соединения
        """
        if not self.current_screenshot_dir or not os.path.exists(self.current_screenshot_dir):
            print("Директория для скриншотов не существует")
            return
        
        # Получаем базовое имя текущей директории
        base_dir = os.path.dirname(self.current_screenshot_dir)
        current_dir_name = os.path.basename(self.current_screenshot_dir)
        
        # Формируем новое имя со статусом в начале
        if is_valid is None:
            status = "skipped"  # Для случаев с ошибками SSL/прокси
        else:
            status = "valid" if is_valid else "invalid"
            
        new_dir_name = f"{status}_{current_dir_name}"
        new_dir_path = os.path.join(base_dir, new_dir_name)
        
        # Переименовываем директорию
        try:
            os.rename(self.current_screenshot_dir, new_dir_path)
            self.current_screenshot_dir = new_dir_path
            print(f"Директория скриншотов помечена как {status}: {new_dir_path}")
        except Exception as e:
            print(f"Ошибка при переименовании директории скриншотов: {str(e)}")
    
    async def take_screenshot(self, page, filename):
        """
        Делает скриншот страницы и сохраняет его в директорию текущей сессии
        
        Args:
            page: Объект страницы Playwright
            filename: Имя файла для скриншота
        
        Returns:
            str: Путь к сохраненному скриншоту или None в случае ошибки
        """
        if not self.current_screenshot_dir:
            print("ВНИМАНИЕ: Директория для скриншотов не создана, скриншот будет сохранен в корне")
            return await page.screenshot(path=filename)
        
        screenshot_path = os.path.join(self.current_screenshot_dir, filename)
        try:
            await page.screenshot(path=screenshot_path)
            print(f"Скриншот сохранен: {screenshot_path}")
            return screenshot_path
        except Exception as e:
            print(f"Ошибка при сохранении скриншота: {str(e)}")
            return None
            
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
            # Проверяем и обрабатываем окно согласия на cookie, если оно появилось
            await self.handle_cookie_consent(page)
            
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
                await self.take_screenshot(page, "tiktok_file_selected.png")
                
                # Ждем достаточное время для завершения загрузки и обработки
                print("Ждем загрузку видео...")
                await page.wait_for_timeout(3000)  # 8 секунд
                
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
            await self.take_screenshot(page, "tiktok_upload_error.png")
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
                await self.take_screenshot(page, "tiktok_published.png")
                
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
                    await self.take_screenshot(page, "tiktok_published.png")
                    
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
                    await self.take_screenshot(page, "tiktok_no_publish_button.png")
                    return False
        except Exception as e:
            print(f"Ошибка при публикации видео: {str(e)}")
            await self.take_screenshot(page, "tiktok_publish_error.png")
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
        
        # Создаем директорию для скриншотов текущей сессии
        self.prepare_screenshot_directory(cookie_file)
        
        # Загружаем куки из файла
        cookies = self.cookies_loader.load_cookies(cookie_file)
        if not cookies:
            print(f"Не удалось загрузить куки из файла {cookie_file}")
            self.cookies_loader.mark_cookie_as_invalid(cookie_file)
            self.mark_screenshot_directory(cookie_file, False)
            return False
        
        # Получаем путь к первому видео
        video_path = self.get_first_video()
        if not video_path:
            print("Не удалось найти видео для загрузки. Убедитесь, что в папке videos есть видео файлы.")
            self.mark_screenshot_directory(cookie_file, False)
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
                    locale=config.DEFAULT_LOCALE,  # Используем локаль из файла конфигурации
                    user_agent=config.DEFAULT_USER_AGENT  # Используем user agent из файла конфигурации
                )
                
                # Установить cookies
                await context.add_cookies(cookies)
                page = await context.new_page()
                
                try:
                    await page.goto("https://tiktok.com", wait_until='load')
                    await page.wait_for_timeout(5000)  # Ждем 5 секунд для загрузки страницы
                except Exception as nav_error:
                    error_text = str(nav_error).lower()
                    
                    # Проверяем, связана ли ошибка с SSL или прокси
                    if any(err in error_text for err in ['ssl_error', 'ssl error', 'proxy', 'connection', 'timeout', 'connect']):
                        print(f"Ошибка соединения (SSL/прокси): {nav_error}")
                        print("Пропускаем обработку - эта ошибка не связана с валидностью куки")
                        self.mark_screenshot_directory(cookie_file, None)  # Не помечаем ни валидным, ни невалидным
                        return False
                    else:
                        # Другие ошибки навигации могут быть связаны с куки
                        raise  # Перебросим ошибку для обработки в блоке catch ниже
                
                # Делаем скриншот главной страницы
                await self.take_screenshot(page, "tiktok_main_page.png")
                
                # Обрабатываем диалог согласия на cookie на главной странице
                await self.handle_cookie_consent(page)
                
                # Проверяем, авторизованы ли мы
                is_authenticated = await self.check_authentication(page)
                
                if is_authenticated:
                    # Переходим на страницу загрузки
                    try:
                        await page.goto("https://www.tiktok.com/tiktokstudio/upload", wait_until='load')
                        await page.wait_for_timeout(5000)  # Ждем 5 секунд для загрузки страницы
                    except Exception as upload_nav_error:
                        error_text = str(upload_nav_error).lower()
                        
                        # Проверяем, связана ли ошибка с SSL или прокси
                        if any(err in error_text for err in ['ssl_error', 'ssl error', 'proxy', 'connection', 'timeout', 'connect']):
                            print(f"Ошибка соединения при переходе на страницу загрузки: {upload_nav_error}")
                            print("Пропускаем обработку - эта ошибка не связана с валидностью куки")
                            self.mark_screenshot_directory(cookie_file, None)  # Не помечаем ни валидным, ни невалидным
                            return False
                        else:
                            # Другие ошибки навигации могут быть связаны с куки
                            raise  # Перебросим ошибку для обработки в блоке catch ниже
                    
                    # Обрабатываем диалог согласия на cookie на странице загрузки
                    await self.handle_cookie_consent(page)
                    
                    # Делаем скриншот страницы загрузки
                    await self.take_screenshot(page, "tiktok_upload_page.png")
                    
                    # Загружаем видео
                    upload_success = await self.upload_video(page, video_path)
                    
                    if upload_success:
                        print("Загрузка и публикация видео выполнены")
                        self.cookies_loader.mark_cookie_as_valid(cookie_file)
                        self.mark_screenshot_directory(cookie_file, True)
                        # Ждем некоторое время перед закрытием браузера
                        await page.wait_for_timeout(3000)  # 3 секунд
                        return True
                    else:
                        print("Не удалось загрузить или опубликовать видео")
                        self.cookies_loader.mark_cookie_as_invalid(cookie_file)
                        self.mark_screenshot_directory(cookie_file, False)
                        return False
                else:
                    print("Не удалось авторизоваться с данными куками")
                    self.cookies_loader.mark_cookie_as_invalid(cookie_file)
                    self.mark_screenshot_directory(cookie_file, False)
                    return False
        
        except Exception as e:
            error_text = str(e).lower()
            
            # Проверяем, связана ли ошибка с SSL или прокси
            if any(err in error_text for err in ['ssl_error', 'ssl error', 'proxy', 'connection', 'timeout', 'connect']):
                print(f"Ошибка соединения: {e}")
                traceback.print_exc()
                print("Пропускаем обработку - эта ошибка не связана с валидностью куки")
                self.mark_screenshot_directory(cookie_file, None)
                return False
            else:
                # Для других ошибок помечаем куки как невалидный
                print(f"Ошибка при обработке куков {cookie_file}: {str(e)}")
                traceback.print_exc()
                self.cookies_loader.mark_cookie_as_invalid(cookie_file)
                self.mark_screenshot_directory(cookie_file, False)
                return False
    
    async def check_authentication(self, page):
        """Проверяет, авторизован ли пользователь на странице TikTok"""
        try:
            # Делаем скриншот для проверки
            await self.take_screenshot(page, "tiktok_auth_check.png")
            
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
    
    async def handle_cookie_consent(self, page):
        """Обрабатывает диалоговое окно с согласием на использование cookie, если оно появилось"""
        try:
            print("Проверяем наличие диалога согласия на cookie...")
            
            # Перед поиском делаем скриншот текущего состояния
            await self.take_screenshot(page, "before_cookie_consent.png")
            
            # Пытаемся найти диалоговое окно с кнопками согласия на cookie
            # Способ 1: Ищем по классу обертки кнопок
            cookie_dialog = await page.query_selector('div.button-wrapper.special-button-wrapper')
            
            if cookie_dialog:
                print("Найдено окно согласия на cookie (по классу обертки)")
                
                # Пытаемся найти любую из кнопок согласия или отказа
                # Так как язык может отличаться, ищем все кнопки внутри специальной обертки
                consent_buttons = await cookie_dialog.query_selector_all('button')
                
                if consent_buttons and len(consent_buttons) > 0:
                    # Нажимаем на последнюю кнопку (обычно это кнопка согласия)
                    button_to_click = consent_buttons[-1]  # Берем последнюю кнопку (обычно это "Разрешить все")
                    
                    # Получаем текст кнопки для лога
                    button_text = await button_to_click.inner_text()
                    print(f"Нажимаем на кнопку с текстом: '{button_text}'")
                    
                    await button_to_click.click()
                    print("Кнопка в окне согласия на cookie нажата")
                    
                    # Даем время на обработку нажатия
                    await page.wait_for_timeout(2000)
                    await self.take_screenshot(page, "after_cookie_consent.png")
                    return True
            
            # Способ 2: Ищем кнопки по содержимому текста, связанного с cookie
            possible_buttons = await page.query_selector_all('button:has-text("cookie"), button:has-text("Cookie"), button:has-text("Accept"), button:has-text("Принять"), button:has-text("Allow"), button:has-text("Разрешить"), button:has-text("Agree"), button:has-text("Consent"), button:has-text("OK")')
            
            if possible_buttons and len(possible_buttons) > 0:
                print("Найдена кнопка согласия на cookie (по тексту)")
                button_to_click = possible_buttons[0]
                button_text = await button_to_click.inner_text()
                print(f"Нажимаем на кнопку с текстом: '{button_text}'")
                
                await button_to_click.click()
                print("Кнопка согласия на cookie нажата")
                
                await page.wait_for_timeout(2000)
                await self.take_screenshot(page, "after_cookie_consent.png")
                return True
                
            # Способ 3: Ищем элементы с data-атрибутами, которые часто используются в диалогах cookie
            cookie_elements = await page.query_selector_all('[data-cookiebanner], [data-testid*="cookie"], [id*="cookie"], [id*="consent"], [class*="consent"], [class*="cookie"]')
            
            if cookie_elements and len(cookie_elements) > 0:
                print("Найден элемент диалога cookie (по data-атрибутам)")
                
                # Ищем внутри этих элементов кнопки
                for element in cookie_elements:
                    buttons = await element.query_selector_all('button')
                    if buttons and len(buttons) > 0:
                        # Предпочтительно нажать на кнопку согласия (обычно это последняя кнопка)
                        button_to_click = buttons[-1]
                        button_text = await button_to_click.inner_text()
                        print(f"Нажимаем на кнопку с текстом: '{button_text}'")
                        
                        await button_to_click.click()
                        print("Кнопка в окне согласия на cookie нажата")
                        
                        await page.wait_for_timeout(2000)
                        await self.take_screenshot(page, "after_cookie_consent.png")
                        return True
            
            # Способ 4: Проверка конкретно для TikTok (если у них есть специфичный формат)
            tiktok_consent_button = await page.query_selector('[data-e2e*="cookie-banner"] button, [data-e2e*="accept"] button')
            
            if tiktok_consent_button:
                print("Найдена кнопка согласия на cookie (специфичная для TikTok)")
                button_text = await tiktok_consent_button.inner_text()
                print(f"Нажимаем на кнопку с текстом: '{button_text}'")
                
                await tiktok_consent_button.click()
                print("Кнопка согласия на cookie TikTok нажата")
                
                await page.wait_for_timeout(2000)
                await self.take_screenshot(page, "after_cookie_consent.png")
                return True
            
            print("Окно согласия на cookie не найдено или уже обработано")
            await self.take_screenshot(page, "after_cookie_consent.png")
            return False
            
        except Exception as e:
            print(f"Ошибка при обработке диалога согласия на cookie: {str(e)}")
            await self.take_screenshot(page, "cookie_consent_error.png")
            return False 