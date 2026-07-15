"""
SQLite база данных для локального хранения:
- Elo рейтингов команд
- Истории матчей
- Прогнозов и результатов
- ROI статистики

SQLite идеален для локального использования - не требует сервера.
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from config.settings import db_config


class FootballDatabase:
    """
    Локальная SQLite база данных

    Таблицы:
    - teams: команды с Elo рейтингами
    - matches: история матчей
    - predictions: прогнозы и их результаты
    - roi_tracking: статистика ROI
    - cache: кэш API-ответов
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or db_config.DB_PATH
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        """Инициализация таблиц"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Команды с Elo
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS teams (
                team_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                country TEXT,
                league_id INTEGER,
                elo_k32 REAL DEFAULT 1500,
                elo_k200 REAL DEFAULT 1500,
                elo_k500 REAL DEFAULT 1500,
                elo_k2000 REAL DEFAULT 1500,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Матчи
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                match_id INTEGER PRIMARY KEY,
                league_id INTEGER,
                season TEXT,
                match_date TIMESTAMP,
                home_team_id INTEGER,
                away_team_id INTEGER,
                home_goals INTEGER,
                away_goals INTEGER,
                home_xg REAL,
                away_xg REAL,
                status TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Прогнозы
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_id INTEGER,
                match_date TIMESTAMP,
                home_team TEXT,
                away_team TEXT,
                league_name TEXT,
                prob_home REAL,
                prob_draw REAL,
                prob_away REAL,
                prob_over25 REAL,
                prob_under25 REAL,
                confidence REAL,
                data_quality REAL,
                value_bets_json TEXT,
                top_selection TEXT,
                top_odds REAL,
                top_edge REAL,
                top_kelly REAL,
                prediction_strength REAL,
                result_home_goals INTEGER,
                result_away_goals INTEGER,
                result_status TEXT DEFAULT 'pending',
                actual_roi REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
        """)

        # ROI статистика
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS roi_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                total_predictions INTEGER DEFAULT 0,
                value_bets_placed INTEGER DEFAULT 0,
                wins INTEGER DEFAULT 0,
                losses INTEGER DEFAULT 0,
                total_staked REAL DEFAULT 0,
                total_returned REAL DEFAULT 0,
                roi_percent REAL DEFAULT 0,
                avg_edge REAL DEFAULT 0,
                yield_percent REAL DEFAULT 0
            )
        """)

        # Кэш API
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_cache (
                cache_key TEXT PRIMARY KEY,
                endpoint TEXT,
                params TEXT,
                response_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    # === TEAMS ===
    def save_team(self, team_id: int, name: str, country: str = "", 
                  league_id: int = None, elo_ratings: Dict[int, float] = None):
        """Сохранить/обновить команду с Elo"""
        conn = self._get_connection()
        cursor = conn.cursor()

        elo = elo_ratings or {32: 1500, 200: 1500, 500: 1500, 2000: 1500}

        cursor.execute("""
            INSERT OR REPLACE INTO teams 
            (team_id, name, country, league_id, elo_k32, elo_k200, elo_k500, elo_k2000, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (team_id, name, country, league_id, 
              elo.get(32, 1500), elo.get(200, 1500), 
              elo.get(500, 1500), elo.get(2000, 1500), datetime.now()))

        conn.commit()
        conn.close()

    def get_team(self, team_id: int) -> Optional[Dict]:
        """Получить данные команды"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM teams WHERE team_id = ?", (team_id,))
        row = cursor.fetchone()
        conn.close()

        if row:
            return {
                "team_id": row[0], "name": row[1], "country": row[2],
                "league_id": row[3],
                "elo": {32: row[4], 200: row[5], 500: row[6], 2000: row[7]},
                "last_updated": row[8]
            }
        return None

    def get_all_teams(self) -> List[Dict]:
        """Получить все команды"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM teams")
        rows = cursor.fetchall()
        conn.close()

        return [{
            "team_id": r[0], "name": r[1], "country": r[2],
            "league_id": r[3],
            "elo": {32: r[4], 200: r[5], 500: r[6], 2000: r[7]},
            "last_updated": r[8]
        } for r in rows]

    # === MATCHES ===
    def save_match(self, match_data: Dict):
        """Сохранить матч"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO matches 
            (match_id, league_id, season, match_date, home_team_id, away_team_id,
             home_goals, away_goals, home_xg, away_xg, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match_data["match_id"], match_data.get("league_id"),
            match_data.get("season"), match_data.get("match_date"),
            match_data.get("home_team_id"), match_data.get("away_team_id"),
            match_data.get("home_goals"), match_data.get("away_goals"),
            match_data.get("home_xg"), match_data.get("away_xg"),
            match_data.get("status", "SCHEDULED")
        ))

        conn.commit()
        conn.close()

    def get_last_matches(self, team_id: int, limit: int = 10) -> List[Dict]:
        """Получить последние матчи команды"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM matches 
            WHERE home_team_id = ? OR away_team_id = ?
            AND status = 'FINISHED'
            ORDER BY match_date DESC
            LIMIT ?
        """, (team_id, team_id, limit))

        rows = cursor.fetchall()
        conn.close()

        matches = []
        for r in rows:
            is_home = r[4] == team_id
            matches.append({
                "match_id": r[0], "match_date": r[3],
                "is_home": is_home,
                "opponent_id": r[5] if is_home else r[4],
                "goals_for": r[6] if is_home else r[7],
                "goals_against": r[7] if is_home else r[6],
                "xg_for": r[8] if is_home else r[9],
                "xg_against": r[9] if is_home else r[8]
            })
        return matches

    # === PREDICTIONS ===
    def save_prediction(self, prediction: Dict):
        """Сохранить прогноз"""
        conn = self._get_connection()
        cursor = conn.cursor()

        value_bets = prediction.get("value_bets", [])
        top = value_bets[0] if value_bets else {}

        cursor.execute("""
            INSERT INTO predictions 
            (match_id, match_date, home_team, away_team, league_name,
             prob_home, prob_draw, prob_away, prob_over25, prob_under25,
             confidence, data_quality, value_bets_json, top_selection,
             top_odds, top_edge, top_kelly, prediction_strength)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            prediction["match_id"],
            prediction.get("match_date"),
            prediction.get("home_team", ""),
            prediction.get("away_team", ""),
            prediction.get("league_name", ""),
            prediction["ensemble_probabilities"]["home_win"],
            prediction["ensemble_probabilities"]["draw"],
            prediction["ensemble_probabilities"]["away_win"],
            prediction.get("prob_over25", 0),
            prediction.get("prob_under25", 0),
            prediction["confidence"],
            prediction["data_quality"],
            json.dumps(value_bets, ensure_ascii=False),
            top.get("selection", ""),
            top.get("odds", 0),
            top.get("edge", 0),
            top.get("kelly", 0),
            prediction["prediction_strength"]
        ))

        conn.commit()
        conn.close()

    def update_prediction_result(self, match_id: int, home_goals: int, away_goals: int):
        """Обновить результат матча и рассчитать ROI"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Получаем прогноз
        cursor.execute("SELECT * FROM predictions WHERE match_id = ?", (match_id,))
        row = cursor.fetchone()

        if not row:
            conn.close()
            return

        # Определяем результат
        if home_goals > away_goals:
            result = "home_win"
        elif home_goals < away_goals:
            result = "away_win"
        else:
            result = "draw"

        # Проверяем, была ли value ставка на этот исход
        value_bets = json.loads(row[13]) if row[13] else []
        actual_roi = 0

        for vb in value_bets:
            if vb.get("selection") == result:
                # Выигрыш
                actual_roi = (vb["odds"] - 1) * vb["kelly"] * 100  # % от банка
                break
            elif vb.get("selection") in ["home_win", "draw", "away_win"]:
                # Проигрыш
                actual_roi = -vb["kelly"] * 100

        cursor.execute("""
            UPDATE predictions 
            SET result_home_goals = ?, result_away_goals = ?,
                result_status = 'resolved', actual_roi = ?, resolved_at = ?
            WHERE match_id = ?
        """, (home_goals, away_goals, actual_roi, datetime.now(), match_id))

        conn.commit()
        conn.close()

    def get_pending_predictions(self) -> List[Dict]:
        """Получить незавершённые прогнозы"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM predictions 
            WHERE result_status = 'pending'
            AND match_date < ?
            ORDER BY match_date DESC
        """, (datetime.now(),))

        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_dict(cursor, r) for r in rows]

    # === ROI STATISTICS ===
    def get_roi_stats(self, days: int = 30) -> Dict:
        """Получить ROI статистику за период"""
        conn = self._get_connection()
        cursor = conn.cursor()

        since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN result_status = 'resolved' THEN 1 ELSE 0 END) as resolved,
                SUM(CASE WHEN actual_roi > 0 THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN actual_roi < 0 THEN 1 ELSE 0 END) as losses,
                SUM(CASE WHEN actual_roi > 0 THEN actual_roi ELSE 0 END) as profit,
                SUM(CASE WHEN actual_roi < 0 THEN actual_roi ELSE 0 END) as loss,
                AVG(top_edge) as avg_edge,
                AVG(confidence) as avg_confidence
            FROM predictions
            WHERE created_at >= ?
        """, (since,))

        row = cursor.fetchone()
        conn.close()

        total = row[0] or 0
        wins = row[2] or 0
        losses = row[3] or 0
        profit = row[4] or 0
        loss = row[5] or 0

        return {
            "total_predictions": total,
            "resolved": row[1] or 0,
            "wins": wins,
            "losses": losses,
            "win_rate": wins / (wins + losses) * 100 if (wins + losses) > 0 else 0,
            "total_roi": profit + loss,
            "avg_edge": row[6] or 0,
            "avg_confidence": row[7] or 0,
            "yield_percent": (profit + loss) / total if total > 0 else 0
        }

    # === CACHE ===
    def get_cache(self, key: str) -> Optional[Dict]:
        """Получить кэшированные данные"""
        if not db_config.ENABLE_CACHE:
            return None

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT response_json FROM api_cache 
            WHERE cache_key = ? AND expires_at > ?
        """, (key, datetime.now()))

        row = cursor.fetchone()
        conn.close()

        if row:
            return json.loads(row[0])
        return None

    def set_cache(self, key: str, data: Dict, ttl_hours: int = None):
        """Сохранить данные в кэш"""
        if not db_config.ENABLE_CACHE:
            return

        ttl = ttl_hours or db_config.CACHE_TTL_HOURS
        expires = datetime.now() + timedelta(hours=ttl)

        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO api_cache (cache_key, response_json, expires_at)
            VALUES (?, ?, ?)
        """, (key, json.dumps(data, ensure_ascii=False), expires))

        conn.commit()
        conn.close()

    def _row_to_dict(self, cursor, row):
        """Конвертировать row в dict"""
        return {col[0]: row[i] for i, col in enumerate(cursor.description)}


# Синглтон
db = FootballDatabase()
