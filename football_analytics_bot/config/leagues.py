"""
Конфигурация футбольных лиг и их специфических параметров
"""
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class LeagueParameters:
    """Параметры специфичные для лиги"""
    league_id: int
    name: str
    country: str
    tier: int  # 1 = топ-лига, 2 = второй эшелон

    # Elo параметры
    elo_k_factor: int = 32
    home_advantage_elo: int = 80

    # Средние показатели лиги (для нормализации)
    avg_goals_home: float = 1.50
    avg_goals_away: float = 1.15
    draw_rate: float = 0.26

    # Коэффициенты для расчета формы
    form_weight_recent: float = 0.30  # Вес последнего матча
    form_weight_oldest: float = 0.10  # Вес самого старого

    # Рынки для анализа
    markets: List[str] = None

    def __post_init__(self):
        if self.markets is None:
            self.markets = ["1X2", "OVER_UNDER_2_5", "BTTS", "ASIAN_HANDICAP"]


# База данных лиг
LEAGUES_DB: Dict[int, LeagueParameters] = {
    # Топ-5 Европы
    39: LeagueParameters(39, "Premier League", "England", 1, 
                         elo_k_factor=32, home_advantage_elo=85,
                         avg_goals_home=1.55, avg_goals_away=1.20, draw_rate=0.25),
    140: LeagueParameters(140, "La Liga", "Spain", 1,
                          elo_k_factor=32, home_advantage_elo=75,
                          avg_goals_home=1.45, avg_goals_away=1.10, draw_rate=0.28),
    135: LeagueParameters(135, "Serie A", "Italy", 1,
                          elo_k_factor=32, home_advantage_elo=70,
                          avg_goals_home=1.50, avg_goals_away=1.15, draw_rate=0.27),
    78: LeagueParameters(78, "Bundesliga", "Germany", 1,
                         elo_k_factor=35, home_advantage_elo=70,
                         avg_goals_home=1.70, avg_goals_away=1.35, draw_rate=0.23),
    61: LeagueParameters(61, "Ligue 1", "France", 1,
                         elo_k_factor=32, home_advantage_elo=65,
                         avg_goals_home=1.40, avg_goals_away=1.05, draw_rate=0.29),

    # Еврокубки
    2: LeagueParameters(2, "Champions League", "Europe", 1,
                        elo_k_factor=40, home_advantage_elo=60,
                        avg_goals_home=1.60, avg_goals_away=1.25, draw_rate=0.24),
    3: LeagueParameters(3, "Europa League", "Europe", 1,
                        elo_k_factor=38, home_advantage_elo=55,
                        avg_goals_home=1.50, avg_goals_away=1.15, draw_rate=0.26),

    # Вторые дивизионы (высокая волатильность = высокий K)
    40: LeagueParameters(40, "Championship", "England", 2,
                           elo_k_factor=45, home_advantage_elo=80,
                           avg_goals_home=1.45, avg_goals_away=1.10, draw_rate=0.28),
}


def get_league_params(league_id: int) -> LeagueParameters:
    """Получить параметры лиги по ID"""
    return LEAGUES_DB.get(league_id, LeagueParameters(
        league_id=league_id,
        name="Unknown",
        country="Unknown",
        tier=1
    ))


def get_all_active_leagues() -> List[int]:
    """Получить список активных лиг"""
    return list(LEAGUES_DB.keys())
