#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автоматический установщик Football Analytics Pro для Windows
Запуск: python setup.py
"""
import os
import sys
import zipfile
import subprocess
from pathlib import Path


def print_header():
    print("=" * 50)
    print("  ⚽ Football Analytics Pro - Установка")
    print("=" * 50)
    print()


def check_python():
    """Проверка версии Python"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("❌ Требуется Python 3.10+")
        print(f"   У вас: Python {version.major}.{version.minor}")
        print("   Скачать: https://python.org/downloads")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True


def find_archive():
    """Поиск архива рядом со скриптом"""
    script_dir = Path(__file__).parent
    archive = script_dir / "football_analytics_bot.zip"

    if not archive.exists():
        # Ищем в текущей директории
        for file in Path.cwd().glob("football_analytics_bot.zip"):
            return file
        print("❌ Архив football_analytics_bot.zip не найден!")
        print(f"   Искали в: {script_dir}")
        print("   Поместите архив в одну папку со скриптом")
        return None

    return archive


def extract_archive(archive_path: Path):
    """Распаковка архива"""
    extract_to = archive_path.parent / "football_analytics_bot"

    print(f"📦 Распаковка в: {extract_to}")

    with zipfile.ZipFile(archive_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)

    print(f"✅ Распаковано")
    return extract_to


def install_dependencies(project_dir: Path):
    """Установка зависимостей"""
    print("📥 Установка зависимостей...")

    req_file = project_dir / "requirements.txt"
    if not req_file.exists():
        print("❌ requirements.txt не найден")
        return False

    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("❌ Ошибка установки:")
        print(result.stderr)
        return False

    print("✅ Зависимости установлены")
    return True


def initialize_project(project_dir: Path):
    """Первая инициализация"""
    print("🔄 Инициализация данных (загрузка команд и Elo)...")
    print("   Это может занять несколько минут...")

    result = subprocess.run(
        [sys.executable, "main.py", "--mode", "update"],
        cwd=project_dir,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("⚠️ Возможны ошибки при инициализации")
        print("   Но проект готов к работе")
    else:
        print("✅ Инициализация завершена")

    return True


def create_shortcuts(project_dir: Path):
    """Создание ярлыков для запуска"""
    print("📝 Создание ярлыков...")

    desktop = Path.home() / "Desktop"
    script_dir = Path(__file__).parent

    shortcuts = {
        "Запустить_Дашборд.bat": f'cd /d "{project_dir}"\npython main.py --mode dashboard\npause',
        "Анализ_Матчей.bat": f'cd /d "{project_dir}"\npython main.py --mode analyze --bankroll 1000\npause',
        "Telegram_Бот.bat": f'cd /d "{project_dir}"\npython main.py --mode telegram\npause',
        "Обновить_Данные.bat": f'cd /d "{project_dir}"\npython main.py --mode update\npause',
    }

    for name, content in shortcuts.items():
        shortcut_path = script_dir / name
        with open(shortcut_path, "w", encoding="utf-8") as f:
            f.write("@echo off\nchcp 65001 >nul\n" + content)
        print(f"   ✅ {name}")

    return True


def main():
    print_header()

    # 1. Проверка Python
    if not check_python():
        input("\nНажмите Enter для выхода...")
        return

    # 2. Поиск архива
    archive = find_archive()
    if not archive:
        input("\nНажмите Enter для выхода...")
        return
    print(f"✅ Архив найден: {archive}")

    # 3. Распаковка
    try:
        project_dir = extract_archive(archive)
    except Exception as e:
        print(f"❌ Ошибка распаковки: {e}")
        input("\nНажмите Enter для выхода...")
        return

    # 4. Установка зависимостей
    if not install_dependencies(project_dir):
        input("\nНажмите Enter для выхода...")
        return

    # 5. Инициализация
    initialize_project(project_dir)

    # 6. Ярлыки
    create_shortcuts(project_dir)

    # Финал
    print()
    print("=" * 50)
    print("  🎉 УСТАНОВКА ЗАВЕРШЕНА!")
    print("=" * 50)
    print()
    print(f"📂 Проект: {project_dir}")
    print()
    print("🚀 Запуск (ярлыки рядом со скриптом):")
    print("   • Запустить_Дашборд.bat")
    print("   • Анализ_Матчей.bat")
    print("   • Telegram_Бот.bat")
    print("   • Обновить_Данные.bat")
    print()
    print("💡 Или вручную:")
    print(f'   cd "{project_dir}"')
    print("   python main.py --mode dashboard")
    print()

    input("Нажмите Enter для выхода...")


if __name__ == "__main__":
    main()
