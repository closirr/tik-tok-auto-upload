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
from free_proxy_integration import get_proxy_manager, get_primary_proxy, refresh_proxy

# Файл для сохранения результатов загрузки
UPLOAD_RESULTS_FILE = "upload_results.json"

class TikTokManager:
    def __init__(self, cookies_dir=config.DEFAULT_COOKIES_DIR, videos_dir=config.DEFAULT_VIDEOS_DIR, screenshots_dir=config.DEFAULT_SCREENSHOTS_DIR):
        self.cookies_dir = cookies_dir
        self.videos_dir = videos_dir
        self.screenshots_dir = screenshots_dir
        self.cookies_loader = CookiesLoader(cookies_dir)
        self.current_screenshot_dir = None
        
        # Настройка прокси в зависимости от режима
        self.proxy_disabled = config.PROXY_DISABLED
        self.use_free_proxy = config.USE_FREE_PROXY
        
        if self.proxy_disabled:
            print("🚫 Прокси отключен")
            self.proxy = None
            self.proxy_manager = None
        elif self.use_free_proxy:
            print("🆓 Используются бесплатные прокси")
            self.proxy = None  # Будет устанавливаться динамически
            self.proxy_manager = get_proxy_manager()
        else:
            print("💰 Используются платные прокси")
            self.proxy = config.PROXY
            self.proxy_manager = None
            
        self.proxy_refresh_url = config.PROXY_REFRESH_URL
        self.use_proxy_rotation = config.USE_PROXY_ROTATION
        
        # Создаем директории, если они не существуют
        for directory in [videos_dir, cookies_dir, screenshots_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
    
    def save_upload_result(self, cookie_file, username, video_url):
        """
        Сохраняет результат успешной загрузки видео в JSON файл
        
        Args:
            cookie_file: Полное имя файла с куками
            username: Никнейм аккаунта TikTok
            video_url: Ссылка на опубликованное видео
        """
        try:
            # Загружаем существующие результаты
            results = []
            if os.path.exists(UPLOAD_RESULTS_FILE):
                with open(UPLOAD_RESULTS_FILE, 'r', encoding='utf-8') as f:
                    results = json.load(f)
            
            # Добавляем новый результат
            result = {
                "cookie_file": os.path.basename(cookie_file),
                "username": username,
                "video_url": video_url,
                "timestamp": datetime.datetime.now().isoformat()
            }
            results.append(result)
            
            # Сохраняем обратно в файл
            with open(UPLOAD_RESULTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            
            print(f"Результат загрузки сохранен в {UPLOAD_RESULTS_FILE}")
            return True
        except Exception as e:
            print(f"Ошибка при сохранении результата загрузки: {str(e)}")
            return False
    
    async def get_tiktok_username(self, page):
        """
        Получает никнейм пользователя TikTok со страницы.
        Оптимизировано - только парсинг HTML без дополнительных переходов.
        
        Args:
            page: Объект страницы Playwright
            
        Returns:
            str: Никнейм пользователя или None если не удалось получить
        """
        try:
            print("Получение никнейма пользователя...")
            
            page_content = await page.content()
            
            # Ищем uniqueId в JSON данных страницы
            unique_id_match = re.search(r'"uniqueId"\s*:\s*"([^"]+)"', page_content)
            if unique_id_match:
                username = unique_id_match.group(1)
                print(f"Найден никнейм (uniqueId): {username}")
                return username
            
            # Ищем nickname
            nickname_match = re.search(r'"nickname"\s*:\s*"([^"]+)"', page_content)
            if nickname_match:
                username = nickname_match.group(1)
                print(f"Найден никнейм (nickname): {username}")
                return username
            
            print("Не удалось получить никнейм пользователя")
            return None
            
        except Exception as e:
            print(f"Ошибка при получении никнейма: {str(e)}")
            return None
    
    def extract_username_from_video_url(self, video_url):
        """
        Извлекает username из URL видео.
        
        Args:
            video_url: URL вида https://www.tiktok.com/@username/video/123
            
        Returns:
            str: username или None
        """
        if not video_url:
            return None
        try:
            match = re.search(r'tiktok\.com/@([^/]+)/video/', video_url)
            if match:
                return match.group(1)
            return None
        except:
            return None
    
    async def get_published_video_url(self, page):
        """
        Получает ссылку на опубликованное видео со страницы контента.
        
        Args:
            page: Объект страницы Playwright
            
        Returns:
            str: URL видео или None если не удалось получить
        """
        try:
            print("Получение ссылки на опубликованное видео...")
            
            # Ждём возможного редиректа после публикации
            await page.wait_for_timeout(2000)
            
            current_url = page.url
            
            # Если мы уже на странице контента - ищем там
            if '/tiktokstudio/content' in current_url:
                await page.wait_for_timeout(3000)
                video_link = await page.query_selector('a[href*="/video/"]')
                if video_link:
                    href = await video_link.get_attribute('href')
                    if href:
                        if href.startswith('/'):
                            href = f"https://www.tiktok.com{href}"
                        print(f"Найдена ссылка на видео: {href}")
                        return href
            
            # Переходим на страницу контента (там список наших видео)
            try:
                print("Переход на страницу контента для получения ссылки на видео...")
                await page.goto("https://www.tiktok.com/tiktokstudio/content", wait_until='domcontentloaded', timeout=15000)
                await page.wait_for_timeout(5000)
                
                # Ищем первое видео в списке (последнее загруженное)
                video_link = await page.query_selector('a[href*="/video/"]')
                if video_link:
                    href = await video_link.get_attribute('href')
                    if href:
                        if href.startswith('/'):
                            href = f"https://www.tiktok.com{href}"
                        print(f"Найдена ссылка на видео на странице контента: {href}")
                        return href
            except Exception as e:
                print(f"Не удалось получить ссылку со страницы контента: {str(e)}")
            
            print("Не удалось получить ссылку на видео")
            return None
            
        except Exception as e:
            print(f"Ошибка при получении ссылки на видео: {str(e)}")
            return None
            
    def prepare_screenshot_directory(self, cookie_file):
        """
        Создает директорию для скриншотов текущей сессии работы с cookie-файлом
        Организует папки по датам для удобного поиска
        
        Args:
            cookie_file: Имя cookie-файла, для которого создается директория
        
        Returns:
            str: Путь к созданной директории для скриншотов
        """
        # Извлекаем имя файла без расширения
        cookie_name = os.path.basename(cookie_file).split('.')[0]
        
        # Получаем текущую дату и время
        now = datetime.datetime.now()
        date_folder = now.strftime("%Y-%m-%d")  # Папка по дате: 2025-12-23
        timestamp = now.strftime("%H%M%S")      # Время для уникальности: 143052
        
        # Создаем структуру: screenshots/2025-12-23/cookie_name_143052/
        screenshot_dir = os.path.join(self.screenshots_dir, date_folder, f"{cookie_name}_{timestamp}")
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
            bool: True, если загрузка запущена успешно
            str: "page_not_loaded" если страница не загрузилась (не помечать как invalid)
            False: если ошибка загрузки
        """
        try:
            # Проверяем IP перед загрузкой видео - УБРАНО ДЛЯ ОПТИМИЗАЦИИ
            # await self.check_whoer_ip(page, "перед_загрузкой_видео")

            
            # Проверяем и обрабатываем окно согласия на cookie, если оно появилось
            await self.handle_cookie_consent(page)
            
            # Обрабатываем информационные модальные окна с кнопкой "Понятно"
            await self.handle_info_modals(page)
            
            # Ждём загрузки страницы с retry
            file_input = None
            max_wait_attempts = 5
            
            for attempt in range(max_wait_attempts):
                file_input = await page.query_selector('input[type="file"]')
                if file_input:
                    break
                    
                print(f"⏳ Ожидание загрузки страницы... ({attempt + 1}/{max_wait_attempts})")
                await page.wait_for_timeout(3000)  # Ждём 3 секунды
                
                # Проверяем наличие лоадера (страница ещё грузится)
                loader = await page.query_selector('[class*="loading"], [class*="spinner"], [class*="loader"]')
                if loader:
                    print("   Страница ещё загружается...")
                    await page.wait_for_timeout(5000)  # Дополнительное ожидание
            
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
                
                # Проверяем IP сразу после выбора файла - УБРАНО ДЛЯ ОПТИМИЗАЦИИ
                # await self.check_whoer_ip(page, "после_выбора_файла")

                
                # Ждем достаточное время для завершения загрузки и обработки
                print("Ждем загрузку видео...")
                await page.wait_for_timeout(25000)  # 25 секунд для загрузки видео
                
                # Проверяем наличие дополнительных форм или шагов
                await self.handle_additional_forms(page)
                
                # Публикуем видео
                publication_result = await self.publish_video(page)
                
                # Если публикация не удалась но видео было выбрано — аккаунт валидный, проблема с сетью
                if publication_result == False:
                    return "publish_failed"  # Не помечать как invalid
                
                return publication_result
                
            else:
                print("❌ Не удалось найти поле для загрузки файла (страница не загрузилась)")
                await self.take_screenshot(page, "page_not_loaded.png")
                return "page_not_loaded"  # Специальное значение - не помечать как invalid
        
        except Exception as e:
            print(f"Ошибка при загрузке видео: {str(e)}")
            await self.take_screenshot(page, "tiktok_upload_error.png")
            return False
            
    async def publish_video(self, page):
        """Публикует загруженное видео, нажимая на кнопку 'Опубликовать'"""
        try:
            # Закрываем модалки которые могут мешать (например "Добавлены новые функции редактирования")
            await self.close_blocking_modals(page)
            
            # Ждём появления кнопки "Опубликовать" с retry
            print("Ищем кнопку 'Опубликовать'...")
            publish_button = None
            
            for attempt in range(10):  # 10 попыток по 2 секунды = 20 секунд макс
                publish_button = await page.query_selector('[data-e2e="post_video_button"]')
                if publish_button:
                    break
                
                # Пробуем альтернативный селектор
                publish_button = await page.query_selector('button:has-text("Опубликовать")')
                if publish_button:
                    break
                    
                print(f"⏳ Ожидание кнопки 'Опубликовать'... ({attempt + 1}/10)")
                await self.close_blocking_modals(page)  # Закрываем модалки на каждой итерации
                await page.wait_for_timeout(2000)
            
            if publish_button:
                print("Нажимаем на кнопку 'Опубликовать'")
                await publish_button.click()
                print("Видео отправлено на публикацию")
                await page.wait_for_timeout(3000)  # Ждем появления модалки
                
                # Проверяем модальное окно "Продолжить публикацию?"
                await self.handle_continue_publish_modal(page)
                
                await page.wait_for_timeout(2000)  # Дополнительное ожидание
                await self.take_screenshot(page, "tiktok_published.png")
                
                # Проверяем IP сразу после нажатия кнопки публикации - УБРАНО ДЛЯ ОПТИМИЗАЦИИ
                # await self.check_whoer_ip(page, "сразу_после_нажатия_кнопки")

                
                # Проверяем успешность публикации
                success = await self.check_publication_success(page)
                if success:
                    print("Видео успешно опубликовано")
                    
                    # Проверяем IP после успешной публикации - УБРАНО ДЛЯ ОПТИМИЗАЦИИ
                    # await self.check_whoer_ip(page, "после_успешной_публикации")

                    return True
                else:
                    print("Не удалось подтвердить успешность публикации")
                    
                    # Проверяем IP после неуспешной публикации - УБРАНО ДЛЯ ОПТИМИЗАЦИИ
                    # await self.check_whoer_ip(page, "после_неуспешной_публикации")

                    return False
            else:
                print("Кнопка 'Опубликовать' не найдена")
                # Попробуем найти другие элементы с похожим текстом
                button = await page.query_selector('button:has-text("Опубликовать")')
                if button:
                    print("Найдена кнопка с текстом 'Опубликовать', нажимаем")
                    
                    # Проверяем IP перед нажатием альтернативной кнопки - УБРАНО ДЛЯ ОПТИМИЗАЦИИ
                    # await self.check_whoer_ip(page, "перед_нажатием_альтернативной_кнопки")

                    
                    await button.click()
                    print("Видео отправлено на публикацию")
                    await page.wait_for_timeout(3000)
                    
                    # Проверяем модальное окно "Продолжить публикацию?"
                    await self.handle_continue_publish_modal(page)
                    
                    await page.wait_for_timeout(2000)
                    await self.take_screenshot(page, "tiktok_published.png")
                    
                    # Проверяем IP после нажатия альтернативной кнопки - УБРАНО ДЛЯ ОПТИМИЗАЦИИ
                    # await self.check_whoer_ip(page, "после_нажатия_альтернативной_кнопки")

                    
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
    
    async def handle_continue_publish_modal(self, page):
        """Обрабатывает модальное окно 'Продолжить публикацию?' которое появляется когда проверка авторских прав не завершена"""
        try:
            print("Проверяем наличие модального окна 'Продолжить публикацию?'...")
            
            # Ищем модальное окно по тексту заголовка
            modal_selectors = [
                'div:has-text("Продолжить публикацию?")',
                '[class*="modal"]:has-text("Продолжить публикацию")',
                '[role="dialog"]:has-text("Продолжить публикацию")',
            ]
            
            modal_found = False
            for selector in modal_selectors:
                try:
                    modal = await page.query_selector(selector)
                    if modal:
                        modal_found = True
                        break
                except:
                    continue
            
            if modal_found:
                print("Найдено модальное окно 'Продолжить публикацию?'")
                await self.take_screenshot(page, "continue_publish_modal.png")
                
                # Ищем кнопку "Опубликовать" в модальном окне
                # Кнопка красная/розовая с текстом "Опубликовать"
                publish_button_selectors = [
                    'button:has-text("Опубликовать"):not([data-e2e="post_video_button"])',
                    '[role="dialog"] button:has-text("Опубликовать")',
                    '[class*="modal"] button:has-text("Опубликовать")',
                    'button[class*="primary"]:has-text("Опубликовать")',
                    'button[class*="confirm"]:has-text("Опубликовать")',
                ]
                
                for selector in publish_button_selectors:
                    try:
                        button = await page.query_selector(selector)
                        if button:
                            # Проверяем что кнопка видима
                            is_visible = await button.is_visible()
                            if is_visible:
                                print(f"Найдена кнопка 'Опубликовать' в модальном окне, нажимаем...")
                                await button.click(force=True)
                                print("Кнопка 'Опубликовать' в модальном окне нажата")
                                await page.wait_for_timeout(2000)
                                return True
                    except Exception as e:
                        continue
                
                # Альтернативный поиск - все кнопки с текстом "Опубликовать"
                try:
                    buttons = await page.query_selector_all('button:has-text("Опубликовать")')
                    for button in buttons:
                        try:
                            is_visible = await button.is_visible()
                            if is_visible:
                                # Проверяем что это не основная кнопка публикации
                                data_e2e = await button.get_attribute('data-e2e')
                                if data_e2e != 'post_video_button':
                                    print("Найдена альтернативная кнопка 'Опубликовать', нажимаем...")
                                    await button.click(force=True)
                                    print("Альтернативная кнопка нажата")
                                    await page.wait_for_timeout(2000)
                                    return True
                        except:
                            continue
                except:
                    pass
                
                print("Не удалось найти кнопку 'Опубликовать' в модальном окне")
                return False
            else:
                print("Модальное окно 'Продолжить публикацию?' не найдено")
                return True  # Возвращаем True так как модалка не появилась - это нормально
                
        except Exception as e:
            print(f"Ошибка при обработке модального окна 'Продолжить публикацию?': {str(e)}")
            return False
    
    async def handle_additional_forms(self, page):
        """Обрабатывает дополнительные формы или шаги при загрузке видео"""
        try:
            # Проверяем IP перед обработкой дополнительных форм - УБРАНО ДЛЯ ОПТИМИЗАЦИИ
            # await self.check_whoer_ip(page, "перед_обработкой_форм")

            
            # Ждем некоторое время для появления форм
            await page.wait_for_timeout(3000)
            
            # Обрабатываем информационные модальные окна с кнопкой "Понятно"
            await self.handle_info_modals(page)
            
            # Проверяем наличие полей для заполнения описания
            description_field = await page.query_selector('textarea[placeholder*="описание"], textarea[placeholder*="description"], [data-e2e="upload-desc"]')
            if description_field:
                print("Заполняем поле описания")
                await description_field.fill("Цікаве відео вео3 банана про #viral #trending")
                await page.wait_for_timeout(1000)
            
            # Проверяем IP после заполнения описания - УБРАНО ДЛЯ ОПТИМИЗАЦИИ
            # await self.check_whoer_ip(page, "после_заполнения_описания")

            
            # Проверяем наличие других полей и кнопок
            # Например, кнопки "Далее" или "Продолжить"
            next_button = await page.query_selector('button:has-text("Далее"), button:has-text("Next"), button:has-text("Continue"), button:has-text("Продолжить")')
            if next_button:
                print("Нажимаем кнопку 'Далее'")
                await next_button.click()
                await page.wait_for_timeout(3000)
                await self.take_screenshot(page, "tiktok_next_step.png")
                
                # Проверяем IP после нажатия кнопки "Далее" - УБРАНО ДЛЯ ОПТИМИЗАЦИИ
                # await self.check_whoer_ip(page, "после_нажатия_далее")

            
            # Делаем скриншот после обработки всех форм
            await self.take_screenshot(page, "tiktok_forms_handled.png")
            
            # Финальная проверка IP после обработки всех форм - УБРАНО ДЛЯ ОПТИМИЗАЦИИ
            # await self.check_whoer_ip(page, "после_обработки_всех_форм")

            
        except Exception as e:
            print(f"Ошибка при обработке дополнительных форм: {str(e)}")
            await self.take_screenshot(page, "tiktok_forms_error.png")
            
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
            if self.use_free_proxy:
                print("🔄 Обновление бесплатного прокси...")
                new_proxy = await refresh_proxy()
                if new_proxy:
                    self.proxy = new_proxy
                    print(f"✅ Бесплатный прокси обновлен: {new_proxy['server']}")
                    return True
                else:
                    print("❌ Не удалось получить новый бесплатный прокси")
                    return False
            else:
                print("🔄 Обновление платного прокси...")
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.proxy_refresh_url) as response:
                        if response.status == 200:
                            response_data = await response.json()
                            if response_data.get("success"):
                                session_id = response_data.get("session")
                                login = response_data.get("login")
                                print(f"✅ IP платного прокси успешно обновлен. Сессия: {session_id}")
                                
                                # Обновляем логин прокси с новой сессией
                                if session_id and login:
                                    self.proxy['username'] = login
                                    print(f"Обновлен логин прокси: {login}")
                                
                                return True
                            else:
                                print("❌ Ошибка при обновлении IP: сервер вернул успех=false")
                                return False
                        else:
                            print(f"❌ Ошибка при обновлении IP прокси. Код ответа: {response.status}")
                            return False
        except Exception as e:
            print(f"❌ Ошибка при обновлении IP прокси: {str(e)}")
            return False
    
    async def check_proxy_connection(self, page):
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
                    return True, [ip]
            
            print("Не удалось получить IP-адрес через прокси")
            return False, []
                
        except Exception as e:
            if "PROXY_PAYMENT_REQUIRED" in str(e):
                # Пробрасываем критическую ошибку выше
                raise
            print(f"Ошибка при проверке прокси: {str(e)}")
            return False, []
    
    async def get_ip_info_via_aiohttp(self, ip=None):
        """Получает информацию об IP через ipinfo.io API с использованием aiohttp"""
        try:
            url = f"https://ipinfo.io/{ip}/json" if ip else "https://ipinfo.io/json"
            headers = {
                'Authorization': f'Bearer {config.IPINFO_TOKEN}'
            }
            
            # Настраиваем прокси для aiohttp
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
                    elif response.status == 402:
                        # Критическая ошибка - проблема с оплатой прокси
                        raise Exception("PROXY_PAYMENT_REQUIRED")
                    else:
                        print(f"Ошибка ipinfo.io API: статус {response.status}")
                        return None
                        
        except aiohttp.ClientResponseError as e:
            if e.status == 402:
                raise Exception("PROXY_PAYMENT_REQUIRED")
            print(f"Ошибка при запросе к ipinfo.io: {e.status}, {e.message}")
            return None
        except Exception as e:
            error_msg = str(e)
            if "PROXY_PAYMENT_REQUIRED" in error_msg:
                raise
            print(f"Ошибка при запросе к ipinfo.io: {error_msg}")
            return None
    
    def extract_ip_from_content(self, content, service_name=None):
        """Извлекает IP-адрес из содержимого страницы"""
        try:
            import re
            ip_match = re.search(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', content)
            if ip_match:
                return ip_match.group(0)
            return None
        except Exception as e:
            print(f"Ошибка при извлечении IP: {str(e)}")
            return None
    
    def is_using_proxy(self, real_ip, proxy_ips):
        """Проверяет, используется ли прокси или реальный IP"""
        if not real_ip or not proxy_ips:
            return None  # Недостаточно данных для проверки
        
        # Проверяем, отличается ли хотя бы один IP от реального
        for proxy_ip in proxy_ips:
            if proxy_ip != real_ip and self.is_valid_ip(proxy_ip):
                return True  # Используется прокси
        
        return False  # Используется реальный IP
    
    def is_valid_ip(self, ip):
        """Проверяет, является ли строка валидным IP-адресом"""
        if not ip:
            return False
        
        import re
        # Простая проверка формата IP
        ip_pattern = r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$'
        return bool(re.match(ip_pattern, ip))
    
    async def check_real_ip(self):
        """Проверяет реальный IP пользователя без использования прокси через ipinfo.io"""
        try:
            print("Проверка реального IP пользователя через ipinfo.io...")
            
            url = "https://ipinfo.io/json"
            headers = {
                'Authorization': f'Bearer {config.IPINFO_TOKEN}'
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        real_ip = data.get('ip')
                        country = data.get('country', 'Неизвестно')
                        city = data.get('city', 'Неизвестно')
                        print(f"Реальный IP: {real_ip} ({country}, {city})")
                        return real_ip
                    else:
                        print(f"Ошибка ipinfo.io API: статус {response.status}")
                        return None
                
        except Exception as e:
            print(f"Ошибка при проверке реального IP: {str(e)}")
            return None
    
    def save_proxy_report(self, real_ip, proxy_ips_start, proxy_ips_end):
        """Сохраняет отчет о проверке прокси в файл"""
        if not self.current_screenshot_dir:
            print("Невозможно сохранить отчет о прокси: директория для скриншотов не создана")
            return False
            
        try:
            report_path = os.path.join(self.current_screenshot_dir, "proxy_report.txt")
            
            with open(report_path, "w", encoding="utf-8") as f:
                f.write("=== ОТЧЕТ О ПРОВЕРКЕ ПРОКСИ ===\n\n")
                
                # Информация о настройках прокси
                f.write("НАСТРОЙКИ ПРОКСИ:\n")
                f.write(f"- Сервер: {self.proxy['server']}\n")
                f.write(f"- Логин: {self.proxy['username']}\n")
                f.write(f"- Пароль: {'*' * len(self.proxy['password'])}\n")
                f.write(f"- Режим ротации: {'Включен' if self.use_proxy_rotation else 'Выключен'}\n\n")
                
                # Информация о реальном IP
                f.write("РЕАЛЬНЫЙ IP:\n")
                f.write(f"- {real_ip}\n\n")
                
                # Информация о прокси в начале сессии
                f.write("ПРОКСИ В НАЧАЛЕ СЕССИИ:\n")
                if proxy_ips_start:
                    for i, ip in enumerate(proxy_ips_start):
                        f.write(f"- IP {i+1}: {ip}\n")
                    
                    # Проверка использования прокси
                    is_proxy_used = self.is_using_proxy(real_ip, proxy_ips_start)
                    if is_proxy_used is True:
                        f.write("\nРезультат: Прокси работает корректно, используется IP прокси.\n")
                    elif is_proxy_used is False:
                        f.write("\nРезультат: ВНИМАНИЕ! Используется реальный IP вместо прокси!\n")
                    else:
                        f.write("\nРезультат: Не удалось определить, используется ли прокси или реальный IP.\n")
                else:
                    f.write("Не удалось получить IP через прокси\n")
                
                f.write("\n")
                
                # Информация о прокси в конце сессии
                f.write("ПРОКСИ В КОНЦЕ СЕССИИ:\n")
                if proxy_ips_end:
                    for i, ip in enumerate(proxy_ips_end):
                        f.write(f"- IP {i+1}: {ip}\n")
                    
                    # Проверка использования прокси
                    is_proxy_used = self.is_using_proxy(real_ip, proxy_ips_end)
                    if is_proxy_used is True:
                        f.write("\nРезультат: Прокси работает корректно, используется IP прокси.\n")
                    elif is_proxy_used is False:
                        f.write("\nРезультат: ВНИМАНИЕ! Используется реальный IP вместо прокси!\n")
                    else:
                        f.write("\nРезультат: Не удалось определить, используется ли прокси или реальный IP.\n")
                else:
                    f.write("Не удалось получить IP через прокси\n")
                
                # Итоговый результат
                f.write("\nИТОГОВЫЙ РЕЗУЛЬТАТ:\n")
                if proxy_ips_start and proxy_ips_end:
                    start_proxy_used = self.is_using_proxy(real_ip, proxy_ips_start)
                    end_proxy_used = self.is_using_proxy(real_ip, proxy_ips_end)
                    
                    if start_proxy_used is True and end_proxy_used is True:
                        f.write("Прокси работала корректно на протяжении всей сессии.\n")
                    elif start_proxy_used is True and end_proxy_used is False:
                        f.write("ВНИМАНИЕ! Прокси работала в начале сессии, но перестала работать к концу!\n")
                    elif start_proxy_used is False and end_proxy_used is True:
                        f.write("Прокси не работала в начале сессии, но заработала к концу.\n")
                    elif start_proxy_used is False and end_proxy_used is False:
                        f.write("ВНИМАНИЕ! Прокси не работала на протяжении всей сессии!\n")
                    else:
                        f.write("Не удалось определить стабильность работы прокси.\n")
                else:
                    f.write("Недостаточно данных для оценки работы прокси.\n")
            
            print(f"Отчет о проверке прокси сохранен: {report_path}")
            return True
            
        except Exception as e:
            print(f"Ошибка при сохранении отчета о прокси: {str(e)}")
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
        
        # Получаем рабочий прокси для текущей сессии (с глобальными лимитами)
        if self.use_free_proxy:
            if not self.proxy:
                print("🔍 Получение бесплатного прокси для сессии...")
                max_proxy_attempts = 3  # Уменьшаем, так как теперь есть глобальные лимиты
                proxy_attempt = 0
                
                while proxy_attempt < max_proxy_attempts:
                    proxy_attempt += 1
                    print(f"🔄 Попытка {proxy_attempt}/{max_proxy_attempts} получения прокси...")
                    
                    self.proxy = await get_primary_proxy()
                    if self.proxy:
                        print(f"✅ Получен прокси: {self.proxy['server']}")
                        break
                    else:
                        print(f"❌ Не удалось получить прокси на попытке {proxy_attempt}")
                        
                        # Проверяем, не заблокирован ли поиск прокси глобально
                        from free_proxy_integration import get_proxy_manager
                        manager = get_proxy_manager()
                        if manager.is_proxy_search_blocked():
                            stats = manager.get_failure_stats()
                            print(f"🛑 Поиск прокси заблокирован глобально:")
                            print(f"   Всего неудач: {stats['total_failed']}/{stats['max_total']}")
                            print(f"   Подряд неудач: {stats['consecutive_failed']}/{stats['max_consecutive']}")
                            print("⏹️  Остановка обработки - все источники прокси недоступны")
                            self.mark_screenshot_directory(cookie_file, None)
                            return False
                    
                    # Небольшая пауза между попытками
                    if proxy_attempt < max_proxy_attempts:
                        await asyncio.sleep(1)
                
                if not self.proxy:
                    print("❌ Не удалось получить рабочий бесплатный прокси после всех попыток")
                    print("⚠️  Пропускаем этот аккаунт - проблема с прокси, а не с куками")
                    self.mark_screenshot_directory(cookie_file, None)  # Помечаем как пропущенный
                    return False
        
        # Выводим текущие настройки прокси для отладки
        if self.proxy_disabled:
            print("🚫 Работа без прокси (прокси отключен)")
        elif self.proxy:
            print("Текущие настройки прокси:")
            print(f"- Тип: {'Бесплатный' if self.use_free_proxy else 'Платный'}")
            print(f"- Сервер: {self.proxy['server']}")
            if self.proxy.get('username'):
                print(f"- Логин: {self.proxy['username']}")
                print(f"- Пароль: {'*' * len(self.proxy['password']) if self.proxy.get('password') else 'Нет'}")
            else:
                print("- Авторизация: Не требуется")
            print(f"- Режим ротации: {'Включен' if self.use_proxy_rotation else 'Выключен'}")
        else:
            print("❌ Прокси не настроен!")
            return False
        
        try:
            async with async_playwright() as p:
                browser = await p.firefox.launch(headless=False)
                
                # Создаем контекст (с прокси или без)
                if self.proxy_disabled or not self.proxy:
                    # Без прокси
                    context = await browser.new_context(
                        locale=config.DEFAULT_LOCALE,
                        user_agent=config.DEFAULT_USER_AGENT
                    )
                else:
                    # С прокси
                    print("Применяем настройки прокси:")
                    print(f"- Сервер: {self.proxy['server']}")
                    if self.proxy.get('username'):
                        print(f"- Логин: {self.proxy['username']}")
                        print(f"- Пароль: {'*' * len(self.proxy['password']) if self.proxy.get('password') else 'Нет'}")
                    else:
                        print("- Авторизация: Не требуется")
                    
                    # Создаем контекст с прокси (убираем None значения для бесплатных прокси)
                    proxy_config = {k: v for k, v in self.proxy.items() if v is not None}
                    
                    context = await browser.new_context(
                        proxy=proxy_config,
                        locale=config.DEFAULT_LOCALE,
                        user_agent=config.DEFAULT_USER_AGENT
                    )
                
                # Установить cookies
                await context.add_cookies(cookies)
                page = await context.new_page()
                
                # Проверяем работу прокси в начале сессии (только если прокси включен)
                if not self.proxy_disabled and self.proxy:
                    print("Проверка работы прокси в начале сессии...")
                    proxy_works = False
                    
                    while not proxy_works:
                        try:
                            proxy_works, proxy_ips = await self.check_proxy_connection(page)
                            if proxy_works:
                                print("✅ Прокси работает корректно")
                                break
                        except Exception as e:
                            print("⚠️  Прокси не работает корректно")
                            
                            if self.use_free_proxy:
                                # Удаляем нерабочий прокси из кэша
                                from free_proxy_integration import get_proxy_manager
                                manager = get_proxy_manager()
                                if self.proxy:
                                    manager.remove_proxy_from_cache(self.proxy['server'])
                                
                                print("🔄 Получаем новый бесплатный прокси...")
                                
                                # Закрываем текущий браузер
                                await browser.close()
                                
                                # Получаем новый прокси (будет крутиться пока не получит рабочий)
                                self.proxy = await get_primary_proxy()
                                if not self.proxy:
                                    # Если глобально заблокирован поиск прокси - выходим без маркировки
                                    if manager.is_proxy_search_blocked():
                                        print("🛑 Поиск прокси заблокирован глобально")
                                        print("⏭️  Пропускаем - проблема с прокси, не с куками")
                                        self.mark_screenshot_directory(cookie_file, None)
                                        return False
                                    
                                    # Ждём и пробуем снова
                                    print("⏳ Ждём 5 секунд и пробуем снова...")
                                    await asyncio.sleep(5)
                                    self.proxy = await get_primary_proxy()
                                    if not self.proxy:
                                        print("❌ Не удалось получить прокси, пропускаем")
                                        self.mark_screenshot_directory(cookie_file, None)
                                        return False
                                
                                print(f"✅ Получен новый прокси: {self.proxy['server']}")
                                
                                # Создаем новый браузер с новым прокси
                                browser = await p.firefox.launch(headless=False)
                                proxy_config = {k: v for k, v in self.proxy.items() if v is not None}
                                context = await browser.new_context(
                                    proxy=proxy_config,
                                    locale=config.DEFAULT_LOCALE,
                                    user_agent=config.DEFAULT_USER_AGENT
                                )
                                await context.add_cookies(cookies)
                                page = await context.new_page()
                                # Продолжаем цикл с новым прокси
                            else:
                                # Платный прокси - пробуем обновить IP
                                print("🔄 Пробуем обновить IP платного прокси...")
                                await self.refresh_proxy_ip()
                                await asyncio.sleep(2)
                                # Продолжаем цикл
                
                # Проверяем авторизацию (уже переходит на страницу загрузки)
                is_authenticated = await self.check_authentication(page)
                
                if is_authenticated == "timeout":
                    # Таймаут загрузки страницы - проблема с прокси/сетью, не с куками
                    print("⚠️  Таймаут при загрузке - пропускаем без пометки invalid")
                    
                    # Удаляем прокси из кэша — он не работает для TikTok
                    if self.use_free_proxy and self.proxy:
                        from free_proxy_integration import get_proxy_manager
                        proxy_manager = get_proxy_manager()
                        proxy_server = self.proxy.get('server', '')
                        proxy_manager.remove_proxy_from_cache(proxy_server)
                        print(f"🗑️ Прокси {proxy_server} удалён из кэша из-за таймаута")
                    
                    self.mark_screenshot_directory(cookie_file, None)  # skipped
                    return False
                
                if is_authenticated == True:
                    # Мы уже на странице загрузки после check_authentication
                    # Не нужен дополнительный переход - экономим трафик
                    
                    # Делаем скриншот страницы загрузки
                    await self.take_screenshot(page, "tiktok_upload_page.png")
                    
                    # Загружаем видео
                    upload_success = await self.upload_video(page, video_path)
                    
                    if upload_success == True:
                        print("Загрузка и публикация видео выполнены")
                        
                        # Сначала получаем ссылку на видео (идёт на страницу контента)
                        video_url = await self.get_published_video_url(page)
                        
                        # Извлекаем username из URL видео (без доп. переходов)
                        username = self.extract_username_from_video_url(video_url)
                        if not username:
                            # Пробуем получить из HTML если не нашли в URL
                            username = await self.get_tiktok_username(page)
                        
                        # Сохраняем результат загрузки в JSON
                        self.save_upload_result(cookie_file, username, video_url)
                        
                        self.cookies_loader.mark_cookie_as_valid(cookie_file)
                        self.mark_screenshot_directory(cookie_file, True)
                        # Ждем некоторое время перед закрытием браузера
                        await page.wait_for_timeout(3000)  # 3 секунд
                        return True
                    elif upload_success == "page_not_loaded":
                        # Страница не загрузилась - проблема с прокси/сетью, не с куками
                        print("⚠️  Страница не загрузилась полностью - пропускаем без пометки invalid")
                        
                        # Удаляем прокси из кэша
                        if self.use_free_proxy and self.proxy:
                            from free_proxy_integration import get_proxy_manager
                            proxy_manager = get_proxy_manager()
                            proxy_server = self.proxy.get('server', '')
                            proxy_manager.remove_proxy_from_cache(proxy_server)
                            print(f"🗑️ Прокси {proxy_server} удалён из кэша")
                        
                        self.mark_screenshot_directory(cookie_file, None)  # skipped
                        return False
                    elif upload_success == "publish_failed":
                        # Видео выбрано, но публикация не удалась - аккаунт валидный, проблема с сетью
                        print("⚠️  Публикация не удалась, но аккаунт валидный - пропускаем без пометки invalid")
                        
                        # Удаляем прокси из кэша
                        if self.use_free_proxy and self.proxy:
                            from free_proxy_integration import get_proxy_manager
                            proxy_manager = get_proxy_manager()
                            proxy_server = self.proxy.get('server', '')
                            proxy_manager.remove_proxy_from_cache(proxy_server)
                            print(f"🗑️ Прокси {proxy_server} удалён из кэша")
                        
                        self.mark_screenshot_directory(cookie_file, None)  # skipped
                        return False
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
            
            # Проверяем, связана ли ошибка с SSL, прокси или сетью
            if any(err in error_text for err in [
                'ssl_error', 'ssl error', 'proxy', 'connection', 'timeout', 'connect',
                'ns_error_unknown_host', 'network error', 'dns', 'host not found',
                'connection refused', 'connection reset', 'connection aborted',
                'bad request', '400', '502', '503', '504', 'gateway', 'unreachable',
                'net::err', 'socket', 'econnrefused', 'etimedout', 'enetunreach'
            ]):
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
        """
        Проверяет, авторизован ли пользователь на TikTok.
        Оптимизировано для экономии трафика - сразу идём на страницу загрузки.
        
        Returns:
            True - авторизован
            False - не авторизован (куки невалидные)
            "timeout" - таймаут загрузки (проблема сети/прокси, не помечать как invalid)
        """
        try:
            print("Проверка авторизации (оптимизированная)...")
            
            # Сразу переходим на страницу загрузки TikTok Studio
            # Это экономит трафик - не грузим тяжёлую главную страницу с видео
            print("Переход на страницу загрузки TikTok Studio...")
            await page.goto("https://www.tiktok.com/tiktokstudio/upload", wait_until='domcontentloaded', timeout=60000)
            
            # Ждём загрузки и возможных редиректов
            await page.wait_for_timeout(5000)
            
            # Проверяем URL после загрузки
            current_url = page.url.lower()
            print(f"Текущий URL: {page.url}")
            
            # Если перекинуло на страницу логина - не авторизован
            if 'login' in current_url or 'signin' in current_url:
                print("Перенаправлены на страницу входа - пользователь не авторизован")
                await self.take_screenshot(page, "tiktok_not_authenticated.png")
                return False
            
            # Если остались на странице studio/upload - авторизован
            if 'studio' in current_url or 'upload' in current_url:
                print("Успешный доступ к TikTok Studio - пользователь авторизован")
                
                # Обрабатываем диалог согласия на cookie, если он появился
                await self.handle_cookie_consent(page)
                
                # Обрабатываем информационные модальные окна
                await self.handle_info_modals(page)
                
                # Делаем скриншот страницы загрузки
                await self.take_screenshot(page, "tiktok_studio_page.png")
                
                return True
            
            # Дополнительная проверка - ищем элементы формы загрузки
            file_input = await page.query_selector('input[type="file"]')
            if file_input:
                print("Найдена форма загрузки - пользователь авторизован")
                await self.handle_cookie_consent(page)
                await self.handle_info_modals(page)
                await self.take_screenshot(page, "tiktok_studio_page.png")
                return True
            
            # Проверяем наличие кнопки входа на странице
            login_selectors = [
                '[data-e2e="top-login-button"]',
                'button:has-text("Войти")',
                'button:has-text("Login")',
                'button:has-text("Log in")',
            ]
            
            for selector in login_selectors:
                try:
                    login_button = await page.query_selector(selector)
                    if login_button:
                        print(f"Найдена кнопка входа: {selector} - пользователь не авторизован")
                        await self.take_screenshot(page, "tiktok_not_authenticated.png")
                        return False
                except:
                    continue
            
            # Если дошли сюда и нет явных признаков - считаем авторизованным
            print("Нет признаков отсутствия авторизации - считаем авторизованным")
            await self.handle_cookie_consent(page)
            await self.handle_info_modals(page)
            await self.take_screenshot(page, "tiktok_studio_page.png")
            return True
                
        except Exception as e:
            error_text = str(e).lower()
            # Проверяем, это таймаут или другая сетевая ошибка
            if 'timeout' in error_text or 'exceeded' in error_text:
                print(f"⏱️ Таймаут при загрузке страницы: {str(e)}")
                await self.take_screenshot(page, "tiktok_timeout_error.png")
                return "timeout"  # Специальное значение - не помечать как invalid
            
            print(f"Ошибка при проверке авторизации: {str(e)}")
            await self.take_screenshot(page, "tiktok_auth_check_error.png")
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
    
    async def handle_content_check_modal(self, page):
        """Обрабатывает модальное окно 'Включить автоматическую проверку контента?' - нажимает Отмена"""
        try:
            print("Проверяем наличие окна 'Включить автоматическую проверку контента'...")
            
            # Ищем окно по заголовку
            modal_title = await page.query_selector('text="Включить автоматическую проверку контента?"')
            
            if modal_title:
                print("Найдено окно 'Включить автоматическую проверку контента'")
                await self.take_screenshot(page, "content_check_modal_found.png")
                
                # Ищем кнопку "Отмена" - несколько способов
                cancel_selectors = [
                    'button:has-text("Отмена")',
                    'div[role="button"]:has-text("Отмена")',
                    'span:has-text("Отмена")',
                    '.TUXButton:has-text("Отмена")',
                ]
                
                for selector in cancel_selectors:
                    cancel_button = await page.query_selector(selector)
                    if cancel_button:
                        print(f"Найдена кнопка 'Отмена', нажимаем...")
                        # Используем force=True чтобы обойти перехват overlay
                        await cancel_button.click(force=True)
                        await page.wait_for_timeout(1000)
                        print("Окно автоматической проверки контента закрыто")
                        await self.take_screenshot(page, "content_check_modal_closed.png")
                        return True
                
                # Если кнопка "Отмена" не найдена, пробуем закрыть крестиком
                close_button = await page.query_selector('[aria-label="Close"], [aria-label="Закрыть"], button svg, .modal-close')
                if close_button:
                    print("Кнопка 'Отмена' не найдена, закрываем крестиком...")
                    await close_button.click(force=True)
                    await page.wait_for_timeout(1000)
                    return True
                    
                print("Не удалось найти кнопку для закрытия окна")
                return False
            else:
                print("Окно 'Включить автоматическую проверку контента' не найдено")
                return False
                
        except Exception as e:
            print(f"Ошибка при обработке окна автоматической проверки контента: {str(e)}")
            return False

    async def handle_info_modals(self, page):
        """Обрабатывает информационные модальные окна с кнопкой 'Понятно'"""
        try:
            # Сначала проверяем окно автоматической проверки контента
            await self.handle_content_check_modal(page)
            
            print("Проверяем наличие информационных модальных окон...")
            
            modals_closed = 0
            max_attempts = 5  # Максимум попыток закрыть модальные окна
            
            for attempt in range(max_attempts):
                # Проверяем окно автоматической проверки контента на каждой итерации
                content_check_closed = await self.handle_content_check_modal(page)
                if content_check_closed:
                    modals_closed += 1
                    continue
                
                # Ищем кнопку "Понятно" в модальных окнах
                # Способ 1: По тексту кнопки
                ponyatno_button = await page.query_selector('button:has-text("Понятно"), div.Button__content:has-text("Понятно")')
                
                if ponyatno_button:
                    print(f"Найдена кнопка 'Понятно' (попытка {attempt + 1})")
                    await ponyatno_button.click()
                    modals_closed += 1
                    await page.wait_for_timeout(1000)
                    continue
                
                # Способ 2: Ищем по классам TikTok (Button__content с текстом "Понятно")
                button_content = await page.query_selector('.Button__content')
                if button_content:
                    button_text = await button_content.inner_text()
                    if "Понятно" in button_text:
                        print(f"Найдена кнопка 'Понятно' по классу (попытка {attempt + 1})")
                        # Кликаем на родительский элемент кнопки
                        parent_button = await button_content.evaluate_handle('el => el.closest("button") || el.parentElement')
                        if parent_button:
                            await parent_button.click()
                        else:
                            await button_content.click()
                        modals_closed += 1
                        await page.wait_for_timeout(1000)
                        continue
                
                # Способ 3: Ищем кнопки "Включить" или "Отмена" в других диалогах
                cancel_button = await page.query_selector('button:has-text("Отмена")')
                
                if cancel_button:
                    # Нажимаем "Отмена" чтобы не включать лишние функции
                    print(f"Найдена кнопка 'Отмена' в диалоге (попытка {attempt + 1})")
                    await cancel_button.click()
                    modals_closed += 1
                    await page.wait_for_timeout(1000)
                    continue
                
                # Способ 4: Ищем кнопку закрытия модального окна (крестик)
                close_button = await page.query_selector('[aria-label="Close"], [aria-label="Закрыть"], button.close, .modal-close, [data-e2e="modal-close"]')
                if close_button:
                    print(f"Найдена кнопка закрытия модального окна (попытка {attempt + 1})")
                    await close_button.click()
                    modals_closed += 1
                    await page.wait_for_timeout(1000)
                    continue
                
                # Если ничего не найдено, выходим из цикла
                break
            
            if modals_closed > 0:
                print(f"Закрыто информационных модальных окон: {modals_closed}")
                await self.take_screenshot(page, "after_info_modals.png")
            else:
                print("Информационные модальные окна не найдены")
            
            return modals_closed > 0
            
        except Exception as e:
            print(f"Ошибка при обработке информационных модальных окон: {str(e)}")
            return False
    
    async def close_blocking_modals(self, page):
        """
        Быстро закрывает модалки которые могут блокировать кнопку Опубликовать.
        Не ждёт если модалки нет — просто пытается закрыть и идёт дальше.
        """
        try:
            # Кликаем в пустое место чтобы сбить фокус с модалки (если она есть)
            # Координаты 600, 50 - верхняя часть страницы, подальше от кнопок
            await page.mouse.click(600, 50)
            await page.wait_for_timeout(300)
            
            # Пробуем закрыть модалку "Понятно" (Добавлены новые функции редактирования)
            ponyatno_selectors = [
                'button:has-text("Понятно")',
                'div:has-text("Понятно"):not(:has(*))',  # div без детей с текстом Понятно
                '[class*="Button"]:has-text("Понятно")',
            ]
            
            for selector in ponyatno_selectors:
                try:
                    button = await page.query_selector(selector)
                    if button:
                        print("🔘 Закрываем модалку 'Понятно'...")
                        await button.click()
                        await page.wait_for_timeout(500)
                        return True
                except:
                    pass
            
            # Пробуем нажать Escape чтобы закрыть любую модалку
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(300)
            
            return False
            
        except Exception as e:
            # Игнорируем ошибки — это не критично
            return False
    
    async def check_whoer_ip(self, page, stage_name=""):
        """Проверяет IP через ipinfo.io API на определенном этапе"""
        try:
            print(f"\n=== Проверка IP через ipinfo.io на этапе: {stage_name} ===")
            
            ip_info = await self.get_ip_info_via_aiohttp()
            
            if ip_info:
                ip = ip_info.get('ip')
                country = ip_info.get('country', 'Неизвестно')
                city = ip_info.get('city', 'Неизвестно')
                
                print(f"IP на этапе '{stage_name}': {ip} ({country}, {city})")
                return ip
            
            return None
            
        except Exception as e:
            print(f"Ошибка при проверке IP на этапе '{stage_name}': {str(e)}")
            return None 