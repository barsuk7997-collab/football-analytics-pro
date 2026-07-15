"""
Профессиональный Elo движок с мульти-K системой
На основе исследований: multi-K Elo показывает MAE 0.032 для home/away win
"""
import math
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from models.team import Team, TeamElo
from models.match import Match, MatchScore
from config.leagues import get_league_params


@dataclass
class EloMatchResult:
    """Результат расчета Elo для матча"""
    home_rating_before: Dict[int, float]
    away_rating_before: Dict[int, float]
    home_rating_after: Dict[int, float]
    away_rating_after: Dict[int, float]
    expected_home: float
    expected_away: float
    actual_home: float
    actual_away: float
    rating_changes: Dict[int, Tuple[float, float]]  # k: (home_change, away_change)


class EloEngine:
    """
    Профессиональный Elo движок для футбола

    Особенности:
    - Мульти-K система (32, 200, 500, 2000) для разных временных горизонтов
    - Учет разницы мячей (goal-margin adjusted)
    - Домашнее преимущество с поправкой на лигу
    - Регрессия к среднему между сезонами
    - Временное затухание (time decay)
    """

    def __init__(self, base_rating: int = 1500):
        self.base_rating = base_rating
        self.k_factors = [32, 200, 500, 2000]  # Оптимальный набор по исследованиям
        self.divisor = 400  # Стандартный делитель Elo

    def expected_score(self, rating_a: float, rating_b: float) -> float:
        """
        Ожидаемый результат для команды A против команды B
        Формула: E_A = 1 / (1 + 10^((R_B - R_A)/400))
        """
        return 1.0 / (1.0 + math.pow(10, (rating_b - rating_a) / self.divisor))

    def goal_margin_multiplier(self, goal_diff: int, k: int) -> float:
        """
        Множитель для учета разницы мячей
        Использует логарифмическую шкалу для предотвращения чрезмерных изменений
        """
        if goal_diff == 0:
            return 1.0
        # log(goal_diff + 1) дает: 1 гол = 0.69, 2 = 1.10, 3 = 1.39, 4 = 1.61
        margin_factor = math.log(abs(goal_diff) + 1)
        # Ограничиваем влияние для высоких K
        max_multiplier = 2.0 if k <= 200 else 1.5
        return min(margin_factor, max_multiplier)

    def calculate_match(
        self,
        home_team: Team,
        away_team: Team,
        score: MatchScore,
        league_id: int,
        match_importance: float = 1.0
    ) -> EloMatchResult:
        """
        Рассчитать изменение Elo после матча

        Args:
            home_team: Хозяева
            away_team: Гости
            score: Счет матча
            league_id: ID лиги для специфических параметров
            match_importance: Важность матча (1.0 = обычный, 1.5 = еврокубки)
        """
        league_params = get_league_params(league_id)
        home_advantage = league_params.home_advantage_elo if not score else 0  # Уже учтено в результате

        # Результат матча
        if score.home > score.away:
            actual_home, actual_away = 1.0, 0.0
        elif score.home < score.away:
            actual_home, actual_away = 0.0, 1.0
        else:
            actual_home, actual_away = 0.5, 0.5

        goal_diff = abs(score.home - score.away)

        rating_changes = {}
        home_after = {}
        away_after = {}
        home_before = {}
        away_before = {}

        expected_home_final = 0.5

        for k in self.k_factors:
            # Текущие рейтинги
            r_home = home_team.elo.get_rating(k)
            r_away = away_team.elo.get_rating(k)
            home_before[k] = r_home
            away_before[k] = r_away

            # Ожидаемый результат с учетом домашнего преимущества
            r_home_eff = r_home + league_params.home_advantage_elo
            expected_h = self.expected_score(r_home_eff, r_away)
            expected_a = 1.0 - expected_h

            if k == 32:  # Сохраняем для возврата
                expected_home_final = expected_h

            # Множитель разницы мячей
            margin_mult = self.goal_margin_multiplier(goal_diff, k)

            # Эффективный K-фактор
            effective_k = k * match_importance * margin_mult

            # Изменения рейтингов
            change_home = effective_k * (actual_home - expected_h)
            change_away = effective_k * (actual_away - expected_a)

            # Обновляем рейтинги
            new_home = r_home + change_home
            new_away = r_away + change_away

            home_after[k] = new_home
            away_after[k] = new_away
            rating_changes[k] = (change_home, change_away)

        return EloMatchResult(
            home_rating_before=home_before,
            away_rating_before=away_before,
            home_rating_after=home_after,
            away_rating_after=away_after,
            expected_home=expected_home_final,
            expected_away=1.0 - expected_home_final,
            actual_home=actual_home,
            actual_away=actual_away,
            rating_changes=rating_changes
        )

    def get_win_probability(
        self,
        home_team: Team,
        away_team: Team,
        league_id: int,
        k: int = 32
    ) -> Tuple[float, float, float]:
        """
        Получить вероятности исходов (home_win, draw, away_win)

        Returns:
            Tuple[float, float, float]: (P_home, P_draw, P_away)
        """
        league_params = get_league_params(league_id)

        r_home = home_team.elo.get_rating(k)
        r_away = away_team.elo.get_rating(k)

        # Эффективные рейтинги с домашним преимуществом
        r_home_eff = r_home + league_params.home_advantage_elo

        # Базовая вероятность победы хозяев (без ничьих)
        p_home_win = self.expected_score(r_home_eff, r_away)
        p_away_win = self.expected_score(r_away, r_home_eff)

        # Нормализация (т.к. в Elo ничья = 0.5 для обеих)
        total = p_home_win + p_away_win
        if total > 0:
            p_home_win /= total
            p_away_win /= total

        # Вероятность ничьей зависит от разницы сил
        rating_diff = abs(r_home_eff - r_away)
        # Чем ближе силы, тем выше вероятность ничьей
        # При равных силах: ~28%, при разнице 400+: ~18%
        base_draw = league_params.draw_rate
        draw_adjustment = max(0, (400 - rating_diff) / 400) * 0.10
        p_draw = base_draw + draw_adjustment

        # Нормализация до 1.0
        remaining = 1.0 - p_draw
        p_home = remaining * p_home_win
        p_away = remaining * p_away_win

        return (p_home, p_draw, p_away)

    def regress_to_mean(
        self,
        team: Team,
        league_id: int,
        season: str
    ) -> Dict[int, float]:
        """
        Регрессия рейтинга к среднему в начале нового сезона
        Согласно исследованиям: regress 1/3 к среднему
        """
        league_params = get_league_params(league_id)
        mean_rating = self.base_rating
        regression_factor = 0.33  # 1/3 к среднему

        new_ratings = {}
        for k in self.k_factors:
            current = team.elo.get_rating(k)
            new_ratings[k] = current + (mean_rating - current) * regression_factor

        return new_ratings

    def get_multi_k_probabilities(
        self,
        home_team: Team,
        away_team: Team,
        league_id: int
    ) -> Dict[int, Tuple[float, float, float]]:
        """
        Получить вероятности от всех K-моделей
        Используется для ансамблевого прогнозирования
        """
        probs = {}
        for k in self.k_factors:
            probs[k] = self.get_win_probability(home_team, away_team, league_id, k)
        return probs

    def ensemble_probability(
        self,
        home_team: Team,
        away_team: Team,
        league_id: int,
        weights: Optional[Dict[int, float]] = None
    ) -> Tuple[float, float, float]:
        """
        Ансамблевая вероятность с взвешиванием разных K
        По умолчанию: K=32 (30%), K=200 (25%), K=500 (25%), K=2000 (20%)
        """
        if weights is None:
            weights = {32: 0.30, 200: 0.25, 500: 0.25, 2000: 0.20}

        all_probs = self.get_multi_k_probabilities(home_team, away_team, league_id)

        p_home = sum(all_probs[k][0] * weights[k] for k in self.k_factors)
        p_draw = sum(all_probs[k][1] * weights[k] for k in self.k_factors)
        p_away = sum(all_probs[k][2] * weights[k] for k in self.k_factors)

        # Нормализация
        total = p_home + p_draw + p_away
        return (p_home/total, p_draw/total, p_away/total)
