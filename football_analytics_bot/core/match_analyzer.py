"""
Главный анализатор: объединяет все модели в единый прогноз
"""
from typing import Optional, Dict, List
from datetime import datetime

from models.team import Team, TeamForm
from models.match import Match
from models.prediction import (
    MatchPrediction, ProbabilityDistribution, 
    ModelContribution, ValueBet
)
from core.elo_engine import EloEngine
from core.form_calculator import FormCalculator
from core.probability_model import PoissonXGModel
from core.value_finder import ValueFinder
from database import db


class MatchAnalyzer:
    """
    Центральный анализатор матчей

    Pipeline:
    1. Загрузка данных команд из БД
    2. Расчёт Elo вероятностей
    3. Расчёт xG/Poisson вероятностей
    4. Расчёт формы
    5. Ансамблевое взвешивание
    6. Поиск value-ставок
    7. Сохранение в БД
    """

    def __init__(self):
        self.elo_engine = EloEngine()
        self.form_calc = FormCalculator()
        self.xg_model = PoissonXGModel()
        self.value_finder = ValueFinder()

        # Веса моделей в ансамбле
        self.model_weights = {
            "elo": 0.40,      # Elo - самая стабильная
            "xg": 0.30,       # xG/Poisson - для тоталов
            "form": 0.20,     # Форма - краткосрочный тренд
            "market": 0.10    # Рынок (если доступен)
        }

    def analyze_match(
        self,
        match: Match,
        home_team: Team = None,
        away_team: Team = None,
        use_db: bool = True
    ) -> MatchPrediction:
        """
        Полный анализ матча

        Args:
            match: Объект матча
            home_team: Данные хозяев (опционально, загрузятся из БД)
            away_team: Данные гостей (опционально, загрузятся из БД)
            use_db: Использовать ли БД для загрузки/сохранения
        """
        prediction = MatchPrediction(match_id=match.match_id)

        # Загружаем команды из БД если не предоставлены
        if use_db and not home_team:
            home_data = db.get_team(match.home_team_id)
            if home_data:
                home_team = self._db_team_to_model(home_data)
            else:
                home_team = Team(team_id=match.home_team_id, name=match.home_team_name)

        if use_db and not away_team:
            away_data = db.get_team(match.away_team_id)
            if away_data:
                away_team = self._db_team_to_model(away_data)
            else:
                away_team = Team(team_id=match.away_team_id, name=match.away_team_name)

        # Загружаем форму из истории матчей
        if use_db:
            home_matches = db.get_last_matches(match.home_team_id, limit=10)
            away_matches = db.get_last_matches(match.away_team_id, limit=10)

            home_team.current_form = self.form_calc.calculate_form(
                home_matches, match.home_team_id, {}
            )
            away_team.current_form = self.form_calc.calculate_form(
                away_matches, match.away_team_id, {}
            )

        # 1. Elo вероятности
        elo_probs = self._get_elo_probabilities(home_team, away_team, match.league_id)
        prediction.elo_probabilities = elo_probs

        # 2. xG/Poisson вероятности
        xg_probs = self._get_xg_probabilities(home_team, away_team, match.league_id)
        prediction.xg_probabilities = xg_probs

        # 3. Форма-вероятности
        form_probs = self._get_form_probabilities(home_team, away_team)
        prediction.form_probabilities = form_probs

        # 4. Ансамблевое взвешивание
        ensemble = self._ensemble_probabilities(
            elo_probs, xg_probs, form_probs, match
        )
        prediction.ensemble_probabilities = ensemble

        # 5. Оценка качества данных
        prediction.data_quality_score = self._assess_data_quality(
            match, home_team, away_team
        )

        # 6. Уверенность прогноза
        confidence = self._calculate_confidence(
            elo_probs, xg_probs, form_probs, prediction.data_quality_score
        )
        prediction.prediction_strength = confidence * 100

        # 7. Поиск value-ставок
        prediction.value_bets = self.value_finder.find_value_bets(
            match, ensemble, confidence
        )

        # 8. Лучшая рекомендация
        if prediction.value_bets:
            prediction.top_recommendation = prediction.get_best_value_bet()

        # Сохраняем вклады моделей
        prediction.model_contributions = [
            ModelContribution("elo", self.model_weights["elo"], elo_probs, 0.85),
            ModelContribution("xg", self.model_weights["xg"], xg_probs, 0.75),
            ModelContribution("form", self.model_weights["form"], form_probs, 0.70),
        ]

        # Сохраняем в БД
        if use_db:
            pred_dict = prediction.to_dict()
            pred_dict["home_team"] = match.home_team_name
            pred_dict["away_team"] = match.away_team_name
            pred_dict["league_name"] = str(match.league_id)
            pred_dict["match_date"] = match.match_date
            pred_dict["prob_over25"] = ensemble.over_2_5 or 0
            pred_dict["prob_under25"] = ensemble.under_2_5 or 0
            db.save_prediction(pred_dict)

        return prediction

    def _get_elo_probabilities(
        self,
        home_team: Team,
        away_team: Team,
        league_id: int
    ) -> ProbabilityDistribution:
        """Вероятности от Elo модели"""
        p_home, p_draw, p_away = self.elo_engine.ensemble_probability(
            home_team, away_team, league_id
        )
        return ProbabilityDistribution(
            home_win=p_home, draw=p_draw, away_win=p_away
        )

    def _get_xg_probabilities(
        self,
        home_team: Team,
        away_team: Team,
        league_id: int
    ) -> ProbabilityDistribution:
        """Вероятности от xG/Poisson модели"""
        try:
            lambda_h, lambda_a = self.xg_model.calculate_expected_goals(
                home_team, away_team, league_id
            )

            p_home, p_draw, p_away = self.xg_model.get_1x2_probabilities(
                lambda_h, lambda_a
            )

            p_over, p_under = self.xg_model.get_total_probabilities(
                lambda_h, lambda_a, 2.5
            )

            p_btts, p_btts_no = self.xg_model.get_btts_probability(
                lambda_h, lambda_a
            )

            return ProbabilityDistribution(
                home_win=p_home, draw=p_draw, away_win=p_away,
                over_2_5=p_over, under_2_5=p_under,
                btts_yes=p_btts, btts_no=p_btts_no
            )
        except Exception:
            # Fallback на Elo если xG недоступен
            return self._get_elo_probabilities(home_team, away_team, league_id)

    def _get_form_probabilities(
        self,
        home_team: Team,
        away_team: Team
    ) -> ProbabilityDistribution:
        """Вероятности на основе формы"""
        h_form = home_team.current_form.form_rating
        a_form = away_team.current_form.form_rating

        # Нормализация в вероятности
        total = h_form + a_form + 50  # +50 для ничьей
        p_home = h_form / total
        p_away = a_form / total
        p_draw = 1 - p_home - p_away

        return ProbabilityDistribution(
            home_win=max(0, p_home),
            draw=max(0, p_draw),
            away_win=max(0, p_away)
        )

    def _ensemble_probabilities(
        self,
        elo: ProbabilityDistribution,
        xg: ProbabilityDistribution,
        form: ProbabilityDistribution,
        match: Match
    ) -> ProbabilityDistribution:
        """Ансамблевое взвешивание вероятностей"""
        w = self.model_weights

        p_home = (
            elo.home_win * w["elo"] +
            xg.home_win * w["xg"] +
            form.home_win * w["form"]
        )

        p_draw = (
            elo.draw * w["elo"] +
            xg.draw * w["xg"] +
            form.draw * w["form"]
        )

        p_away = (
            elo.away_win * w["elo"] +
            xg.away_win * w["xg"] +
            form.away_win * w["form"]
        )

        # Инкорпорируем рыночную информацию если доступна
        if match.odds:
            market = match.average_odds
            if market:
                m_probs = market.implied_probs
                p_home = p_home * 0.90 + m_probs[0] * 0.10
                p_draw = p_draw * 0.90 + m_probs[1] * 0.10
                p_away = p_away * 0.90 + m_probs[2] * 0.10

        # Нормализация
        total = p_home + p_draw + p_away

        return ProbabilityDistribution(
            home_win=p_home/total,
            draw=p_draw/total,
            away_win=p_away/total,
            over_2_5=xg.over_2_5,
            under_2_5=xg.under_2_5,
            btts_yes=xg.btts_yes,
            btts_no=xg.btts_no
        )

    def _assess_data_quality(
        self,
        match: Match,
        home_team: Team,
        away_team: Team
    ) -> float:
        """Оценка полноты данных (0-100)"""
        score = 100

        checks = [
            (home_team.elo.get_rating(32) != 1500, 15),
            (away_team.elo.get_rating(32) != 1500, 15),
            (home_team.current_form.matches_played >= 3, 10),
            (away_team.current_form.matches_played >= 3, 10),
            (len(match.odds) > 0, 15),
            (match.home_lineup or match.away_lineup, 10),
            (home_team.injuries.total_injured >= 0, 5),
        ]

        for condition, penalty in checks:
            if not condition:
                score -= penalty

        return max(0, score)

    def _calculate_confidence(
        self,
        elo: ProbabilityDistribution,
        xg: ProbabilityDistribution,
        form: ProbabilityDistribution,
        data_quality: float
    ) -> float:
        """Рассчитать уверенность в прогнозе"""
        # Согласие моделей
        home_diff = abs(elo.home_win - xg.home_win) + abs(elo.home_win - form.home_win)
        draw_diff = abs(elo.draw - xg.draw) + abs(elo.draw - form.draw)
        away_diff = abs(elo.away_win - xg.away_win) + abs(elo.away_win - form.away_win)

        avg_diff = (home_diff + draw_diff + away_diff) / 6
        agreement = max(0, 1 - avg_diff * 2)

        # Сила предсказания
        probs = [elo.home_win, elo.draw, elo.away_win]
        max_prob = max(probs)
        clarity = (max_prob - 0.33) / 0.67

        confidence = (
            agreement * 0.4 +
            (data_quality / 100) * 0.3 +
            clarity * 0.3
        )

        return min(1.0, max(0, confidence))

    def _db_team_to_model(self, db_team: Dict) -> Team:
        """Конвертировать данные из БД в модель Team"""
        from models.team import TeamElo

        team = Team(
            team_id=db_team["team_id"],
            name=db_team["name"],
            country=db_team.get("country", "")
        )
        team.elo = TeamElo(ratings=db_team.get("elo", {}))
        return team


# Синглтон
analyzer = MatchAnalyzer()
