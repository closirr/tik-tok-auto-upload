import json
import re
import traceback
import os
import glob
import shutil

class CookiesLoader:
    def __init__(self, cookies_dir='cookies'):
        self.cookies_dir = cookies_dir
        
        # Создаем директорию, если она не существует
        if not os.path.exists(cookies_dir):
            os.makedirs(cookies_dir)
    
    def load_cookies(self, cookie_file):
        """Загрузка куков из файла."""
        print(f"Загрузка куков из файла: {cookie_file}")
        try:
            with open(cookie_file, 'r', encoding='utf-8', errors='ignore') as f:
                cookies_data = f.read().strip()
                
                # Пробуем загрузить как JSON
                try:
                    cookies = json.loads(cookies_data)
                    if isinstance(cookies, list):
                        print(f"Успешно загружены куки в формате JSON: {len(cookies)} шт.")
                        return cookies
                except json.JSONDecodeError:
                    print("Не удалось распарсить как JSON, пробуем текстовый формат...")
                
                # Если не JSON, пробуем парсить текстовый формат
                cookies = []
                
                # Проверяем на формат Netscape
                if "# Netscape HTTP Cookie File" in cookies_data or "# HTTP Cookie File" in cookies_data:
                    print("Обнаружен формат Netscape Cookie File")
                    lines = cookies_data.split('\n')
                    for line in lines:
                        line = line.strip()
                        if not line or line.startswith('#'):
                            continue
                        
                        try:
                            # Формат: domain flag path secure expiration name value
                            parts = line.split('\t')
                            if len(parts) >= 7:
                                domain, httpOnly, path, secure, expiry, name, value = parts[:7]
                                
                                cookie = {
                                    'domain': domain,
                                    'path': path,
                                    'secure': secure.lower() == 'true',
                                    'httpOnly': httpOnly.lower() == 'true',
                                    'name': name,
                                    'value': value
                                }
                                
                                if expiry and expiry.isdigit():
                                    cookie['expires'] = int(expiry)
                                
                                cookies.append(cookie)
                        except Exception as e:
                            print(f"Ошибка при парсинге строки куки Netscape: {line}")
                            print(f"Ошибка: {str(e)}")
                    
                    if cookies:
                        print(f"Успешно загружены куки в формате Netscape: {len(cookies)} шт.")
                        return cookies
                
                # Стандартный формат (domain TAB path TAB secure TAB expiry TAB name TAB value)
                # Или другие форматы с разделителями табуляцией
                lines = cookies_data.split('\n')
                
                # Регулярное выражение для парсинга строк куков, несколько вариантов
                cookie_patterns = [
                    r'([^\t]+)\t(FALSE|TRUE)\t([^\t]+)\t(FALSE|TRUE)\t(\d*)\t([^\t]+)\t(.*)', # Стандартный формат
                    r'([^\t]+)\t(FALSE|TRUE)\t([^\t]*)\t(FALSE|TRUE)\t(\d*)\t([^\t]+)\t(.*)', # Вариант с пустым path
                    r'\.([^\t]+)\t(FALSE|TRUE)\t([^\t]+)\t(FALSE|TRUE)\t(\d*)\t([^\t]+)\t(.*)', # Вариант с точкой перед доменом
                ]
                
                for line in lines:
                    line = line.strip()
                    # Пропускаем комментарии и пустые строки
                    if not line or line.startswith('#') or line.startswith('–') or line.startswith('*') or line.startswith('='):
                        continue
                    
                    # Пробуем разные шаблоны регулярных выражений
                    match_found = False
                    for pattern in cookie_patterns:
                        match = re.match(pattern, line)
                        if match:
                            domain, httpOnly, path, secure, expiry, name, value = match.groups()
                            
                            # Исправляем домен - добавляем точку в начале, если её нет
                            if not domain.startswith('.') and 'tiktok' in domain:
                                domain = '.' + domain
                                
                            cookie = {
                                'domain': domain,
                                'path': path,
                                'secure': secure.lower() == 'true',
                                'httpOnly': httpOnly.lower() == 'true',
                                'name': name,
                                'value': value
                            }
                            
                            if expiry and expiry.isdigit():
                                cookie['expires'] = int(expiry)
                            
                            cookies.append(cookie)
                            match_found = True
                            break
                    
                    # Если не удалось распарсить по стандартным паттернам, ищем домен и значение вручную
                    if not match_found:
                        # Проверяем, есть ли в строке формат ключ:значение
                        if ':' in line and not ('@' in line and len(line) < 40):  # Исключаем строки с email
                            parts = line.split(':', 1)
                            name = parts[0].strip()
                            value = parts[1].strip()
                            
                        # Проверяем, есть ли это строка с доменом в начале и вкладкой после него
                        elif "\t" in line and line.count("\t") >= 1:
                            parts = line.split('\t')
                            if len(parts) >= 2:
                                # Возможно, это домен и значение
                                domain = parts[0].strip()
                                
                                # Ищем имя и значение кука в оставшейся части
                                if "=" in parts[-1]:
                                    name_value = parts[-1].strip().split("=", 1)
                                    if len(name_value) == 2:
                                        name = name_value[0].strip()
                                        value = name_value[1].strip()
                                        
                                        cookie = {
                                            'domain': domain if domain.startswith('.') else '.' + domain,
                                            'path': '/',
                                            'secure': False,
                                            'httpOnly': False,
                                            'name': name,
                                            'value': value
                                        }
                                        cookies.append(cookie)
                                        print(f"Извлечен кук из упрощенной строки: {domain} {name}")
                
                if cookies:
                    print(f"Успешно загружены куки в текстовом формате: {len(cookies)} шт.")
                    return cookies
                
                print(f"Неподдерживаемый формат файла куков: {cookie_file}")
                return None
        except Exception as e:
            print(f"Ошибка при чтении файла {cookie_file}: {str(e)}")
            traceback.print_exc()
            return None

    def get_cookie_files(self):
        """Получает список файлов с куками, которые еще не были обработаны (не имеют префиксов valid_ или invalid_)"""
        all_files = glob.glob(os.path.join(self.cookies_dir, '*.*'))
        # Фильтруем файлы, которые еще не были обработаны
        return [f for f in all_files if not os.path.basename(f).startswith(('valid_', 'invalid_'))]

    def mark_cookie_as_valid(self, cookie_file):
        """Помечает файл с куками как валидный"""
        basename = os.path.basename(cookie_file)
        dirname = os.path.dirname(cookie_file)
        new_name = os.path.join(dirname, f"valid_{basename}")
        
        try:
            shutil.move(cookie_file, new_name)
            print(f"Файл {cookie_file} помечен как валидный -> {new_name}")
            return new_name
        except Exception as e:
            print(f"Ошибка при переименовании файла {cookie_file}: {str(e)}")
            return None

    def mark_cookie_as_invalid(self, cookie_file):
        """Помечает файл с куками как невалидный"""
        basename = os.path.basename(cookie_file)
        dirname = os.path.dirname(cookie_file)
        new_name = os.path.join(dirname, f"invalid_{basename}")
        
        try:
            shutil.move(cookie_file, new_name)
            print(f"Файл {cookie_file} помечен как невалидный -> {new_name}")
            return new_name
        except Exception as e:
            print(f"Ошибка при переименовании файла {cookie_file}: {str(e)}")
            return None