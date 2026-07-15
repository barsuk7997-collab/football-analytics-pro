"""
Интеграция с Polymarket для получения рынков футбольных матчей
Polymarket использует Polygon blockchain и GraphQL API
Публичный доступ - ключ не требуется
"""
import requests
from typing import List, Dict, Optional
from datetime import datetime

from database import db


class PolymarketClient:
    """
    Клиент для Polymarket

    Особенности:
    - Децентрализованные рынки предсказаний
    - Цены = вероятности (0-1)
    - Низкие комиссии, прозрачные расчёты
    """

    GRAPHQL_URL = "https://api.polymarket.com/graphql"
    REST_URL = "https://gamma-api.polymarket.com"

    # Запрос для поиска футбольных рынков
    FOOTBALL_MARKETS_QUERY = """
    query GetFootballMarkets($search: String!) {
        markets(
            where: {
                question_contains: $search,
                active: true,
                closed: false
            }
            limit: 50
            orderBy: volume
            orderDirection: desc
        ) {
            id
            question
            slug
            description
            volume
            liquidity
            outcomes {
                id
                name
                price
                probability
            }
            endDate
            category
            tags
        }
    }
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

    def search_football_markets(
        self,
        search_terms: List[str] = None
    ) -> List[Dict]:
        """
        Поиск футбольных рынков

        Args:
            search_terms: Ключевые слова для поиска
        """
        if search_terms is None:
            search_terms = ["football", "soccer", "match", "win", "draw", "premier", "la liga"]

        all_markets = []
        for term in search_terms:
            try:
                markets = self._graphql_query(
                    self.FOOTBALL_MARKETS_QUERY,
                    {"search": term}
                )
                if markets and "data" in markets:
                    all_markets.extend(markets["data"].get("markets", []))
            except Exception as e:
                print(f"Polymarket search error for '{term}': {e}")

        # Удаляем дубликаты
        seen = set()
        unique = []
        for m in all_markets:
            if m.get("id") and m["id"] not in seen:
                seen.add(m["id"])
                unique.append(m)

        return unique

    def get_market_by_id(self, market_id: str) -> Optional[Dict]:
        """Получить детали рынка по ID"""
        query = """
        query GetMarket($id: String!) {
            market(id: $id) {
                id
                question
                outcomes {
                    id
                    name
                    price
                    probability
                }
                volume
                liquidity
                endDate
            }
        }
        """
        try:
            result = self._graphql_query(query, {"id": market_id})
            return result.get("data", {}).get("market") if result else None
        except Exception as e:
            print(f"Error fetching market {market_id}: {e}")
            return None

    def match_polymarket_to_fixture(
        self,
        polymarket_market: Dict,
        fixtures: List[Dict]
    ) -> Optional[Dict]:
        """
        Сопоставить рынок Polymarket с матчем из API-Football

        Использует нечёткое сравнение названий команд
        """
        question = polymarket_market.get("question", "").lower()

        for fixture in fixtures:
            home = fixture["teams"]["home"]["name"].lower()
            away = fixture["teams"]["away"]["name"].lower()

            # Простое сопоставление по подстрокам
            home_match = any(word in question for word in home.split())
            away_match = any(word in question for word in away.split())

            if home_match or away_match:
                return {
                    "polymarket_id": polymarket_market["id"],
                    "fixture_id": fixture["fixture"]["id"],
                    "match": f"{fixture['teams']['home']['name']} vs {fixture['teams']['away']['name']}",
                    "polymarket_prices": {
                        o["name"]: o.get("price", 0) 
                        for o in polymarket_market.get("outcomes", [])
                    },
                    "polymarket_question": polymarket_market.get("question", "")
                }

        return None

    def get_all_football_markets(self) -> List[Dict]:
        """Получить все активные футбольные рынки"""
        return self.search_football_markets()

    def get_market_prices(self, market_id: str) -> Dict[str, float]:
        """Получить цены (вероятности) рынка"""
        market = self.get_market_by_id(market_id)
        if not market:
            return {}

        return {
            o["name"]: o.get("price", 0)
            for o in market.get("outcomes", [])
        }

    def _graphql_query(self, query: str, variables: Dict) -> Dict:
        """Выполнить GraphQL запрос"""
        response = self.session.post(
            self.GRAPHQL_URL,
            json={"query": query, "variables": variables},
            timeout=30
        )
        response.raise_for_status()
        return response.json()


# Синглтон
polymarket_client = PolymarketClient()
