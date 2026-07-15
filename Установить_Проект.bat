@echo off
chcp 65001 >nul
title Football Analytics Pro - Установка
color 0A

echo ==========================================
echo  ⚽ Football Analytics Pro - Установка
echo ==========================================
echo.

:: Проверяем Python
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python не найден! Установите Python 3.10+
    echo    Скачать: https://python.org/downloads
    pause
    exit /b 1
)

echo ✅ Python найден
python --version
echo.

:: Путь к проекту (рядом с архивом)
set "PROJECT_DIR=%~dp0football_analytics_bot"
set "ARCHIVE=%~dp0football_analytics_bot.zip"

:: Проверяем архив
if not exist "%ARCHIVE%" (
    echo ❌ Архив не найден: %ARCHIVE%
    echo    Убедитесь, что football_analytics_bot.zip в одной папке со скриптом
    pause
    exit /b 1
)

echo ✅ Архив найден
echo.

:: Распаковка
echo 📦 Распаковка архива...
powershell -Command "Expand-Archive -Path '%ARCHIVE%' -DestinationPath '%PROJECT_DIR%' -Force"
if errorlevel 1 (
    echo ❌ Ошибка распаковки
    pause
    exit /b 1
)
echo ✅ Распаковано в: %PROJECT_DIR%
echo.

:: Переход в папку проекта
cd /d "%PROJECT_DIR%"

:: Установка зависимостей
echo 📥 Установка зависимостей...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ❌ Ошибка установки зависимостей
    pause
    exit /b 1
)
echo ✅ Зависимости установлены
echo.

:: Первый запуск - инициализация
echo 🔄 Первая инициализация (загрузка команд и Elo)...
python main.py --mode update
if errorlevel 1 (
    echo ⚠️ Возможны ошибки при инициализации, но проект готов к работе
)
echo.

:: Создаём ярлыки
echo 📝 Создание ярлыков...

:: Ярлык для дашборда
echo @echo off > "%~dp0Запустить_Дашборд.bat"
echo chcp 65001 ^>nul >> "%~dp0Запустить_Дашборд.bat"
echo cd /d "%PROJECT_DIR%" >> "%~dp0Запустить_Дашборд.bat"
echo python main.py --mode dashboard >> "%~dp0Запустить_Дашборд.bat"
echo pause >> "%~dp0Запустить_Дашборд.bat"

:: Ярлык для анализа
echo @echo off > "%~dp0Анализ_Матчей.bat"
echo chcp 65001 ^>nul >> "%~dp0Анализ_Матчей.bat"
echo cd /d "%PROJECT_DIR%" >> "%~dp0Анализ_Матчей.bat"
echo python main.py --mode analyze --bankroll 1000 >> "%~dp0Анализ_Матчей.bat"
echo pause >> "%~dp0Анализ_Матчей.bat"

:: Ярлык для Telegram
echo @echo off > "%~dp0Telegram_Бот.bat"
echo chcp 65001 ^>nul >> "%~dp0Telegram_Бот.bat"
echo cd /d "%PROJECT_DIR%" >> "%~dp0Telegram_Бот.bat"
echo python main.py --mode telegram >> "%~dp0Telegram_Бот.bat"
echo pause >> "%~dp0Telegram_Бот.bat"

:: Ярлык для обновления
echo @echo off > "%~dp0Обновить_Данные.bat"
echo chcp 65001 ^>nul >> "%~dp0Обновить_Данные.bat"
echo cd /d "%PROJECT_DIR%" >> "%~dp0Обновить_Данные.bat"
echo python main.py --mode update >> "%~dp0Обновить_Данные.bat"
echo pause >> "%~dp0Обновить_Данные.bat"

echo ✅ Ярлыки созданы
echo.

echo ==========================================
echo  🎉 УСТАНОВКА ЗАВЕРШЕНА!
echo ==========================================
echo.
echo 📂 Проект установлен в:
echo    %PROJECT_DIR%
echo.
echo 🚀 Быстрый запуск (ярлыки рядом):
echo    • Запустить_Дашборд.bat
echo    • Анализ_Матчей.bat
echo    • Telegram_Бот.bat
echo    • Обновить_Данные.bat
echo.
echo 💡 Или вручную:
echo    cd "%PROJECT_DIR%"
echo    python main.py --mode dashboard
echo.
pause
