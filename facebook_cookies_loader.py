import json
import re
import traceback
import os
import glob
import shutil

class FacebookCookiesLoader:
    def __init__(self, cookies_dir='facebook_cookies'):
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
                                
                                # Обработка expires
                                try:
                                    exp_val = int(expiry) if expiry and expiry.strip() else 0
                                    if exp_val > 0:
                                        cookie['expires'] = exp_val
                                    else:
                                        cookie['expires'] = -1
                                except:
                                    cookie['expires'] = -1
                                
                                cookies.append(cookie)
                        except Exception as e:
                            print(f"Ошибка при парсинге строки куки Netscape: {line}")
                    
                    if cookies:
                        print(f"Успешно загружены куки в формате Netscape: {len(cookies)} шт.")
                        return cookies
                
                # Стандартный формат с табуляцией
                lines = cookies_data.split('\n')
                
                cookie_patterns = [
                    r'([^\t]+)\t(FALSE|TRUE)\t([^\t]+)\t(FALSE|TRUE)\t(\d*)\t([^\t]+)\t(.*)',
                    r'([^\t]+)\t(FALSE|TRUE)\t([^\t]*)\t(FALSE|TRUE)\t(\d*)\t([^\t]+)\t(.*)',
                    r'\.([^\t]+)\t(FALSE|TRUE)\t([^\t]+)\t(FALSE|TRUE)\t(\d*)\t([^\t]+)\t(.*)',
                ]
                
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith('#') or line.startswith('–') or line.startswith('*') or line.startswith('='):
                        continue
                    
                    for pattern in cookie_patterns:
                        match = re.match(pattern, line)
                        if match:
                            domain, httpOnly, path, secure, expiry, name, value = match.groups()
                            
                            if not domain.startswith('.') and 'facebook' in domain:
                                domain = '.' + domain
                                
                            cookie = {
                                'domain': domain,
                                'path': path,
                                'secure': secure.lower() == 'true',
                                'httpOnly': httpOnly.lower() == 'true',
                                'name': name,
                                'value': value
                            }
                            
                            try:
                                exp_val = int(expiry) if expiry and expiry.strip() else 0
                                if exp_val > 0:
                                    cookie['expires'] = exp_val
                                else:
                                    cookie['expires'] = -1
                            except:
                                cookie['expires'] = -1
                            
                            cookies.append(cookie)
                            break
                
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
        """Получает список файлов с куками, которые еще не были обработаны"""
        all_files = glob.glob(os.path.join(self.cookies_dir, '*.*'))
        return [f for f in all_files if not os.path.basename(f).startswith(('valid_', 'invalid_', 'password_'))]

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

    def mark_cookie_as_password(self, cookie_file):
        """Помечает файл с куками как требующий ввода пароля"""
        basename = os.path.basename(cookie_file)
        dirname = os.path.dirname(cookie_file)
        new_name = os.path.join(dirname, f"password_{basename}")
        
        try:
            shutil.move(cookie_file, new_name)
            print(f"Файл {cookie_file} помечен как требующий пароль -> {new_name}")
            return new_name
        except Exception as e:
            print(f"Ошибка при переименовании файла {cookie_file}: {str(e)}")
            return None
