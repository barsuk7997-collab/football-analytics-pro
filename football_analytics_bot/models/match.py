"""
Модель футбольного матча с полной статистикой
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum


class MatchStatus(Enum):
    SCHEDULED = "SCHEDULED"
    LIVE = "LIVE"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"


class MarketType(Enum):
    HOME_WIN = "1"
    DRAW = "X"
    AWAY_WIN = "2"
    OVER_2_5 = "OVER_2_5"
    UNDER_2_5 = "UNDER_2_5"
    BTTS_YES = "BTTS_YES"
    BTTS_NO = "BTTS_NO"
    ASIAN_HANDICAP = "AH"


@dataclass
class MatchOdds:
    """Коэффициенты букмекеров"""
    bookmaker: str
    home_win: float
    draw: float
    away_win: float
    over_2_5: Optional[float] = None
    under_2_5: Optional[float] = None
    btts_yes: Optional[float] = None
    btts_no: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def margin(self) -> float:
        """Букмекерская маржа (overround)"""
        return (1/self.home_win + 1/self.draw + 1/self.away_win) - 1

    @property
    def implied_prob_home(self) -> float:
        """Подразумеваемая вероятность победы хозяев (без маржи)"""
        total = 1/self.home_win + 1/self.draw + 1/self.away_win
        return (1/self.home_win) / total

    @property
    def implied_prob_draw(self) -> float:
        total = 1/self.home_win + 1/self.draw + 1/self.away_win
        return (1/self.draw) / total

    @property
    def implied_prob_away(self) -> float:
        total = 1/self.home_win + 1/self.draw + 1/self.away_win
        return (1/self.away_win) / total


@dataclass
class MatchScore:
    """Счет матча"""
    home: int = 0
    away: int = 0
    ht_home: Optional[int] = None
    ht_away: Optional[int] = None

    @property
    def total(self) -> int:
        return self.home + self.away

    @property
    def btts(self) -> bool:
        return self.home > 0 and self.away > 0

    @property
    def winner(self) -> Optional[str]:
        if self.home > self.away:
            return "home"
        elif self.away > self.home:
            return "away"
        return "draw"


@dataclass
class MatchStats:
    """Статистика матча (xG, удары, владение и т.д.)"""
    possession_home: Optional[float] = None
    possession_away: Optional[float] = None
    shots_home: Optional[int] = None
    shots_away: Optional[int] = None
    shots_on_target_home: Optional[int] = None
    shots_on_target_away: Optional[int] = None
    xg_home: Optional[float] = None
    xg_away: Optional[float] = None
    corners_home: Optional[int] = None
    corners_away: Optional[int] = None
    fouls_home: Optional[int] = None
    fouls_away: Optional[int] = None


@dataclass
class Match:
    """Полная модель футбольного матча"""
    match_id: int
    league_id: int
    season: str

    # Команды
    home_team_id: int
    home_team_name: str
    away_team_id: int
    away_team_name: str

    # Время и статус
    match_date: datetime
    status: MatchStatus = MatchStatus.SCHEDULED
    venue: str = ""
    is_neutral: bool = False  # Нейтральное поле?

    # Счет и статистика
    score: MatchScore = field(default_factory=MatchScore)
    stats: MatchStats = field(default_factory=MatchStats)

    # Коэффициенты
    odds: List[MatchOdds] = field(default_factory=list)

    # Составы
    home_lineup: List[Dict] = field(default_factory=list)
    away_lineup: List[Dict] = field(default_factory=list)

    # Прогнозы
    predictions: Dict[str, 'MatchPrediction'] = field(default_factory=dict)

    # Polymarket
    polymarket_market_id: Optional[str] = None
    polymarket_prices: Dict[str, float] = field(default_factory=dict)

    @property
    def is_finished(self) -> bool:
        return self.status == MatchStatus.FINISHED

    @property
    def best_odds(self) -> Optional[MatchOdds]:
        """Лучшие коэффициенты по каждому исходу"""
        if not self.odds:
            return None
        # Находим максимальные коэффициенты
        best = MatchOdds(
            bookmaker="Best Aggregate",
            home_win=max(o.home_win for o in self.odds),
            draw=max(o.draw for o in self.odds),
            away_win=max(o.away_win for o in self.odds)
        )
        return best

    @property
    def average_odds(self) -> Optional[MatchOdds]:
        """Средние коэффициенты"""
        if not self.odds:
            return None
        n = len(self.odds)
        return MatchOdds(
            bookmaker="Average",
            home_win=sum(o.home_win for o in self.odds) / n,
            draw=sum(o.draw for o in self.odds) / n,
            away_win=sum(o.away_win for o in self.odds) / n
        )

    def get_odds_by_bookmaker(self, bookmaker: str) -> Optional[MatchOdds]:
        """Получить коэффициенты конкретного букмекера"""
        for odds in self.odds:
            if odds.bookmaker.lower() == bookmaker.lower():
                return odds
        return None
