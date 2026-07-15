"""
Интеграция с football-data.org
Бесплатный тариф: 12 лиг, 10 запросов/мин, текущий сезон доступен
API: https://api.football-data.org/v4/
"""
import requests
import time
from typing import List, Dict, Optional
from datetime import datetime

from config.settings import api_config
from database import db


class FootballDataClient:
    """
    Клиент для football-data.org

    Бесплатный тариф:
    - 12 соревнований (Топ-5 + Champions League + др.)
    - 10 запросов/мин
    - Текущий сезон доступен
    - Нужен API key (бесплатный)

    Получить ключ: https://www.football-data.org/
    """

    BASE_URL = "https://api.football-data.org/v4"

    # ID лиг (Топ-5 Европы)
    LEAGUE_IDS = {
        "PL": 2021,      # Premier League
        "BL1": 2002,     # Bundesliga
        "SA": 2019,      # Serie A
        "PD": 2014,      # La Liga (Primera Division)
        "FL1": 2015,     # Ligue 1
        "CL": 2001,      # Champions League
    }

    def __init__(self, api_key: str = None):
        self.api_key = api_key or "YOUR_API_KEY"
        self.headers = {"X-Auth-Token": self.api_key}
        self.last_request = 0
        self.min_delay = 6.0  # 10 запросов/мин = 6 сек между запросами

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
            print("⚠️ Rate limit exceeded, ждём 10 сек...")
            time.sleep(10)
            return self._request(endpoint, params)

        if response.status_code == 403:
            raise APIError("Неверный API ключ или доступ запрещён. Получите ключ на football-data.org")

        if response.status_code != 200:
            raise APIError(f"HTTP {response.status_code}: {response.text}")

        return response.json()

    def get_competitions(self) -> List[Dict]:
        """Получить список доступных соревнований"""
        data = self._request("competitions")
        return data.get("competitions", [])

    def get_matches(
        self,
        competition: str = None,
        date_from: str = None,
        date_to: str = None,
        status: str = None
    ) -> List[Dict]:
        """
        Получить матчи

        Args:
            competition: Код лиги (PL, BL1, SA, PD, FL1, CL)
            date_from: YYYY-MM-DD
            date_to: YYYY-MM-DD
            status: SCHEDULED, LIVE, IN_PLAY, FINISHED, TIMED
        """
        if competition:
            league_id = self.LEAGUE_IDS.get(competition)
            if not league_id:
                raise APIError(f"Неизвестная лига: {competition}")
            endpoint = f"competitions/{league_id}/matches"
        else:
            endpoint = "matches"

        params = {}
        if date_from:
            params["dateFrom"] = date_from
        if date_to:
            params["dateTo"] = date_to
        if status:
            params["status"] = status

        data = self._request(endpoint, params)
        return data.get("matches", [])

    def get_today_matches(self) -> List[Dict]:
        """Матчи на сегодня"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.get_matches(date_from=today, date_to=today)

    def get_upcoming_matches(self, days: int = 7) -> List[Dict]:
        """Предстоящие матчи"""
        today = datetime.now().strftime("%Y-%m-%d")
        future = (datetime.now() + __import__("datetime").timedelta(days=days)).strftime("%Y-%m-%d")
        return self.get_matches(date_from=today, date_to=future, status="SCHEDULED")

    def get_standings(self, competition: str) -> Dict:
        """Турнирная таблица"""
        league_id = self.LEAGUE_IDS.get(competition)
        if not league_id:
            raise APIError(f"Неизвестная лига: {competition}")

        return self._request(f"competitions/{league_id}/standings")

    def get_team(self, team_id: int) -> Dict:
        """Информация о команде"""
        return self._request(f"teams/{team_id}")

    def convert_to_fixture_format(self, match: Dict) -> Dict:
        """
        Конвертировать формат football-data.org в формат API-Football
        для совместимости с остальным проектом
        """
        return {
            "fixture": {
                "id": match.get("id"),
                "date": match.get("utcDate"),
                "status": match.get("status"),
                "venue": match.get("venue", "")
            },
            "league": {
                "id": match.get("competition", {}).get("id"),
                "name": match.get("competition", {}).get("name"),
                "season": match.get("season", {}).get("startDate", "")[:4]
            },
            "teams": {
                "home": {
                    "id": match.get("homeTeam", {}).get("id"),
                    "name": match.get("homeTeam", {}).get("name"),
                    "shortName": match.get("homeTeam", {}).get("shortName", "")
                },
                "away": {
                    "id": match.get("awayTeam", {}).get("id"),
                    "name": match.get("awayTeam", {}).get("name"),
                    "shortName": match.get("awayTeam", {}).get("shortName", "")
                }
            },
            "goals": {
                "home": match.get("score", {}).get("fullTime", {}).get("home"),
                "away": match.get("score", {}).get("fullTime", {}).get("away")
            },
            "score": {
                "halftime": {
                    "home": match.get("score", {}).get("halfTime", {}).get("home"),
                    "away": match.get("score", {}).get("halfTime", {}).get("away")
                }
            }
        }


class APIError(Exception):
    pass


# Синглтон (без ключа — нужно получить на football-data.org)
football_data = FootballDataClient()
