#!/usr/bin/env python3
"""
Football Analytics Pro — точка входа

Использование:
    python main.py --mode dashboard    # Запуск дашборда
    python main.py --mode analyze --date 2026-07-15  # Анализ матчей
    python main.py --mode backtest --season 2025  # Бэктестинг
    python main.py --mode telegram   # Запуск Telegram бота
    python main.py --mode update     # Обновление Elo и статистики
"""
import argparse
import asyncio
import json
from datetime import datetime, timedelta

from config.settings import api_config, model_config
from config.leagues import get_all_active_leagues
from data_sources.football_data_org import football_data, FootballDataClient
from data_sources.polymarket import polymarket_client
from data_sources.odds_aggregator import OddsAggregator
from core.match_analyzer import analyzer
from core.elo_engine import EloEngine
from database import db
from telegram_bot import telegram_bot
from models.team import Team, TeamElo
from models.match import Match, MatchScore


def setup_argparse():
    parser = argparse.ArgumentParser(description="Football Analytics Pro")
    parser.add_argument("--mode", choices=["dashboard", "analyze", "backtest", "telegram", "update"],
                       default="dashboard", help="Режим работы")
    parser.add_argument("--date", type=str, help="Дата для анализа (YYYY-MM-DD)")
    parser.add_argument("--league", type=int, help="ID лиги")
    parser.add_argument("--output", type=str, default="predictions.json",
                       help="Файл для сохранения результатов")
    parser.add_argument("--bankroll", type=float, default=1000,
                       help="Банкролл для расчёта Kelly")
    return parser.parse_args()


def initialize_teams_from_api():
    """Инициализация команд из football-data.org в БД"""
    print("🔄 Инициализация команд из football-data.org")
    print("⚠️ Нужен API ключ! Получите бесплатно на: https://www.football-data.org/")
    print()

    # Проверяем ключ
    if football_data.api_key == "YOUR_API_KEY":
        print("❌ API ключ не настроен!")
        print("   1. Зарегистрируйтесь на https://www.football-data.org/")
        print("   2. Получите бесплатный API ключ")
        print("   3. Вставьте ключ в файл: config/settings.py")
        print("      FOOTBALL_DATA_KEY = 'ваш_ключ'")
        return

    leagues = ["PL", "BL1", "SA", "PD", "FL1"]

    for league in leagues:
        try:
            # Получаем матчи для извлечения команд
            matches = football_data.get_matches(competition=league, status="SCHEDULED")

            # Извлекаем уникальные команды
            teams_dict = {}
            for match in matches:
                home = match.get("homeTeam", {})
                away = match.get("awayTeam", {})

                for team in [home, away]:
                    team_id = team.get("id")
                    if team_id and team_id not in teams_dict:
                        teams_dict[team_id] = team

            # Сохраняем в БД
            for team_id, team in teams_dict.items():
                db.save_team(
                    team_id=team_id,
                    name=team.get("name", ""),
                    country="",
                    league_id=league,
                    elo_ratings={32: 1500, 200: 1500, 500: 1500, 2000: 1500}
                )

            print(f"  ✅ {league}: {len(teams_dict)} команд сохранено")
        except Exception as e:
            print(f"  ❌ Ошибка лиги {league}: {e}")


def update_elo_from_finished_matches(season: str = "2024", days_back: int = 7):
    """
    Обновить Elo на основе завершённых матчей.

    ⚠️ БЕСПЛАТНЫЙ ТАРИФ: Нет доступа к историческим данным (прошлые даты).
    Elo будет рассчитываться по мере поступления новых матчей.
    """
    print("🔄 Обновление Elo...")
    print("⚠️ Бесплатный тариф не даёт доступ к историческим матчам.")
    print("   Elo инициализирован базовым значением 1500.")
    print("   По мере анализа новых матчей Elo будет обновляться.")
    print("✅ Elo готов к работе (базовые значения)")


def analyze_matches(date: str = None, league_id: int = None, bankroll: float = 1000):
    """Анализ предстоящих матчей"""
    if not date:
        date = datetime.now().strftime("%Y-%m-%d")

    print(f"🔍 Анализ матчей на {date}")

    # Получаем матчи (текущий сезон 2026)
    if league_id:
        fixtures = football_api.get_fixtures_without_season(date=date, league_id=league_id)
    else:
        fixtures = fd_client.get_matches_unified("PL", date, date)

    print(f"Найдено матчей: {len(fixtures)}")

    predictions = []
    odds_aggregator = OddsAggregator(football_api)

    for fixture in fixtures:
        match_id = fixture["fixture"]["id"]
        home_id = fixture["teams"]["home"]["id"]
        away_id = fixture["teams"]["away"]["id"]
        league = fixture["league"]["id"]

        home_name = fixture["teams"]["home"]["name"]
        away_name = fixture["teams"]["away"]["name"]

        print(f"\n📊 Анализ: {home_name} vs {away_name}")

        # Загружаем команды из БД
        home_data = db.get_team(home_id)
        away_data = db.get_team(away_id)

        if not home_data:
            print(f"  ⚠️ Команда {home_name} не найдена в БД, пропускаем")
            continue
        if not away_data:
            print(f"  ⚠️ Команда {away_name} не найдена в БД, пропускаем")
            continue

        # Создаём объекты команд
        from models.team import TeamElo
        home_team = Team(team_id=home_id, name=home_name)
        home_team.elo = TeamElo(ratings=home_data["elo"])

        away_team = Team(team_id=away_id, name=away_name)
        away_team.elo = TeamElo(ratings=away_data["elo"])

        # Создаём матч
        match = Match(
            match_id=match_id,
            league_id=league,
            season="2024",
            home_team_id=home_id,
            home_team_name=home_name,
            away_team_id=away_id,
            away_team_name=away_name,
            match_date=datetime.fromisoformat(fixture["fixture"]["date"].replace("Z", "+00:00"))
        )

        # Пробуем получить коэффициенты
        try:
            odds = odds_aggregator.get_odds(match_id)
            if odds:
                match.odds.append(odds)
        except Exception:
            pass

        # Анализ
        prediction = analyzer.analyze_match(match, home_team, away_team)
        pred_data = prediction.to_dict()
        pred_data["home_team"] = home_name
        pred_data["away_team"] = away_name
        pred_data["league_name"] = fixture["league"]["name"]
        pred_data["match_date"] = fixture["fixture"]["date"]
        predictions.append(pred_data)

        # Вывод результатов
        print(f"  Вероятности: П1={pred_data['ensemble_probabilities']['home_win']:.1%}, "
              f"X={pred_data['ensemble_probabilities']['draw']:.1%}, "
              f"П2={pred_data['ensemble_probabilities']['away_win']:.1%}")

        if pred_data["value_bets"]:
            print(f"  🎯 VALUE СТАВКИ:")
            for vb in pred_data["value_bets"]:
                bet_size = vb["kelly"] * bankroll
                print(f"    {vb['selection']}: кэф={vb['odds']:.2f}, "
                      f"edge={vb['edge']*100:.1f}%, Kelly={vb['kelly']*100:.1f}% "
                      f"(${bet_size:.2f})")
        else:
            print(f"  ❌ Value не обнаружено")

    return predictions


def run_dashboard():
    """Запуск Streamlit дашборда"""
    import subprocess
    import sys

    dashboard_path = "dashboard/app.py"
    print("🚀 Запуск дашборда...")
    subprocess.run([sys.executable, "-m", "streamlit", "run", dashboard_path])


def run_telegram():
    """Запуск Telegram бота"""
    print("🤖 Запуск Telegram бота...")
    telegram_bot.run()


def run_backtest(season: str = "2024"):
    """Бэктестинг модели на исторических данных"""
    print(f"📈 Бэктестинг сезона {season}...")
    # TODO: Реализовать полный бэктест
    print("(Функция в разработке)")


def main():
    args = setup_argparse()

    if args.mode == "dashboard":
        run_dashboard()

    elif args.mode == "analyze":
        predictions = analyze_matches(args.date, args.league, args.bankroll)

        # Сохраняем результаты
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(predictions, f, ensure_ascii=False, indent=2)

        print(f"\n✅ Результаты сохранены в {args.output}")

        # Сводка
        value_count = sum(1 for p in predictions if p["value_bets"])
        print(f"Матчей проанализировано: {len(predictions)}")
        print(f"Value-ставок найдено: {value_count}")

        # Отправляем в Telegram если есть value
        if telegram_bot.enabled and value_count > 0:
            asyncio.run(telegram_bot.send_daily_summary(predictions))

    elif args.mode == "telegram":
        run_telegram()

    elif args.mode == "backtest":
        run_backtest(args.season)

    elif args.mode == "update":
        print("🔄 Обновление данных...")
        initialize_teams_from_api()
        print("✅ Обновление завершено")


if __name__ == "__main__":
    main()
