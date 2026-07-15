"""
Агрегация коэффициентов без платного API Odds

Источники:
1. API-Football odds endpoint (если доступен на тарифе)
2. Ручной ввод через дашборд
3. Парсинг публичных агрегаторов (опционально)
4. Polymarket цены как альтернатива
"""
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from models.match import MatchOdds


@dataclass
class AggregatedOdds:
    """Агрегированные коэффициенты"""
    source: str
    home_win: float
    draw: float
    away_win: float
    over_2_5: Optional[float] = None
    under_2_5: Optional[float] = None
    timestamp: str = ""

    @property
    def margin(self) -> float:
        return (1/self.home_win + 1/self.draw + 1/self.away_win) - 1

    @property
    def implied_probs(self) -> Tuple[float, float, float]:
        """Подразумеваемые вероятности без маржи (proportional method)"""
        p_home = 1 / self.home_win
        p_draw = 1 / self.draw
        p_away = 1 / self.away_win
        total = p_home + p_draw + p_away
        return (p_home/total, p_draw/total, p_away/total)


class OddsAggregator:
    """
    Агрегатор коэффициентов без платного API

    Стратегии получения коэффициентов:
    1. Попытка получить через API-Football
    2. Использование Polymarket как benchmark
    3. Ручной ввод пользователем
    """

    def __init__(self, football_api_client=None):
        self.api = football_api_client
        self.manual_odds = {}  # {fixture_id: MatchOdds}

    def get_odds_from_api_football(self, fixture_id: int) -> Optional[MatchOdds]:
        """Попытка получить коэффициенты через API-Football"""
        if not self.api:
            return None

        try:
            odds_data = self.api.get_odds(fixture_id=fixture_id)
            if not odds_data:
                return None

            # Берем первого букмекера
            bookmaker = odds_data[0].get("bookmakers", [{}])[0]
            bets = bookmaker.get("bets", [])

            for bet in bets:
                if bet.get("name") == "Match Winner":
                    values = {v["value"]: v["odd"] for v in bet.get("values", [])}
                    return MatchOdds(
                        bookmaker=bookmaker.get("name", "Unknown"),
                        home_win=float(values.get("Home", 0)),
                        draw=float(values.get("Draw", 0)),
                        away_win=float(values.get("Away", 0))
                    )
        except Exception:
            pass

        return None

    def set_manual_odds(
        self,
        fixture_id: int,
        home_win: float,
        draw: float,
        away_win: float,
        over_2_5: float = None,
        under_2_5: float = None
    ):
        """Установить коэффициенты вручную (из дашборда или Telegram)"""
        self.manual_odds[fixture_id] = MatchOdds(
            bookmaker="Manual",
            home_win=home_win,
            draw=draw,
            away_win=away_win,
            over_2_5=over_2_5,
            under_2_5=under_2_5
        )

    def get_odds(self, fixture_id: int) -> Optional[MatchOdds]:
        """Получить коэффициенты (автоматически или вручную)"""
        # 1. Пробуем API
        odds = self.get_odds_from_api_football(fixture_id)
        if odds:
            return odds

        # 2. Проверяем ручной ввод
        if fixture_id in self.manual_odds:
            return self.manual_odds[fixture_id]

        return None

    def get_best_odds(self, fixture_ids: List[int]) -> Dict[int, MatchOdds]:
        """Получить коэффициенты для нескольких матчей"""
        return {fid: self.get_odds(fid) for fid in fixture_ids}

    def calculate_true_probability(
        self,
        odds: MatchOdds,
        method: str = "margin_proportional"
    ) -> Tuple[float, float, float]:
        """
        Удалить маржу букмекера для получения "истинной" вероятности

        Methods:
            - margin_proportional: Распределяем маржу пропорционально
            - basic: Простое деление на сумму
        """
        p_home = 1 / odds.home_win
        p_draw = 1 / odds.draw
        p_away = 1 / odds.away_win
        total = p_home + p_draw + p_away

        return (p_home/total, p_draw/total, p_away/total)

    def get_polymarket_as_odds(
        self,
        polymarket_prices: Dict[str, float]
    ) -> Optional[MatchOdds]:
        """
        Конвертировать цены Polymarket в коэффициенты

        Polymarket prices = вероятности (0-1)
        Коэффициент = 1 / вероятность
        """
        if not polymarket_prices:
            return None

        # Пытаемся распознать исходы
        home_odds = None
        draw_odds = None
        away_odds = None

        for name, price in polymarket_prices.items():
            name_lower = name.lower()
            if any(word in name_lower for word in ["home", "1", "п1"]):
                home_odds = 1 / price if price > 0 else 0
            elif any(word in name_lower for word in ["draw", "x", "ничья"]):
                draw_odds = 1 / price if price > 0 else 0
            elif any(word in name_lower for word in ["away", "2", "п2"]):
                away_odds = 1 / price if price > 0 else 0

        if home_odds and draw_odds and away_odds:
            return MatchOdds(
                bookmaker="Polymarket",
                home_win=home_odds,
                draw=draw_odds,
                away_win=away_odds
            )

        return None
