"""
Вероятностная модель на основе Poisson распределения и xG
Для рынков: тоталы, обе забьют, точный счёт
"""
import math
from typing import Dict, Tuple, List
from scipy.stats import poisson

from models.team import Team
from config.leagues import get_league_params


class PoissonXGModel:
    """
    Модель на основе ожидаемых голов (xG)

    Рассчитывает:
    - Ожидаемое количество голов каждой команды
    - Вероятности точного счёта
    - Вероятности тоталов и BTTS
    """

    def __init__(self):
        self.league_avg_goals_home = 1.50
        self.league_avg_goals_away = 1.15

    def calculate_expected_goals(
        self,
        home_team: Team,
        away_team: Team,
        league_id: int
    ) -> Tuple[float, float]:
        """
        Рассчитать ожидаемое количество голов

        Формула: 
        λ_home = (home_attack × away_defense × league_avg_home) / league_avg
        λ_away = (away_attack × home_defense × league_avg_away) / league_avg
        """
        league = get_league_params(league_id)

        # Сила атаки и обороны (нормализованные)
        home_attack = self._get_attack_strength(home_team, "home")
        home_defense = self._get_defense_strength(home_team, "home")
        away_attack = self._get_attack_strength(away_team, "away")
        away_defense = self._get_defense_strength(away_team, "away")

        # Ожидаемые голы
        lambda_home = home_attack * away_defense * league.avg_goals_home
        lambda_away = away_attack * home_defense * league.avg_goals_away

        # Корректировки
        lambda_home *= self._form_adjustment(home_team)
        lambda_away *= self._form_adjustment(away_team)

        # Корректировка на травмы
        lambda_home *= (1 - home_team.injuries.impact_score * 0.15)
        lambda_away *= (1 - away_team.injuries.impact_score * 0.15)

        return (max(0.3, lambda_home), max(0.3, lambda_away))

    def _get_attack_strength(self, team: Team, venue: str) -> float:
        """Сила атаки команды (1.0 = средняя по лиге)"""
        stats = team.season_stats
        if venue == "home" and stats.home_played > 0:
            raw = stats.home_goals_for / stats.home_played
        elif stats.away_played > 0:
            raw = stats.away_goals_for / stats.away_played
        else:
            raw = stats.goals_for / max(stats.played, 1)

        if raw == 0:
            return 1.0
        return raw / self.league_avg_goals_home

    def _get_defense_strength(self, team: Team, venue: str) -> float:
        """Сила обороны (1.0 = средняя, <1 = сильная оборона)"""
        stats = team.season_stats
        if venue == "home" and stats.home_played > 0:
            raw = stats.home_goals_against / stats.home_played
        elif stats.away_played > 0:
            raw = stats.away_goals_against / stats.away_played
        else:
            raw = stats.goals_against / max(stats.played, 1)

        if raw == 0:
            return 1.0
        # Нормализация (меньше пропущено = сильнее, поэтому инверсия)
        return self.league_avg_goals_away / max(raw, 0.5)

    def _form_adjustment(self, team: Team) -> float:
        """Корректировка на текущую форму (0.8-1.2)"""
        form_rating = team.current_form.form_rating
        return 0.8 + (form_rating / 100) * 0.4

    def get_score_probabilities(
        self,
        lambda_home: float,
        lambda_away: float,
        max_goals: int = 6
    ) -> Dict[Tuple[int, int], float]:
        """
        Матрица вероятностей точного счёта

        Returns:
            {(home_goals, away_goals): probability}
        """
        probs = {}
        for h in range(max_goals + 1):
            for a in range(max_goals + 1):
                p = poisson.pmf(h, lambda_home) * poisson.pmf(a, lambda_away)
                probs[(h, a)] = p
        return probs

    def get_1x2_probabilities(
        self,
        lambda_home: float,
        lambda_away: float
    ) -> Tuple[float, float, float]:
        """Вероятности 1X2 из Poisson модели"""
        score_probs = self.get_score_probabilities(lambda_home, lambda_away)

        p_home = sum(p for (h, a), p in score_probs.items() if h > a)
        p_draw = sum(p for (h, a), p in score_probs.items() if h == a)
        p_away = sum(p for (h, a), p in score_probs.items() if h < a)

        return (p_home, p_draw, p_away)

    def get_total_probabilities(
        self,
        lambda_home: float,
        lambda_away: float,
        line: float = 2.5
    ) -> Tuple[float, float]:
        """Вероятности тотала больше/меньше"""
        score_probs = self.get_score_probabilities(lambda_home, lambda_away)

        p_over = sum(p for (h, a), p in score_probs.items() if h + a > line)
        p_under = 1 - p_over

        return (p_over, p_under)

    def get_btts_probability(
        self,
        lambda_home: float,
        lambda_away: float
    ) -> Tuple[float, float]:
        """Вероятности обе забьют да/нет"""
        p_home_scores = 1 - poisson.pmf(0, lambda_home)
        p_away_scores = 1 - poisson.pmf(0, lambda_away)

        p_btts = p_home_scores * p_away_scores
        return (p_btts, 1 - p_btts)
