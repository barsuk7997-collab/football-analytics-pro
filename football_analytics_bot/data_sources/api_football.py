"""
Интеграция с API-Football v3 (api-football.com)
Бесплатный тариф: 100 запросов/день

⚠️ БЕСПЛАТНЫЙ ТАРИФ ОГРАНИЧЕНИЯ:
- Сезоны: только 2022-2024
- Для текущих матчей используем live endpoint или без season
"""
import requests
import time
import hashlib
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta

from config.settings import api_config
from database import db


class APIFootballClient:
    """
    Клиент для API-Football v3
    Адаптирован для бесплатного тарифа (сезоны 2022-2024)
    """

    def __init__(self):
        self.base_url = api_config.API_FOOTBALL_URL
        self.headers = {
            "x-rapidapi-host": api_config.API_FOOTBALL_HOST,
            "x-rapidapi-key": api_config.API_FOOTBALL_KEY
        }
        self.delay = api_config.API_FOOTBALL_DELAY
        self._last_request = 0
        self._daily_count = 0
        self._daily_reset = datetime.now().date()

    def _check_rate_limit(self):
        """Проверка и ожидание rate limit"""
        today = datetime.now().date()
        if today != self._daily_reset:
            self._daily_count = 0
            self._daily_reset = today

        if self._daily_count >= api_config.API_FOOTBALL_DAILY_LIMIT:
            raise RateLimitError("Daily limit reached (100 requests)")

        elapsed = time.time() - self._last_request
        if elapsed < self.delay:
            time.sleep(self.delay - elapsed)

    def _request(self, endpoint: str, params: Dict = None) -> Dict:
        """Выполнить запрос с кэшированием и rate limiting"""
        cache_key = self._make_cache_key(endpoint, params)
        cached = db.get_cache(cache_key)
        if cached:
            return cached

        self._check_rate_limit()

        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, headers=self.headers, params=params, timeout=30)
        self._last_request = time.time()
        self._daily_count += 1

        if response.status_code == 429:
            raise RateLimitError("Rate limit exceeded")

        if response.status_code != 200:
            raise APIError(f"HTTP {response.status_code}: {response.text}")

        data = response.json()
        if data.get("errors"):
            # Проверяем тип ошибки
            errors = data["errors"]
            if isinstance(errors, dict):
                if "season" in errors or "plan" in str(errors):
                    # Ошибка сезона — возвращаем пустой результат
                    return {"response": [], "errors": errors}
            raise APIError(f"API Error: {errors}")

        db.set_cache(cache_key, data, ttl_hours=6)
        return data

    def _make_cache_key(self, endpoint: str, params: Dict) -> str:
        key_str = f"{endpoint}:{json.dumps(params or {}, sort_keys=True)}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def get_fixtures(
        self,
        date: Optional[str] = None,
        league_id: Optional[int] = None,
        team_id: Optional[int] = None,
        season: Optional[str] = None,
        status: str = "NS",
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> List[Dict]:
        """Получить список матчей"""
        params = {"status": status}
        if date:
            params["date"] = date
        if league_id:
            params["league"] = league_id
        if team_id:
            params["team"] = team_id
        if season:
            params["season"] = season
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        try:
            data = self._request("fixtures", params)
            return data.get("response", [])
        except APIError as e:
            if "season" in str(e).lower() or "plan" in str(e).lower():
                print(f"⚠️ Бесплатный тариф ограничен: {e}")
                return []
            raise

    def get_fixtures_without_season(
        self,
        date: Optional[str] = None,
        league_id: Optional[int] = None,
        status: str = "NS"
    ) -> List[Dict]:
        """
        Получить матчи БЕЗ указания сезона.
        Для бесплатного тарифа — пробуем без season.
        """
        params = {"status": status}
        if date:
            params["date"] = date
        if league_id:
            params["league"] = league_id

        try:
            data = self._request("fixtures", params)
            return data.get("response", [])
        except APIError as e:
            error_str = str(e).lower()
            if "season" in error_str or "plan" in error_str or "free" in error_str:
                print(f"⚠️ API ограничение: {e}")
                print(f"   Попробуйте использовать сезон 2024 или демо-данные")
                return []
            raise

    def get_daily_fixtures_top5(self, date: str) -> List[Dict]:
        """
        Получить матчи Топ-5 лиг за день.
        Для бесплатного тарифа используем season=2024 (исторические)
        или пробуем без season (текущие)
        """
        top5_leagues = [39, 140, 135, 78, 61]
        all_fixtures = []

        for league_id in top5_leagues:
            # Пробуем сначала без season (для текущих матчей)
            fixtures = self.get_fixtures_without_season(
                date=date,
                league_id=league_id,
                status="NS"
            )

            if not fixtures:
                # Если не сработало — пробуем с season=2024 (исторические)
                try:
                    fixtures = self.get_fixtures(
                        date=date,
                        league_id=league_id,
                        season="2024",
                        status="NS"
                    )
                except Exception:
                    fixtures = []

            all_fixtures.extend(fixtures)

        return all_fixtures

    def get_team_info(self, team_id: int) -> Dict:
        """Информация о команде"""
        try:
            data = self._request("teams", {"id": team_id})
            teams = data.get("response", [])
            return teams[0] if teams else {}
        except APIError:
            return {}

    def get_league_teams(self, league_id: int, season: str = "2024") -> List[Dict]:
        """Получить все команды лиги"""
        try:
            params = {"league": league_id, "season": season}
            data = self._request("teams", params)
            return data.get("response", [])
        except APIError as e:
            if "season" in str(e).lower() or "plan" in str(e).lower():
                print(f"⚠️ Нет доступа к сезону {season} для лиги {league_id}")
                return []
            raise

    def get_team_statistics(self, team_id: int, league_id: int, season: str = "2024") -> Dict:
        """Получить статистику команды"""
        try:
            params = {"team": team_id, "league": league_id, "season": season}
            data = self._request("teams/statistics", params)
            return data.get("response", {})
        except APIError:
            return {}


class APIError(Exception):
    """Ошибка API"""
    pass


class RateLimitError(APIError):
    """Превышен лимит запросов"""
    pass


# Синглтон
football_api = APIFootballClient()
