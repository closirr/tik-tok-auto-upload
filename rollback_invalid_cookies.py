#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для отката файлов куков, которые были ошибочно помечены как invalid
из-за проблем с прокси (ошибка 402 Payment Required)
"""

import os
import shutil
import glob
from pathlib import Path

def rollback_invalid_cookies():
    """Откатывает файлы куков, помеченные как invalid, обратно в extracted_"""
    
    cookies_dir = Path("cookies")
    screenshots_dir = Path("screenshots")
    
    if not cookies_dir.exists():
        print("Папка cookies не найдена!")
        return
    
    # Найти все файлы с префиксом invalid_
    invalid_files = list(cookies_dir.glob("invalid_extracted_*.txt"))
    
    if not invalid_files:
        print("Файлы с префиксом invalid_extracted_ не найдены")
        return
    
    print(f"Найдено {len(invalid_files)} файлов для отката")
    
    rollback_count = 0
    
    for invalid_file in invalid_files:
        # Получить оригинальное имя файла (убрать префикс invalid_)
        original_name = invalid_file.name.replace("invalid_", "")
        original_path = cookies_dir / original_name
        
        try:
            # Переименовать файл обратно
            invalid_file.rename(original_path)
            print(f"✓ Откачен: {invalid_file.name} -> {original_name}")
            rollback_count += 1
            
            # Также откатить папку со скриншотами, если она существует
            invalid_screenshot_pattern = f"invalid_{original_name.replace('.txt', '')}_*"
            invalid_screenshot_dirs = list(screenshots_dir.glob(invalid_screenshot_pattern))
            
            for invalid_screenshot_dir in invalid_screenshot_dirs:
                # Убрать префикс invalid_ из имени папки
                original_screenshot_name = invalid_screenshot_dir.name.replace("invalid_", "")
                original_screenshot_path = screenshots_dir / original_screenshot_name
                
                if not original_screenshot_path.exists():
                    invalid_screenshot_dir.rename(original_screenshot_path)
                    print(f"  ✓ Откачена папка скриншотов: {invalid_screenshot_dir.name} -> {original_screenshot_name}")
                else:
                    print(f"  ⚠ Папка скриншотов уже существует: {original_screenshot_name}")
            
        except Exception as e:
            print(f"✗ Ошибка при откате {invalid_file.name}: {e}")
    
    print(f"\nОткачено файлов: {rollback_count} из {len(invalid_files)}")
    
    # Показать статистику оставшихся файлов
    remaining_invalid = len(list(cookies_dir.glob("invalid_*.txt")))
    extracted_files = len(list(cookies_dir.glob("extracted_*.txt")))
    valid_files = len(list(cookies_dir.glob("valid_*.txt")))
    
    print(f"\nТекущая статистика:")
    print(f"- Файлы extracted_: {extracted_files}")
    print(f"- Файлы valid_: {valid_files}")
    print(f"- Файлы invalid_: {remaining_invalid}")

if __name__ == "__main__":
    print("Откат файлов куков, помеченных как invalid...")
    print("=" * 50)
    rollback_invalid_cookies()