"""
Модель прогноза матча с value betting анализом
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum


class BetRecommendation(Enum):
    STRONG_BUY = "STRONG_BUY"      # Уверенная ставка
    BUY = "BUY"                    # Рекомендуется
    NEUTRAL = "NEUTRAL"            # Нет value
    AVOID = "AVOID"                # Избегать
    STRONG_AVOID = "STRONG_AVOID"  # Против ставки


@dataclass
class ProbabilityDistribution:
    """Распределение вероятностей исходов"""
    home_win: float = 0.0
    draw: float = 0.0
    away_win: float = 0.0
    over_2_5: Optional[float] = None
    under_2_5: Optional[float] = None
    btts_yes: Optional[float] = None
    btts_no: Optional[float] = None

    @property
    def is_valid(self) -> bool:
        """Проверка валидности (сумма ~1.0)"""
        total = self.home_win + self.draw + self.away_win
        return 0.98 <= total <= 1.02

    def get_fair_odds(self) -> Dict[str, float]:
        """Преобразовать вероятности в честные коэффициенты"""
        return {
            "home_win": 1/self.home_win if self.home_win > 0 else 0,
            "draw": 1/self.draw if self.draw > 0 else 0,
            "away_win": 1/self.away_win if self.away_win > 0 else 0,
            "over_2_5": 1/self.over_2_5 if self.over_2_5 and self.over_2_5 > 0 else 0,
            "under_2_5": 1/self.under_2_5 if self.under_2_5 and self.under_2_5 > 0 else 0,
        }


@dataclass
class ValueBet:
    """Value-ставка с полным анализом"""
    market: str  # "1X2", "OVER_UNDER_2_5", "BTTS"
    selection: str  # "home_win", "draw", "away_win", "over_2_5", etc.

    # Вероятности
    model_probability: float
    market_probability: float
    implied_odds: float  # Коэффициент букмекера

    # Value метрики
    edge: float  # (model_prob - market_prob) / market_prob
    expected_value: float  # (model_prob * odds) - 1

    # Kelly Criterion
    kelly_fraction: float  # Оптимальная доля банка
    kelly_bet_size: float  # Рекомендуемая ставка в %

    # Доверие
    confidence: float  # 0-1
    model_agreement: float  # Согласие между моделями

    # Рекомендация
    recommendation: BetRecommendation = BetRecommendation.NEUTRAL

    @property
    def is_value(self) -> bool:
        return self.edge > 0.05 and self.expected_value > 0

    @property
    def rating_stars(self) -> int:
        """Рейтинг от 1 до 5 звезд"""
        if self.edge > 0.20:
            return 5
        elif self.edge > 0.15:
            return 4
        elif self.edge > 0.10:
            return 3
        elif self.edge > 0.05:
            return 2
        return 1


@dataclass
class ModelContribution:
    """Вклад каждой модели в итоговый прогноз"""
    model_name: str
    weight: float
    probabilities: ProbabilityDistribution
    confidence: float


@dataclass
class MatchPrediction:
    """Полный прогноз матча"""
    match_id: int
    generated_at: datetime = field(default_factory=datetime.now)

    # Вероятности от разных моделей
    elo_probabilities: Optional[ProbabilityDistribution] = None
    xg_probabilities: Optional[ProbabilityDistribution] = None
    form_probabilities: Optional[ProbabilityDistribution] = None
    ensemble_probabilities: ProbabilityDistribution = field(default_factory=ProbabilityDistribution)

    # Вклад моделей
    model_contributions: List[ModelContribution] = field(default_factory=list)

    # Value-ставки
    value_bets: List[ValueBet] = field(default_factory=list)

    # Метрики
    home_advantage_factor: float = 1.0
    form_factor: float = 1.0
    injury_impact: float = 0.0

    # Итоговая рекомендация
    top_recommendation: Optional[ValueBet] = None

    # Качество прогноза
    prediction_strength: float = 0.0  # 0-100
    data_quality_score: float = 0.0  # Насколько полные данные

    def get_best_value_bet(self) -> Optional[ValueBet]:
        """Получить лучшую value-ставку"""
        if not self.value_bets:
            return None
        return max(self.value_bets, key=lambda x: x.expected_value)

    def get_all_value_bets(self, min_edge: float = 0.05) -> List[ValueBet]:
        """Получить все ставки с положительным value"""
        return [vb for vb in self.value_bets if vb.edge >= min_edge]

    def to_dict(self) -> Dict:
        """Сериализация в словарь"""
        return {
            "match_id": self.match_id,
            "generated_at": self.generated_at.isoformat(),
            "ensemble_probabilities": {
                "home_win": round(self.ensemble_probabilities.home_win, 3),
                "draw": round(self.ensemble_probabilities.draw, 3),
                "away_win": round(self.ensemble_probabilities.away_win, 3),
            },
            "value_bets": [
                {
                    "market": vb.market,
                    "selection": vb.selection,
                    "model_prob": round(vb.model_probability, 3),
                    "market_prob": round(vb.market_probability, 3),
                    "odds": vb.implied_odds,
                    "edge": round(vb.edge, 3),
                    "ev": round(vb.expected_value, 3),
                    "kelly": round(vb.kelly_bet_size, 2),
                    "confidence": round(vb.confidence, 2),
                    "stars": vb.rating_stars,
                    "recommendation": vb.recommendation.value
                }
                for vb in self.value_bets
            ],
            "prediction_strength": round(self.prediction_strength, 1),
            "data_quality": round(self.data_quality_score, 1)
        }
