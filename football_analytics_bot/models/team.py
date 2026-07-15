"""
Модель футбольной команды с полной статистикой
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime


@dataclass
class TeamForm:
    """Форма команды за последние N матчей"""
    matches_played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_scored: int = 0
    goals_conceded: int = 0
    xg_scored: float = 0.0
    xg_conceded: float = 0.0
    form_points: float = 0.0  # Взвешенные очки (3 за победу, 1 за ничью)
    form_rating: float = 0.0  # 0-100
    last_5_results: List[str] = field(default_factory=list)  # ['W', 'D', 'L', 'W', 'W']

    @property
    def goal_difference(self) -> int:
        return self.goals_scored - self.goals_conceded

    @property
    def points_per_game(self) -> float:
        return self.form_points / max(self.matches_played, 1)

    @property
    def win_rate(self) -> float:
        return self.wins / max(self.matches_played, 1)


@dataclass
class TeamInjuries:
    """Информация о травмах и дисквалификациях"""
    total_injured: int = 0
    key_players_injured: int = 0  # Игроки с рейтингом > 80
    injured_players: List[Dict] = field(default_factory=list)
    suspension_count: int = 0

    @property
    def impact_score(self) -> float:
        """Оценка влияния травм (0-1)"""
        if self.total_injured == 0:
            return 0.0
        return min(1.0, (self.key_players_injured * 0.3 + self.total_injured * 0.1))


@dataclass
class TeamElo:
    """Elo рейтинги команды (мульти-K система)"""
    ratings: Dict[int, float] = field(default_factory=dict)  # {K: rating}
    last_updated: Optional[datetime] = None

    def get_rating(self, k: int = 32) -> float:
        return self.ratings.get(k, 1500.0)

    def update_rating(self, k: int, new_rating: float):
        self.ratings[k] = new_rating
        self.last_updated = datetime.now()


@dataclass
class TeamSeasonStats:
    """Сезонная статистика команды"""
    season: str = ""
    league_id: int = 0

    # Общая статистика
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0

    # Дома / В гостях
    home_played: int = 0
    home_wins: int = 0
    home_goals_for: int = 0
    home_goals_against: int = 0

    away_played: int = 0
    away_wins: int = 0
    away_goals_for: int = 0
    away_goals_against: int = 0

    # xG
    xg_for: float = 0.0
    xg_against: float = 0.0

    @property
    def points(self) -> int:
        return self.wins * 3 + self.draws

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def ppg(self) -> float:
        return self.points / max(self.played, 1)

    @property
    def home_ppg(self) -> float:
        home_points = self.home_wins * 3 + (self.home_played - self.home_wins - 
                      (self.home_played - self.home_wins - self.home_goals_for))  # упрощенно
        return home_points / max(self.home_played, 1)


@dataclass
class Team:
    """Полная модель футбольной команды"""
    team_id: int
    name: str
    country: str = ""
    founded: int = 0
    logo_url: str = ""

    # Рейтинги и статистика
    elo: TeamElo = field(default_factory=TeamElo)
    current_form: TeamForm = field(default_factory=TeamForm)
    season_stats: TeamSeasonStats = field(default_factory=TeamSeasonStats)
    injuries: TeamInjuries = field(default_factory=TeamInjuries)

    # История
    last_matches: List[Dict] = field(default_factory=list)
    head_to_head: Dict[int, List[Dict]] = field(default_factory=dict)  # {opponent_id: matches}

    # Состав
    squad: List[Dict] = field(default_factory=list)
    key_players: List[int] = field(default_factory=list)  # player_ids

    @property
    def overall_strength(self) -> float:
        """Общая сила команды (0-100)"""
        elo_component = min(100, max(0, (self.elo.get_rating(32) - 1300) / 10))
        form_component = self.current_form.form_rating
        injury_penalty = self.injuries.impact_score * 20

        return max(0, min(100, elo_component * 0.5 + form_component * 0.4 - injury_penalty * 0.1))

    def get_h2h_record(self, opponent_id: int, last_n: int = 5) -> Dict:
        """Получить историю встреч с соперником"""
        matches = self.head_to_head.get(opponent_id, [])
        recent = matches[-last_n:] if matches else []

        wins = sum(1 for m in recent if m.get('winner') == self.team_id)
        draws = sum(1 for m in recent if m.get('winner') is None)

        return {
            'played': len(recent),
            'wins': wins,
            'draws': draws,
            'losses': len(recent) - wins - draws,
            'goals_for': sum(m.get('goals_for', 0) for m in recent),
            'goals_against': sum(m.get('goals_against', 0) for m in recent)
        }
