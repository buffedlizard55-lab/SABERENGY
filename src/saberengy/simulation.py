"""Schematic game-script sampler for the synthetic demo.

This is not the calibrated NFL model. That model is nfl_model.py and uses
public schedule and weekly counting stats. This file does not download
nflverse, nba_api, or MLB Stats API data, and it does not use DraftKings
Sportsbook odds.

SaberSim's public docs say their product simulates games play-by-play:
https://support.sabersim.com/en/articles/12078831-how-projections-work

This sampler does not do that. It draws a total, a home share, and a
per-team factor so a quarterback and his own receivers move together in
the demo. The factor is not a published SaberSim weight.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Tuple
import random
import math
import numpy as np
from collections import defaultdict

@dataclass
class PlayerOutcome:
    player_id: str
    player_name: str
    team: str
    position: str
    fantasy_points: float
    # Detailed stats (sport-specific)
    stats: Dict[str, float] = field(default_factory=dict)
    # For correlation tracking
    game_id: str = ""
    sim_index: int = 0

@dataclass
class GameScript:
    game_id: str
    sim_index: int
    home_team: str
    away_team: str
    home_score: float
    away_score: float
    # All player outcomes in this script
    player_outcomes: List[PlayerOutcome] = field(default_factory=list)
    # Game flow metadata
    total_plays: int = 0
    is_shootout: bool = False
    is_blowout: bool = False
    game_flow: str = ""  # e.g., "trailing_team_pass_heavy"

class Simulator:
    """Schematic sampler. Not play-by-play, and not a sportsbook fetch.

    vegas_total is whatever the caller passes. Same-team quarterback and
    receiver draws share a factor so the demo can show correlation. That
    factor is not a SaberSim weight.
    """

    def __init__(self, sport: str = "NFL", n_sims: int = 1000, seed: int = 42):
        self.sport = sport.upper()
        self.n_sims = n_sims
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)

    def run(self, slate: List[Dict]) -> List[GameScript]:
        """
        slate: list of games, each dict with:
        - game_id, home_team, away_team, players (list of dicts with id, name, team, pos, projection, std, etc.)
        - vegas_total, spread, etc. (optional)

        Returns: list of GameScript, len = len(slate) * n_sims
        """
        all_scripts = []
        for game in slate:
            scripts = self._simulate_game(game)
            all_scripts.extend(scripts)
        return all_scripts

    def _simulate_game(self, game: Dict) -> List[GameScript]:
        game_id = game.get("game_id", "unknown")
        home = game.get("home_team", "HOME")
        away = game.get("away_team", "AWAY")
        players = game.get("players", [])
        vegas_total = game.get("vegas_total", 45.0)
        # Sport-specific simulation
        if self.sport == "NFL":
            return self._simulate_nfl_game(game_id, home, away, players, vegas_total)
        elif self.sport == "NBA":
            return self._simulate_nba_game(game_id, home, away, players, vegas_total)
        elif self.sport == "MLB":
            return self._simulate_mlb_game(game_id, home, away, players, vegas_total)
        else:
            return self._simulate_generic_game(game_id, home, away, players, vegas_total)

    def _simulate_nfl_game(self, game_id, home, away, players, vegas_total):
        """NFL: model game script, pass volume rises when trailing."""
        scripts = []
        for sim_idx in range(self.n_sims):
            # Schematic environment. vegas_total is caller-supplied, not a sportsbook fetch.
            total_pts = max(10, np.random.normal(vegas_total, 10))
            # Home advantage
            home_share = np.random.normal(0.52, 0.08)  # home scores ~52% of points
            home_score = total_pts * home_share
            away_score = total_pts * (1 - home_share)

            # Determine game flow
            is_blowout = abs(home_score - away_score) > 14
            is_shootout = total_pts > vegas_total + 10
            if home_score > away_score + 7:
                flow = "home_leading_run_heavy"
            elif away_score > home_score + 7:
                flow = "away_leading_run_heavy"
            else:
                flow = "neutral_shootout" if is_shootout else "neutral"

            outcomes = []
            # One boom factor per team so a QB and his own WR/TE share a script.
            # This is a schematic, not the calibrated model in nfl_model.py.
            home_qb_factor = float(np.random.normal(1.0, 0.35))
            away_qb_factor = float(np.random.normal(1.0, 0.35))
            rb_game_script_factor = 1.2 if is_blowout else 0.9 if is_shootout else 1.0

            for p in players:
                base_proj = p.get("projection", 10.0)
                std = p.get("std", base_proj * 0.4)
                pos = p.get("position", "WR")
                team = p.get("team", home)
                team_qb_factor = home_qb_factor if team == home else away_qb_factor

                if pos == "QB":
                    fp = max(0, np.random.normal(base_proj * team_qb_factor, std * 0.7))
                elif pos in ("WR", "TE"):
                    fp = max(0, np.random.normal(base_proj * (0.6 + 0.4 * team_qb_factor), std))
                elif pos == "RB":
                    fp = max(0, np.random.normal(base_proj * rb_game_script_factor, std))
                else:
                    fp = max(0, np.random.normal(base_proj, std))

                outcomes.append(PlayerOutcome(
                    player_id=p.get("id", p.get("name", "unknown")),
                    player_name=p.get("name", "unknown"),
                    team=p.get("team", home),
                    position=pos,
                    fantasy_points=fp,
                    stats={"base": base_proj, "boom_factor": team_qb_factor if pos == "QB" else 1.0},
                    game_id=game_id,
                    sim_index=sim_idx
                ))

            scripts.append(GameScript(
                game_id=game_id,
                sim_index=sim_idx,
                home_team=home,
                away_team=away,
                home_score=home_score,
                away_score=away_score,
                player_outcomes=outcomes,
                total_plays=int(np.random.normal(125, 10)),
                is_shootout=is_shootout,
                is_blowout=is_blowout,
                game_flow=flow
            ))
        return scripts

    def _simulate_nba_game(self, game_id, home, away, players, vegas_total):
        """NBA: pace, usage, foul trouble, blowout risk."""
        scripts = []
        for sim_idx in range(self.n_sims):
            total_pts = max(150, np.random.normal(vegas_total if vegas_total>100 else 220, 15))
            home_share = np.random.normal(0.52, 0.05)
            home_score = total_pts * home_share
            away_score = total_pts * (1 - home_share)
            is_blowout = abs(home_score - away_score) > 20
            pace_factor = np.random.normal(1.0, 0.12)

            outcomes = []
            for p in players:
                base = p.get("projection", 30.0)
                std = p.get("std", base * 0.35)
                # Blowout reduces starters minutes
                minutes_factor = 0.75 if is_blowout and p.get("is_starter", True) else 1.0
                # Pace factor affects all
                fp = max(0, np.random.normal(base * pace_factor * minutes_factor, std))
                outcomes.append(PlayerOutcome(
                    player_id=p.get("id", p.get("name")),
                    player_name=p.get("name"),
                    team=p.get("team", home),
                    position=p.get("position", "G"),
                    fantasy_points=fp,
                    stats={"pace": pace_factor, "minutes_factor": minutes_factor},
                    game_id=game_id,
                    sim_index=sim_idx
                ))
            scripts.append(GameScript(
                game_id=game_id,
                sim_index=sim_idx,
                home_team=home,
                away_team=away,
                home_score=home_score,
                away_score=away_score,
                player_outcomes=outcomes,
                total_plays=int(np.random.normal(200, 15)),
                is_shootout=total_pts > 240,
                is_blowout=is_blowout,
                game_flow="blowout" if is_blowout else "pace_up" if pace_factor>1.1 else "pace_down" if pace_factor<0.9 else "neutral"
            ))
        return scripts

    def _simulate_mlb_game(self, game_id, home, away, players, vegas_total):
        """Schematic MLB draw. No park factors and no live rates."""
        scripts = []
        for sim_idx in range(self.n_sims):
            # MLB totals typically 7-11 runs
            total_runs = max(1, np.random.normal(vegas_total if vegas_total<20 else 9, 2.5))
            home_share = np.random.normal(0.52, 0.1)
            home_score = total_runs * home_share
            away_score = total_runs * (1 - home_share)

            # Pitcher factor: dominant pitcher suppresses opposing stack
            pitcher_dominance = np.random.choice([0.6, 0.8, 1.0, 1.2, 1.5], p=[0.1, 0.2, 0.4, 0.2, 0.1])

            outcomes = []
            # Determine if stack booms: if home scores lot, home hitters boom together
            home_stack_factor = home_score / (total_runs/2) if total_runs>0 else 1.0
            away_stack_factor = away_score / (total_runs/2) if total_runs>0 else 1.0

            for p in players:
                base = p.get("projection", 8.0)
                std = p.get("std", base * 0.8)  # MLB hitters high variance
                pos = p.get("position", "OF")
                team = p.get("team", home)

                if pos == "P":
                    fp = max(0, np.random.normal(base * pitcher_dominance, std * 0.5))
                else:
                    stack_factor = home_stack_factor if team == home else away_stack_factor
                    if team == home:
                        # If pitcher dominant for away, suppress home? Actually pitcher_dominance suppresses opposite
                        pass
                    # High variance
                    fp = max(0, np.random.normal(base * stack_factor, std))
                    # Add zero-inflation
                    if random.random() < 0.35:  # 35% chance bust to near 0
                        fp = max(0, np.random.normal(1.0, 1.5))

                outcomes.append(PlayerOutcome(
                    player_id=p.get("id", p.get("name")),
                    player_name=p.get("name"),
                    team=team,
                    position=pos,
                    fantasy_points=fp,
                    stats={"stack_factor": home_stack_factor if team==home else away_stack_factor, "pitcher_dom": pitcher_dominance},
                    game_id=game_id,
                    sim_index=sim_idx
                ))

            scripts.append(GameScript(
                game_id=game_id,
                sim_index=sim_idx,
                home_team=home,
                away_team=away,
                home_score=home_score,
                away_score=away_score,
                player_outcomes=outcomes,
                total_plays=int(total_runs * 6),  # approx plate appearances
                is_shootout=total_runs > 12,
                is_blowout=abs(home_score - away_score) > 5,
                game_flow="pitcher_dominant" if pitcher_dominance < 0.8 else "shootout" if total_runs>12 else "neutral"
            ))
        return scripts

    def _simulate_generic_game(self, game_id, home, away, players, vegas_total):
        scripts = []
        for sim_idx in range(self.n_sims):
            total = max(1, np.random.normal(vegas_total, vegas_total*0.2))
            home_score = total * 0.52
            away_score = total * 0.48
            outcomes = []
            for p in players:
                base = p.get("projection", 10.0)
                std = p.get("std", base*0.4)
                fp = max(0, np.random.normal(base, std))
                outcomes.append(PlayerOutcome(
                    player_id=p.get("id", p.get("name")),
                    player_name=p.get("name"),
                    team=p.get("team", home),
                    position=p.get("position", "P"),
                    fantasy_points=fp,
                    game_id=game_id,
                    sim_index=sim_idx
                ))
            scripts.append(GameScript(
                game_id=game_id, sim_index=sim_idx,
                home_team=home, away_team=away,
                home_score=home_score, away_score=away_score,
                player_outcomes=outcomes,
                is_shootout=False, is_blowout=False, game_flow="neutral"
            ))
        return scripts

    def compute_correlation_matrix(self, scripts: List[GameScript]) -> Dict[Tuple[str,str], float]:
        """
        Compute correlation between players based on co-occurrence in same sim.
        If QB and WR both boom in same sim, correlation high.
        Returns dict (player_id1, player_id2) -> correlation coefficient
        """
        # Group by game_id
        by_game = defaultdict(list)
        for s in scripts:
            by_game[s.game_id].append(s)

        corr = {}
        for game_id, game_scripts in by_game.items():
            # Build matrix: rows = sims, cols = players
            player_ids = list({p.player_id for script in game_scripts for p in script.player_outcomes})
            if len(player_ids) < 2:
                continue
            # Map player_id -> list of fantasy points across sims
            points_by_player = {pid: [] for pid in player_ids}
            for script in sorted(game_scripts, key=lambda x: x.sim_index):
                outcome_map = {p.player_id: p.fantasy_points for p in script.player_outcomes}
                for pid in player_ids:
                    points_by_player[pid].append(outcome_map.get(pid, 0.0))

            # Compute Pearson correlation for each pair
            for i, pid1 in enumerate(player_ids):
                for pid2 in player_ids[i+1:]:
                    x = np.array(points_by_player[pid1])
                    y = np.array(points_by_player[pid2])
                    if np.std(x) == 0 or np.std(y) == 0:
                        corr_val = 0.0
                    else:
                        corr_val = np.corrcoef(x, y)[0,1]
                        if math.isnan(corr_val):
                            corr_val = 0.0
                    corr[(pid1, pid2)] = float(corr_val)
                    corr[(pid2, pid1)] = float(corr_val)
        return corr
