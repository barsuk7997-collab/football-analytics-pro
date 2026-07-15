"""
Расчёт взвешенной формы команды с экспоненциальным затуханием
"""
import math
from typing import List, Dict
from datetime import datetime, timedelta

from models.team import TeamForm


class FormCalculator:
    """
    Калькулятор формы с учётом:
    - Экспоненциального затухания (новые матчи важнее)
    - Силы соперников (победа над сильным = больше очков)
    - Дома/в гостях раздельно
    - xG вместо реальных голов (если доступно)
    """

    def __init__(self, decay_factor: float = 0.85, matches_count: int = 5):
        self.decay = decay_factor
        self.matches_count = matches_count

    def calculate_form(
        self,
        matches: List[Dict],
        team_id: int,
        opponent_elos: Dict[int, float] = None
    ) -> TeamForm:
        """
        Рассчитать форму команды

        Args:
            matches: Последние матчи [{date, opponent_id, is_home, goals_for, 
                     goals_against, xg_for, xg_against, result}]
            team_id: ID команды
            opponent_elos: {opponent_id: elo_rating} для оценки силы соперников
        """
        form = TeamForm()
        weights = []
        opponent_elos = opponent_elos or {}

        # Сортируем по дате (новые первые)
        sorted_matches = sorted(matches, key=lambda x: x.get("date", ""), reverse=True)
        recent = sorted_matches[:self.matches_count]

        for i, match in enumerate(recent):
            # Вес с экспоненциальным затуханием
            weight = self.decay ** i
            weights.append(weight)

            # Определяем результат
            goals_for = match.get("goals_for", 0)
            goals_against = match.get("goals_against", 0)

            if goals_for > goals_against:
                result = "W"
                points = 3
                form.wins += 1
            elif goals_for == goals_against:
                result = "D"
                points = 1
                form.draws += 1
            else:
                result = "L"
                points = 0
                form.losses += 1

            form.last_5_results.append(result)
            form.matches_played += 1

            # Усиленные очки за победу над сильным соперником
            opponent_id = match.get("opponent_id", 0)
            opponent_elo = opponent_elos.get(opponent_id, 1500)
            strength_bonus = 1.0 + max(0, (opponent_elo - 1500) / 400) * 0.3

            weighted_points = points * weight * strength_bonus
            form.form_points += weighted_points

            # Голы (предпочитаем xG если доступен)
            gf = match.get("xg_for", goals_for)
            ga = match.get("xg_against", goals_against)
            form.goals_scored += gf * weight
            form.goals_conceded += ga * weight

        # Нормализованный рейтинг формы (0-100)
        if weights:
            max_possible = sum(3 * w for w in weights)
            form.form_rating = min(100, (form.form_points / max_possible) * 100)

        return form

    def get_home_away_split(
        self,
        matches: List[Dict],
        team_id: int
    ) -> Dict[str, TeamForm]:
        """Раздельная форма дома и в гостях"""
        home_matches = [m for m in matches if m.get("is_home", True)]
        away_matches = [m for m in matches if not m.get("is_home", True)]

        return {
            "home": self.calculate_form(home_matches, team_id, {}),
            "away": self.calculate_form(away_matches, team_id, {})
        }
