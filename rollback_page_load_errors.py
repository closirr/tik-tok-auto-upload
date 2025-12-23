#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для отката файлов куков, которые были ошибочно помечены как invalid
из-за проблем с загрузкой страницы (не из-за невалидных куков)

Критерий: если в папке скриншотов есть tiktok_studio_page.png или tiktok_upload_page.png,
значит авторизация прошла успешно, но страница не загрузилась полностью.
"""

import os
from pathlib import Path
from datetime import datetime

def rollback_page_load_errors():
    """Откатывает файлы куков, где авторизация прошла но страница не загрузилась"""
    
    cookies_dir = Path("cookies")
    screenshots_base = Path("screenshots")
    
    if not cookies_dir.exists():
        print("Папка cookies не найдена!")
        return
    
    # Найти все файлы с префиксом invalid_
    invalid_files = list(cookies_dir.glob("invalid_extracted_*.txt"))
    
    if not invalid_files:
        print("Файлы с префиксом invalid_extracted_ не найдены")
        return
    
    print(f"Найдено {len(invalid_files)} invalid файлов для анализа")
    print("=" * 60)
    
    rollback_count = 0
    skip_count = 0
    
    for invalid_file in invalid_files:
        # Получить базовое имя без invalid_ и .txt
        base_name = invalid_file.stem.replace("invalid_", "")
        
        # Искать папку скриншотов в подпапках по датам
        screenshot_found = False
        auth_success = False
        page_loaded = False
        not_authenticated = False
        
        for date_dir in screenshots_base.iterdir():
            if not date_dir.is_dir():
                continue
                
            # Ищем папки скриншотов для этого файла
            for screenshot_dir in date_dir.iterdir():
                if not screenshot_dir.is_dir():
                    continue
                    
                # Проверяем соответствие имени (с или без invalid_)
                dir_base = screenshot_dir.name.replace("invalid_", "")
                if not dir_base.startswith(base_name):
                    continue
                
                screenshot_found = True
                
                # Проверяем наличие скриншотов авторизации
                studio_page = screenshot_dir / "tiktok_studio_page.png"
                upload_page = screenshot_dir / "tiktok_upload_page.png"
                not_auth_page = screenshot_dir / "tiktok_not_authenticated.png"
                
                if studio_page.exists() or upload_page.exists():
                    auth_success = True
                    
                    # Проверяем есть ли file_selected (значит страница загрузилась)
                    file_selected = screenshot_dir / "tiktok_file_selected.png"
                    if file_selected.exists():
                        page_loaded = True
                
                if not_auth_page.exists():
                    not_authenticated = True
                
                # Проверяем был ли таймаут (tiktok_timeout_error.png или tiktok_auth_check_error.png без not_authenticated)
                timeout_error = screenshot_dir / "tiktok_timeout_error.png"
                auth_check_error = screenshot_dir / "tiktok_auth_check_error.png"
                if timeout_error.exists() or (auth_check_error.exists() and not not_auth_page.exists()):
                    # Это таймаут - нужно откатить
                    auth_success = True  # Считаем что авторизация могла быть OK
                    page_loaded = False
        
        # Решаем что делать с файлом
        if not screenshot_found:
            print(f"⚠️  {invalid_file.name}: скриншоты не найдены, пропускаем")
            skip_count += 1
            continue
            
        if not_authenticated:
            print(f"❌ {invalid_file.name}: не авторизован (правильно invalid)")
            skip_count += 1
            continue
            
        if auth_success and not page_loaded:
            # Авторизация прошла, но страница не загрузилась - откатываем!
            original_name = invalid_file.name.replace("invalid_", "")
            original_path = cookies_dir / original_name
            
            try:
                invalid_file.rename(original_path)
                print(f"✅ ОТКАТ: {invalid_file.name}")
                print(f"   -> {original_name} (авторизация OK, страница не загрузилась)")
                rollback_count += 1
            except Exception as e:
                print(f"❌ Ошибка отката {invalid_file.name}: {e}")
        elif auth_success and page_loaded:
            print(f"❓ {invalid_file.name}: авторизация OK, страница загрузилась - проверить вручную")
            skip_count += 1
        else:
            print(f"⚠️  {invalid_file.name}: неизвестный статус, пропускаем")
            skip_count += 1
    
    print("=" * 60)
    print(f"\n📊 Результат:")
    print(f"   Откачено: {rollback_count}")
    print(f"   Пропущено: {skip_count}")
    
    # Показать статистику
    remaining_invalid = len(list(cookies_dir.glob("invalid_*.txt")))
    extracted_files = len(list(cookies_dir.glob("extracted_*.txt")))
    valid_files = len(list(cookies_dir.glob("valid_*.txt")))
    
    print(f"\n📁 Текущая статистика:")
    print(f"   extracted_: {extracted_files}")
    print(f"   valid_: {valid_files}")
    print(f"   invalid_: {remaining_invalid}")

if __name__ == "__main__":
    print("🔄 Откат куков с ошибкой загрузки страницы")
    print("=" * 60)
    rollback_page_load_errors()
