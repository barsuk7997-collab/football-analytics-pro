"""
Поиск value-ставок и расчёт Kelly Criterion
"""
import math
from typing import List, Optional, Dict
from dataclasses import dataclass

from models.match import Match, MatchOdds
from models.prediction import (
    ValueBet, BetRecommendation, 
    ProbabilityDistribution, MatchPrediction
)
from config.settings import model_config


class ValueFinder:
    """
    Детектор value-ставок

    Основная логика:
    1. Сравнение модельной вероятности с рыночной
    2. Расчёт edge и expected value
    3. Kelly Criterion для размера ставки
    4. Фильтрация по порогам уверенности
    """

    def __init__(self):
        self.min_edge = model_config.MIN_VALUE_EDGE
        self.max_edge = model_config.MAX_VALUE_EDGE
        self.min_odds = model_config.MIN_ODDS
        self.max_odds = model_config.MAX_ODDS
        self.kelly_fraction = model_config.KELLY_FRACTION

    def find_value_bets(
        self,
        match: Match,
        model_probs: ProbabilityDistribution,
        confidence: float
    ) -> List[ValueBet]:
        """
        Найти все value-ставки в матче

        Args:
            match: Матч с коэффициентами
            model_probs: Вероятности от ансамблевой модели
            confidence: Уверенность прогноза (0-1)
        """
        value_bets = []

        # Получаем лучшие коэффициенты
        best_odds = match.best_odds
        if not best_odds:
            return value_bets

        # Рынок 1X2
        markets_1x2 = [
            ("home_win", model_probs.home_win, best_odds.home_win),
            ("draw", model_probs.draw, best_odds.draw),
            ("away_win", model_probs.away_win, best_odds.away_win),
        ]

        for selection, prob, odds in markets_1x2:
            vb = self._analyze_market(
                market="1X2",
                selection=selection,
                model_prob=prob,
                odds=odds,
                confidence=confidence
            )
            if vb:
                value_bets.append(vb)

        # Тоталы
        if model_probs.over_2_5 and best_odds.over_2_5:
            vb = self._analyze_market(
                market="OVER_UNDER_2_5",
                selection="over_2_5",
                model_prob=model_probs.over_2_5,
                odds=best_odds.over_2_5,
                confidence=confidence
            )
            if vb: value_bets.append(vb)

        if model_probs.under_2_5 and best_odds.under_2_5:
            vb = self._analyze_market(
                market="OVER_UNDER_2_5",
                selection="under_2_5",
                model_prob=model_probs.under_2_5,
                odds=best_odds.under_2_5,
                confidence=confidence
            )
            if vb: value_bets.append(vb)

        # Сортируем по expected value
        value_bets.sort(key=lambda x: x.expected_value, reverse=True)
        return value_bets

    def _analyze_market(
        self,
        market: str,
        selection: str,
        model_prob: float,
        odds: float,
        confidence: float
    ) -> Optional[ValueBet]:
        """
        Анализ конкретного рынка на наличие value
        """
        # Фильтр коэффициентов
        if not (self.min_odds <= odds <= self.max_odds):
            return None

        # Рыночная вероятность (с учётом маржи)
        market_prob = 1 / odds

        # Edge = (model_prob - market_prob) / market_prob
        edge = (model_prob - market_prob) / market_prob if market_prob > 0 else 0

        # Expected Value = (model_prob * odds) - 1
        ev = model_prob * odds - 1

        # Проверка порогов
        if edge < self.min_edge or ev <= 0:
            return None

        # Kelly Criterion: f* = (bp - q) / b
        # где b = odds - 1, p = model_prob, q = 1 - p
        b = odds - 1
        p = model_prob
        q = 1 - p

        kelly_full = (b * p - q) / b if b > 0 else 0
        kelly_fraction = max(0, kelly_full * self.kelly_fraction)

        # Ограничения Kelly
        kelly_bet = max(
            model_config.MIN_KELLY_BET,
            min(kelly_fraction, model_config.MAX_KELLY_BET)
        )

        # Рекомендация
        if edge > 0.20 and confidence > 0.75:
            rec = BetRecommendation.STRONG_BUY
        elif edge > 0.10 and confidence > 0.60:
            rec = BetRecommendation.BUY
        elif edge > 0.05:
            rec = BetRecommendation.NEUTRAL
        else:
            rec = BetRecommendation.AVOID

        # Согласие моделей (будет заполнено позже)
        model_agreement = confidence

        return ValueBet(
            market=market,
            selection=selection,
            model_probability=model_prob,
            market_probability=market_prob,
            implied_odds=odds,
            edge=edge,
            expected_value=ev,
            kelly_fraction=kelly_fraction,
            kelly_bet_size=kelly_bet,
            confidence=confidence,
            model_agreement=model_agreement,
            recommendation=rec
        )

    def get_kelly_bet_size(
        self,
        bankroll: float,
        value_bet: ValueBet
    ) -> float:
        """
        Рассчитать размер ставки в валюте

        Args:
            bankroll: Текущий банкролл
            value_bet: Value-ставка с Kelly fraction
        """
        return bankroll * value_bet.kelly_bet_size
