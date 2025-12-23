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
                
                # Сначала пробуем текстовый формат
                cookies = self._parse_text_format(cookies_data)
                if cookies:
                    return cookies
                
                # Если текстовый формат не сработал, пробуем JSON
                try:
                    cookies = json.loads(cookies_data)
                    if isinstance(cookies, list):
                        print(f"Успешно загружены куки в формате JSON: {len(cookies)} шт.")
                        return cookies
                except json.JSONDecodeError:
                    pass
                
                print(f"Неподдерживаемый формат файла куков: {cookie_file}")
                return None
        except Exception as e:
            print(f"Ошибка при чтении файла {cookie_file}: {str(e)}")
            traceback.print_exc()
            return None
    
    def _parse_text_format(self, cookies_data):
        """Парсит куки из текстового формата (Netscape и другие)"""
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
                        
                        # Playwright требует expires: -1 (сессионный) или положительное число
                        if expiry and expiry.isdigit() and int(expiry) > 0:
                            cookie['expires'] = int(expiry)
                        else:
                            cookie['expires'] = -1  # Сессионный кук
                        
                        cookies.append(cookie)
                except Exception as e:
                    print(f"Ошибка при парсинге строки куки Netscape: {line}")
                    print(f"Ошибка: {str(e)}")
            
            if cookies:
                print(f"Успешно загружены куки в формате Netscape: {len(cookies)} шт.")
                return cookies
        
        # Стандартный формат (domain TAB path TAB secure TAB expiry TAB name TAB value)
        lines = cookies_data.split('\n')
        
        # Регулярное выражение для парсинга строк куков
        cookie_patterns = [
            r'([^\t]+)\t(FALSE|TRUE)\t([^\t]+)\t(FALSE|TRUE)\t(\d*)\t([^\t]+)\t(.*)',
            r'([^\t]+)\t(FALSE|TRUE)\t([^\t]*)\t(FALSE|TRUE)\t(\d*)\t([^\t]+)\t(.*)',
            r'\.([^\t]+)\t(FALSE|TRUE)\t([^\t]+)\t(FALSE|TRUE)\t(\d*)\t([^\t]+)\t(.*)',
        ]
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('–') or line.startswith('*') or line.startswith('='):
                continue
            
            match_found = False
            for pattern in cookie_patterns:
                match = re.match(pattern, line)
                if match:
                    domain, httpOnly, path, secure, expiry, name, value = match.groups()
                    
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
                    
                    if expiry and expiry.isdigit() and int(expiry) > 0:
                        cookie['expires'] = int(expiry)
                    else:
                        cookie['expires'] = -1
                    
                    cookies.append(cookie)
                    match_found = True
                    break
            
            if not match_found:
                if ':' in line and not ('@' in line and len(line) < 40):
                    parts = line.split(':', 1)
                    name = parts[0].strip()
                    value = parts[1].strip()
                    
                elif "\t" in line and line.count("\t") >= 1:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        domain = parts[0].strip()
                        
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
                                    'value': value,
                                    'expires': -1
                                }
                                cookies.append(cookie)
                                print(f"Извлечен кук из упрощенной строки: {domain} {name}")
        
        if cookies:
            print(f"Успешно загружены куки в текстовом формате: {len(cookies)} шт.")
            return cookies
        
        return None

    def get_cookie_files(self):
        """Получает список файлов с куками, которые еще не были обработаны (не имеют префиксов valid_ или invalid_)"""
        all_files = glob.glob(os.path.join(self.cookies_dir, '*.*'))
        # Фильтруем файлы, которые еще не были обработаны
        return [f for f in all_files if not os.path.basename(f).startswith(('valid_', 'invalid_'))]

    def get_cookie_files_with_valid_priority(self):
        """
        Получает список файлов с куками с приоритетом valid_ файлов.
        Сначала возвращаются файлы с префиксом valid_, потом все остальные (кроме invalid_).
        """
        all_files = glob.glob(os.path.join(self.cookies_dir, '*.*'))
        
        # Разделяем файлы на категории
        valid_files = [f for f in all_files if os.path.basename(f).startswith('valid_')]
        unprocessed_files = [f for f in all_files if not os.path.basename(f).startswith(('valid_', 'invalid_'))]
        
        # Сначала valid_, потом необработанные
        result = valid_files + unprocessed_files
        
        print(f"Найдено файлов с куками: {len(valid_files)} valid, {len(unprocessed_files)} необработанных")
        return result

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