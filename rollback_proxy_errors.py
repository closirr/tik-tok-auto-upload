#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для отката файлов куков, которые были ошибочно помечены как invalid
из-за проблем с прокси или сетью
"""

import os
import shutil
import glob
from pathlib import Path
import datetime

def analyze_screenshot_folders():
    """Анализирует папки скриншотов для определения причины invalid статуса"""
    
    screenshots_dir = Path("screenshots")
    if not screenshots_dir.exists():
        return {}
    
    proxy_error_indicators = [
        "NS_ERROR_UNKNOWN_HOST",
        "connection refused", 
        "timeout",
        "network error",
        "dns",
        "ssl error",
        "proxy error"
    ]
    
    analysis_results = {}
    
    # Ищем папки с invalid_ префиксом
    for date_folder in screenshots_dir.iterdir():
        if date_folder.is_dir():
            invalid_folders = list(date_folder.glob("invalid_*"))
            
            for invalid_folder in invalid_folders:
                # Извлекаем имя куки файла из имени папки
                folder_name = invalid_folder.name
                # Убираем invalid_ и timestamp в конце
                cookie_name = folder_name.replace("invalid_", "").rsplit("_", 1)[0]
                
                # Проверяем скриншоты на наличие ошибок прокси
                has_proxy_error = False
                error_details = []
                
                # Ищем скриншоты с ошибками
                error_screenshots = list(invalid_folder.glob("*error*.png"))
                
                if error_screenshots:
                    # Если есть скриншоты ошибок, вероятно это проблема с прокси
                    has_proxy_error = True
                    error_details.append("Найдены скриншоты ошибок")
                
                # Проверяем отчет о прокси, если есть
                proxy_report = invalid_folder / "proxy_report.txt"
                if proxy_report.exists():
                    try:
                        with open(proxy_report, 'r', encoding='utf-8') as f:
                            report_content = f.read().lower()
                            
                        for indicator in proxy_error_indicators:
                            if indicator.lower() in report_content:
                                has_proxy_error = True
                                error_details.append(f"Найден индикатор: {indicator}")
                                break
                    except:
                        pass
                
                analysis_results[cookie_name] = {
                    'has_proxy_error': has_proxy_error,
                    'error_details': error_details,
                    'screenshot_folder': str(invalid_folder),
                    'date': date_folder.name
                }
    
    return analysis_results

def rollback_proxy_error_cookies():
    """Откатывает файлы куков, помеченные как invalid из-за проблем с прокси"""
    
    cookies_dir = Path("cookies")
    screenshots_dir = Path("screenshots")
    
    if not cookies_dir.exists():
        print("Папка cookies не найдена!")
        return
    
    # Проверяем, используются ли бесплатные прокси
    import config
    using_free_proxy = getattr(config, 'USE_FREE_PROXY', False)
    
    print("🔍 Анализ папок скриншотов для определения причин invalid статуса...")
    screenshot_analysis = analyze_screenshot_folders()
    
    # Найти все файлы с префиксом invalid_
    invalid_files = list(cookies_dir.glob("invalid_extracted_*.txt"))
    
    if not invalid_files:
        print("Файлы с префиксом invalid_extracted_ не найдены")
        return
    
    print(f"Найдено {len(invalid_files)} invalid файлов для анализа")
    
    if using_free_proxy:
        print("🆓 Обнаружено использование бесплатных прокси")
        print("   Все invalid файлы будут откачены, так как ошибки скорее всего связаны с прокси")
        
        # При использовании бесплатных прокси откатываем все файлы
        proxy_error_files = [(f, {'error_details': ['Бесплатные прокси - вероятная ошибка сети']}) for f in invalid_files]
        unknown_error_files = []
    else:
        print("💰 Обнаружено использование платных прокси")
        print("   Будут откачены только файлы с явными ошибками прокси")
        
        # Разделяем файлы на категории только для платных прокси
        proxy_error_files = []
        unknown_error_files = []
        
        for invalid_file in invalid_files:
            # Извлекаем имя куки файла
            cookie_name = invalid_file.name.replace("invalid_", "").replace(".txt", "")
            
            # Проверяем анализ скриншотов
            if cookie_name in screenshot_analysis:
                analysis = screenshot_analysis[cookie_name]
                if analysis['has_proxy_error']:
                    proxy_error_files.append((invalid_file, analysis))
                else:
                    unknown_error_files.append((invalid_file, analysis))
            else:
                # Если нет данных анализа, считаем неизвестной ошибкой
                unknown_error_files.append((invalid_file, {'error_details': ['Нет данных анализа']}))
    
    print(f"\n📊 Результаты анализа:")
    print(f"   🔗 Файлы для отката: {len(proxy_error_files)}")
    print(f"   ❓ Файлы остаются invalid: {len(unknown_error_files)}")
    
    if not proxy_error_files:
        print("\n✅ Файлов для отката не найдено")
        return
    
    print(f"\n🔄 Откат файлов:")
    
    rollback_count = 0
    
    for invalid_file, analysis in proxy_error_files:
        # Получить оригинальное имя файла (убрать префикс invalid_)
        original_name = invalid_file.name.replace("invalid_", "")
        original_path = cookies_dir / original_name
        
        try:
            # Переименовать файл обратно
            invalid_file.rename(original_path)
            print(f"✓ Откачен: {invalid_file.name} -> {original_name}")
            print(f"  Причина: {', '.join(analysis['error_details'])}")
            rollback_count += 1
            
            # Также откатить папку со скриншотами, если она существует
            if 'screenshot_folder' in analysis:
                screenshot_folder = Path(analysis['screenshot_folder'])
                if screenshot_folder.exists():
                    # Убрать префикс invalid_ из имени папки
                    original_screenshot_name = screenshot_folder.name.replace("invalid_", "")
                    original_screenshot_path = screenshot_folder.parent / original_screenshot_name
                    
                    if not original_screenshot_path.exists():
                        screenshot_folder.rename(original_screenshot_path)
                        print(f"  ✓ Откачена папка скриншотов: {screenshot_folder.name} -> {original_screenshot_name}")
                    else:
                        print(f"  ⚠ Папка скриншотов уже существует: {original_screenshot_name}")
            
        except Exception as e:
            print(f"✗ Ошибка при откате {invalid_file.name}: {e}")
    
    print(f"\n🎉 Откачено файлов: {rollback_count} из {len(proxy_error_files)}")
    
    if unknown_error_files:
        print(f"\n⚠️  Файлы остаются invalid (возможно реальные проблемы с куками):")
        for invalid_file, analysis in unknown_error_files[:5]:  # Показываем первые 5
            print(f"   - {invalid_file.name}")
            if analysis['error_details']:
                print(f"     Детали: {', '.join(analysis['error_details'])}")
        
        if len(unknown_error_files) > 5:
            print(f"   ... и еще {len(unknown_error_files) - 5} файлов")
    
    # Показать статистику оставшихся файлов
    remaining_invalid = len(list(cookies_dir.glob("invalid_*.txt")))
    extracted_files = len(list(cookies_dir.glob("extracted_*.txt")))
    valid_files = len(list(cookies_dir.glob("valid_*.txt")))
    
    print(f"\n📈 Текущая статистика:")
    print(f"   - Файлы extracted_: {extracted_files}")
    print(f"   - Файлы valid_: {valid_files}")
    print(f"   - Файлы invalid_: {remaining_invalid}")

def show_analysis_only():
    """Показывает только анализ без отката"""
    
    print("🔍 Анализ invalid файлов (без отката)")
    print("=" * 40)
    
    # Проверяем тип прокси
    import config
    using_free_proxy = getattr(config, 'USE_FREE_PROXY', False)
    proxy_type = "🆓 Бесплатные" if using_free_proxy else "💰 Платные"
    print(f"Тип прокси: {proxy_type}")
    
    screenshot_analysis = analyze_screenshot_folders()
    
    cookies_dir = Path("cookies")
    invalid_files = list(cookies_dir.glob("invalid_extracted_*.txt"))
    
    if not invalid_files:
        print("Файлы с префиксом invalid_extracted_ не найдены")
        return
    
    proxy_errors = 0
    unknown_errors = 0
    
    if using_free_proxy:
        print(f"\n🆓 При использовании бесплатных прокси все {len(invalid_files)} файлов будут откачены")
        proxy_errors = len(invalid_files)
    else:
        print(f"\n💰 При использовании платных прокси анализируем каждый файл:")
        
        for invalid_file in invalid_files:
            cookie_name = invalid_file.name.replace("invalid_", "").replace(".txt", "")
            
            if cookie_name in screenshot_analysis:
                analysis = screenshot_analysis[cookie_name]
                if analysis['has_proxy_error']:
                    proxy_errors += 1
                    print(f"🔗 {invalid_file.name}")
                    print(f"   Причина: {', '.join(analysis['error_details'])}")
                else:
                    unknown_errors += 1
            else:
                unknown_errors += 1
    
    print(f"\n📊 Итого:")
    print(f"   🔗 Будут откачены: {proxy_errors}")
    print(f"   ❓ Останутся invalid: {unknown_errors}")
    print(f"   📁 Всего invalid файлов: {len(invalid_files)}")
    
    if using_free_proxy:
        print(f"\n💡 Рекомендация: При бесплатных прокси откатывайте все invalid файлы")
    else:
        print(f"\n💡 Рекомендация: При платных прокси откатывайте только файлы с ошибками прокси")

if __name__ == "__main__":
    print("Откат файлов куков с ошибками прокси")
    print("=" * 40)
    
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--analyze":
        show_analysis_only()
    else:
        print("Для анализа без отката используйте: python rollback_proxy_errors.py --analyze")
        print()
        
        response = input("Продолжить откат файлов с ошибками прокси? (y/N): ")
        if response.lower() in ['y', 'yes', 'да']:
            rollback_proxy_error_cookies()
        else:
            print("Откат отменен")