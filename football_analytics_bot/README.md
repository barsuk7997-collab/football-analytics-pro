# ⚽ Football Analytics Pro

**Professional Value Betting Intelligence System**

Аналитический модуль для футбольных прогнозов с поиском value-ставок на основе статистических моделей.

## 🎯 Возможности

- **Мульти-K Elo система** — 4 временных горизонта (K=32/200/500/2000)
- **Poisson xG модель** — ожидаемые голы для тоталов и BTTS
- **Ансамблевое прогнозирование** — взвешенное голосование моделей
- **Kelly Criterion** — оптимальный размер ставки
- **Telegram уведомления** — мгновенные алерты о value-ставках
- **ROI трекинг** — автоматическая статистика результатов
- **SQLite база данных** — локальное хранение без сервера

## 🚀 Быстрый старт

### 1. Установка

```bash
git clone <repo>
cd football_analytics_bot
pip install -r requirements.txt
```

### 2. Первоначальная настройка

```bash
# Инициализация команд и Elo
python main.py --mode update
```

### 3. Запуск дашборда

```bash
python main.py --mode dashboard
```

### 4. Анализ матчей

```bash
# На сегодня
python main.py --mode analyze

# На конкретную дату
python main.py --mode analyze --date 2026-07-15

# С банкроллом $2000
python main.py --mode analyze --bankroll 2000
```

### 5. Telegram бот

```bash
python main.py --mode telegram
```

## 📊 Архитектура

```
football_analytics_bot/
├── config/
│   ├── settings.py          # API ключи, параметры
│   └── leagues.py           # Конфигурация лиг
├── core/
│   ├── elo_engine.py        # Мульти-K Elo
│   ├── match_analyzer.py    # Главный анализатор
│   ├── probability_model.py # Poisson xG
│   ├── form_calculator.py   # Расчёт формы
│   └── value_finder.py      # Детектор value
├── data_sources/
│   ├── api_football.py      # API-Football интеграция
│   ├── polymarket.py        # Polymarket рынки
│   └── odds_aggregator.py   # Агрегация коэффициентов
├── models/
│   ├── team.py              # Модель команды
│   ├── match.py             # Модель матча
│   └── prediction.py        # Модель прогноза
├── dashboard/
│   └── app.py               # Streamlit дашборд
├── database.py              # SQLite хранилище
├── telegram_bot.py          # Telegram уведомления
└── main.py                  # Точка входа
```

## 🎲 Модели

### Elo Engine
- **K=32** — краткосрочная динамика
- **K=200** — среднесрочные тренды
- **K=500** — долгосрочная сила
- **K=2000** — сезонная стабильность

### Ансамбль
| Модель | Вес | Назначение |
|--------|-----|------------|
| Elo    | 40% | Базовая сила команд |
| xG     | 30% | Тоталы и точный счёт |
| Форма  | 20% | Краткосрочный тренд |
| Рынок  | 10% | Wisdom of crowds |

## 📈 Value Betting

**Edge** = (Model_Prob - Market_Prob) / Market_Prob

**Kelly Fraction** = (bp - q) / b × 0.25

Где:
- b = odds - 1
- p = модельная вероятность
- q = 1 - p
- 0.25 = консервативный fractional Kelly

## ⚠️ Ограничения бесплатного тарифа API-Football

- **100 запросов/день**
- **~30 запросов/час** (для равномерности)
- Кэширование на 6 часов для экономии

## 🔧 Настройка

Все параметры в `config/settings.py`:

```python
MIN_VALUE_EDGE = 0.05      # Минимальный edge 5%
KELLY_FRACTION = 0.25      # Консервативный Kelly
CONFIDENCE_THRESHOLD = 0.60  # Минимальная уверенность
```

## 📋 Команды Telegram

- `/start` — Приветствие
- `/today` — Анализ сегодняшних матчей
- `/value` — Только value-ставки
- `/stats` — ROI статистика
- `/help` — Справка

## 📝 Лицензия

MIT License — используйте на свой страх и риск.

**Важно:** Это аналитический инструмент для ручного принятия решений. Автор не несёт ответственности за финансовые потери.
