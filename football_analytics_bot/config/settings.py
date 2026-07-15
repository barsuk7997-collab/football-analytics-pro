"""
Конфигурация аналитического модуля Football Analytics Pro
Версия: 2.1 (football-data.org)
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class APIConfig:
    """Конфигурация API-источников"""

    # football-data.org (БЕСПЛАТНЫЙ, 12 лиг, текущий сезон)
    # Регистрация: https://www.football-data.org/client/register
    FOOTBALL_DATA_KEY: str = "91dbffc2323242f1bcd63bdd403eb9e4"

    # API-Football (резервный, ограничен бесплатный тариф)
    API_FOOTBALL_KEY: str = "22c5bafdc1f3ba01198c95699f9870ed"
    API_FOOTBALL_HOST: str = "v3.football.api-sports.io"
    API_FOOTBALL_URL: str = "https://v3.football.api-sports.io"

    # Rate limits API-Football
    API_FOOTBALL_DAILY_LIMIT: int = 100
    API_FOOTBALL_DELAY: float = 0.6

    # Polymarket (публичный доступ)
    POLYMARKET_API: str = "https://gamma-api.polymarket.com"
    POLYMARKET_GRAPHQL: str = "https://api.polymarket.com/graphql"

    # Telegram Bot
    TELEGRAM_BOT_TOKEN: str = "8785949425:AAHvzyykG7QEmqnZ8fRkOCmxJHNGWYzxyx4"
    TELEGRAM_CHAT_ID: str = "845348948"
    TELEGRAM_ENABLED: bool = True


@dataclass
class ModelConfig:
    """Параметры статистических моделей"""
    ELO_BASE_RATING: int = 1500
    ELO_K_FACTORS: List[int] = field(default_factory=lambda: [32, 200, 500, 2000])
    ELO_HOME_ADVANTAGE: int = 80
    ELO_GOAL_MARGIN_WEIGHT: bool = True
    ELO_REGRESSION_MEAN: float = 0.33

    FORM_MATCHES_COUNT: int = 5
    FORM_DECAY_FACTOR: float = 0.85

    MIN_VALUE_EDGE: float = 0.05
    MAX_VALUE_EDGE: float = 0.35
    MIN_ODDS: float = 1.50
    MAX_ODDS: float = 10.0

    KELLY_FRACTION: float = 0.25
    MIN_KELLY_BET: float = 0.01
    MAX_KELLY_BET: float = 0.10

    CONFIDENCE_THRESHOLD: float = 0.60
    ACTIVE_MARKETS: List[str] = field(default_factory=lambda: ["1X2", "OVER_UNDER_2_5"])


@dataclass
class LeagueConfig:
    """Конфигурация лиг - ТОП-5 ЕВРОПЫ"""
    LEAGUES: Dict[int, Dict] = field(default_factory=lambda: {
        39: {"name": "Premier League", "country": "England", "tier": 1},
        140: {"name": "La Liga", "country": "Spain", "tier": 1},
        135: {"name": "Serie A", "country": "Italy", "tier": 1},
        78: {"name": "Bundesliga", "country": "Germany", "tier": 1},
        61: {"name": "Ligue 1", "country": "France", "tier": 1},
    })


@dataclass
class DatabaseConfig:
    DB_TYPE: str = "sqlite"
    DB_PATH: str = "data/football_analytics.db"
    ENABLE_CACHE: bool = True
    CACHE_TTL_HOURS: int = 6


# Глобальные конфиги
api_config = APIConfig()
model_config = ModelConfig()
league_config = LeagueConfig()
db_config = DatabaseConfig()
