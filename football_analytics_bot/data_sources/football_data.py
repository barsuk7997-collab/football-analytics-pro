"""
Интеграция с football-data.org API
БЕСПЛАТНЫЙ, 12 топ-лиг, 10 запросов/мин, founder обещал free forever

Регистрация: https://www.football-data.org/client/register
"""
import requests
import time
from typing import List, Dict, Optional
from datetime import datetime


class FootballDataClient:
    """
    Клиент для football-data.org API

    Бесплатный тариф:
    - 12 лиг: PL, La Liga, Bundesliga, Serie A, Ligue 1, Champions League, etc.
    - 10 запросов/мин
    - Результаты, расписание, турнирные таблицы, бомбардиры
    - Небольшая задержка (не real-time, но достаточно для анализа)

    Нужен API ключ (бесплатный): https://www.football-data.org/client/register
    """

    BASE_URL = "https://api.football-data.org/v4"

    # ID лиг (football-data.org)
    LEAGUE_IDS = {
        "PL": 2021,        # Premier League
        "ELC": 2016,       # Championship
        "BL1": 2002,       # Bundesliga
        "BL2": 2004,       # 2. Bundesliga
        "DED": 2003,       # Eredivisie
        "PPL": 2017,       # Primeira Liga
        "SA": 2019,        # Serie A
        "PD": 2014,        # La Liga
        "FL1": 2015,       # Ligue 1
        "CL": 2001,        # Champions League
        "EL": 2146,        # Europa League
        "WC": 2000,        # World Cup
        "EC": 2018,        # European Championship
    }

    def __init__(self, api_key: str = None):
        from config.settings import api_config
        self.api_key = api_config.FOOTBALL_DATA_KEY
        self.headers = {
            "X-Auth-Token": self.api_key
        }
        self.last_request = 0
        self.min_delay = 6.1  # 10 запросов/мин = 6 сек между запросами

    def _request(self, endpoint: str, params: Dict = None) -> Dict:
        """Запрос с rate limiting"""
        # Rate limiting
        elapsed = time.time() - self.last_request
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)

        url = f"{self.BASE_URL}/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        self.last_request = time.time()

        if response.status_code == 429:
            raise APIError("Rate limit exceeded (10 req/min)")

        if response.status_code == 403:
            raise APIError("Invalid API key or access denied")

        if response.status_code != 200:
            raise APIError(f"HTTP {response.status_code}: {response.text}")

        return response.json()

    # === COMPETITIONS ===
    def get_competitions(self) -> List[Dict]:
        """Список доступных лиг"""
        data = self._request("competitions")
        return data.get("competitions", [])

    # === MATCHES ===
    def get_matches(
        self,
        competition_id: int = None,
        date_from: str = None,
        date_to: str = None,
        status: str = None  # SCHEDULED, LIVE, IN_PLAY, FINISHED, POSTPONED, etc.
    ) -> List[Dict]:
        """
        Получить матчи

        Args:
            competition_id: ID лиги (2021=PL, 2014=La Liga, etc.)
            date_from: YYYY-MM-DD
            date_to: YYYY-MM-DD
            status: SCHEDULED, LIVE, FINISHED
        """
        params = {}
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        if status:
            params["status"] = status

        if competition_id:
            endpoint = f"competitions/{competition_id}/matches"
        else:
            endpoint = "matches"

        data = self._request(endpoint, params)
        return data.get("matches", [])

    def get_today_matches(self, competition_id: int = None) -> List[Dict]:
        """Матчи на сегодня"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.get_matches(
            competition_id=competition_id,
            date_from=today,
            date_to=today
        )

    def get_upcoming_matches(self, days: int = 7, competition_id: int = None) -> List[Dict]:
        """Предстоящие матчи"""
        today = datetime.now().strftime("%Y-%m-%d")
        to_date = (datetime.now() + __import__("datetime").timedelta(days=days)).strftime("%Y-%m-%d")
        return self.get_matches(
            competition_id=competition_id,
            date_from=today,
            date_to=to_date,
            status="SCHEDULED"
        )

    # === STANDINGS ===
    def get_standings(self, competition_id: int) -> Dict:
        """Турнирная таблица"""
        data = self._request(f"competitions/{competition_id}/standings")
        return data

    # === TEAMS ===
    def get_team(self, team_id: int) -> Dict:
        """Информация о команде"""
        return self._request(f"teams/{team_id}")

    def get_team_matches(self, team_id: int, status: str = None, limit: int = 10) -> List[Dict]:
        """Матчи команды"""
        params = {"limit": limit}
        if status:
            params["status"] = status
        data = self._request(f"teams/{team_id}/matches", params)
        return data.get("matches", [])

    # === TOP SCORERS ===
    def get_scorers(self, competition_id: int, limit: int = 10) -> List[Dict]:
        """Топ бомбардиры"""
        data = self._request(f"competitions/{competition_id}/scorers", {"limit": limit})
        return data.get("scorers", [])

    # === CONVERT TO UNIFIED FORMAT ===
    def convert_match(self, fd_match: Dict) -> Dict:
        """
        Конвертировать матч football-data.org в формат API-Football
        для совместимости с нашим модулем
        """
        return {
            "fixture": {
                "id": fd_match.get("id"),
                "date": fd_match.get("utcDate"),
                "status": {"short": fd_match.get("status", "")}
            },
            "league": {
                "id": fd_match.get("competition", {}).get("id"),
                "name": fd_match.get("competition", {}).get("name"),
                "season": fd_match.get("season", {}).get("id")
            },
            "teams": {
                "home": {
                    "id": fd_match.get("homeTeam", {}).get("id"),
                    "name": fd_match.get("homeTeam", {}).get("name"),
                    "logo": fd_match.get("homeTeam", {}).get("crest")
                },
                "away": {
                    "id": fd_match.get("awayTeam", {}).get("id"),
                    "name": fd_match.get("awayTeam", {}).get("name"),
                    "logo": fd_match.get("awayTeam", {}).get("crest")
                }
            },
            "goals": {
                "home": fd_match.get("score", {}).get("fullTime", {}).get("home"),
                "away": fd_match.get("score", {}).get("fullTime", {}).get("away")
            },
            "score": {
                "halftime": {
                    "home": fd_match.get("score", {}).get("halfTime", {}).get("home"),
                    "away": fd_match.get("score", {}).get("halfTime", {}).get("away")
                }
            }
        }

    def get_matches_unified(
        self,
        competition_code: str = None,
        date_from: str = None,
        date_to: str = None
    ) -> List[Dict]:
        """
        Получить матчи в унифицированном формате (совместим с API-Football)
        """
        comp_id = self.LEAGUE_IDS.get(competition_code) if competition_code else None
        matches = self.get_matches(comp_id, date_from, date_to)
        return [self.convert_match(m) for m in matches]


class APIError(Exception):
    pass
