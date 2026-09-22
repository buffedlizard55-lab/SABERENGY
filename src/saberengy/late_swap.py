"""
Late Swap — automatic resims when news breaks.

Verified from:
- https://support.sabersim.com/en/articles/12079563-using-late-swap
  "If you’re not late swapping, you’re betting on a frozen version of reality that no longer exists."
  "When this happens, SaberSim doesn’t just patch holes—it rewrites the story your lineups are betting on"
  "Quick Swap (Red Lightning Bolt): Ranking metric, Salary thresholds, Stack retention, Avoid opponents, Salary upgrades, Drop another player"
  "Notifications: Browser and mobile alerts when players in your entries are ruled out or projections swing sharply."
  "Automatic Resims: Every time projections or news update, SaberSim reruns its play-by-play sims"

This module does not poll a live injury feed. check_news() invents a random
OUT about 5% of the time so the swap function can be exercised. Do not treat
that as news.
"""

from typing import List, Dict, Callable
import time
import random

class LateSwapManager:
    def __init__(self, simulator, projection_engine_factory, ownership_model_factory):
        """
        simulator: Simulator instance
        projection_engine_factory: callable that returns ProjectionEngine from scripts
        ownership_model_factory: callable that returns OwnershipModel
        """
        self.simulator = simulator
        self.proj_factory = projection_engine_factory
        self.own_factory = ownership_model_factory
        self.is_live = False

    def check_news(self, slate: List[Dict], current_projections: Dict) -> Dict:
        """
        Does not poll an injury API. Returns a random OUT about 5% of the time.
        A real implementation would call:
        - NBA: https://stats.nba.com injury report
        - NFL: https://api.sportradar.com/nfl/official/.../injuries
        - MLB: https://statsapi.mlb.com/api/v1/teams/.../roster

        Here we simulate random news for demo.
        """
        # Simulate 5% chance of news per check
        changes = {}
        if random.random() < 0.05:
            # Pick random player to be OUT
            if current_projections:
                pid = random.choice(list(current_projections.keys()))
                changes[pid] = {"status": "OUT", "new_projection": 0, "reason": "Simulated injury news"}
        return changes

    def quick_swap(
        self,
        lineup: List[str],
        out_player_id: str,
        projections: Dict[str, Dict],
        ownership: Dict[str, float] = None,
        salary_cap: int = 50000,
        retain_stack: bool = True,
        avoid_opponents: bool = True,
    ) -> List[str]:
        """
        Quick Swap: red lightning bolt highlights ruled-out players so you can fix instantly.
        Options:
        - Ranking metric: usually projections
        - Salary thresholds: exclude cheap punts
        - Stack retention: keep stacks intact if possible
        - Avoid opponents: prevent hitters from being swapped against opposing pitcher
        - Salary upgrades: fill extra cap space if replacements cheaper
        - Drop another player: optionally remove second player to make salary work

        Source: https://support.sabersim.com/en/articles/12079563-using-late-swap
        """
        if out_player_id not in lineup:
            return lineup

        # Remove out player
        new_lineup = [pid for pid in lineup if pid != out_player_id]
        salary_used = sum(projections.get(pid, {}).get("salary", 5000) for pid in new_lineup)
        remaining_cap = salary_cap - salary_used

        # Find replacement: highest projection under remaining_cap.
        # CRITICAL: never re-select the ruled-out player itself.
        candidates = [
            (pid, proj) for pid, proj in projections.items()
            if pid != out_player_id
            and pid not in new_lineup
            and proj.get("projection", 0) > 0
            and proj.get("salary", 5000) <= remaining_cap
        ]
        # Sort by projection
        candidates.sort(key=lambda x: x[1].get("projection", 0), reverse=True)

        # Stack retention: if out player was part of stack, prefer same team
        out_team = projections.get(out_player_id, {}).get("team")
        if retain_stack and out_team:
            # Prefer players from same team as other lineup members? Simplified: prefer same team as out player
            same_team = [c for c in candidates if c[1].get("team") == out_team]
            if same_team:
                candidates = same_team + [c for c in candidates if c not in same_team]

        # Happy path: a single affordable replacement exists — take the best
        # (prefer same-team for stack retention when enabled).
        if candidates:
            new_lineup.append(candidates[0][0])
        elif new_lineup:
            # Drop another player only when no single replacement fits the
            # remaining cap ("Drop another player" option — Source: Using Late
            # Swap support article, https://support.sabersim.com/en/articles/12079563-using-late-swap).
            lineup_by_proj = sorted(
                new_lineup,
                key=lambda pid: projections.get(pid, {}).get("projection", 0),
            )
            for drop_pid in lineup_by_proj:
                trial = [pid for pid in new_lineup if pid != drop_pid]
                salary_used = sum(
                    projections.get(pid, {}).get("salary", 5000) for pid in trial
                )
                remaining_cap = salary_cap - salary_used
                slots_to_fill = len(lineup) - len(trial)
                trial_candidates = [
                    (pid, proj)
                    for pid, proj in projections.items()
                    if pid not in trial
                    and pid != out_player_id
                    and proj.get("projection", 0) > 0
                ]
                trial_candidates.sort(
                    key=lambda x: x[1].get("projection", 0), reverse=True
                )
                # Greedily fill all open slots under the remaining cap
                filled = []
                cap_left = remaining_cap
                for pid, proj in trial_candidates:
                    sal = proj.get("salary", 5000)
                    if sal <= cap_left:
                        filled.append(pid)
                        cap_left -= sal
                    if len(filled) == slots_to_fill:
                        break
                if len(filled) == slots_to_fill:
                    new_lineup = trial + filled
                    break

        return new_lineup[: len(lineup)]

    def auto_resim_loop(self, slate: List[Dict], poll_interval: int = 60, callback: Callable = None):
        """
        Automatic Resims: Every time projections or news update, reruns play-by-play sims.
        Source: https://support.sabersim.com/en/articles/12079563-using-late-swap

        This loop polls for news every poll_interval seconds, and if news found, reruns sims.
        """
        self.is_live = True
        # Initial sim
        scripts = self.simulator.run(slate)
        proj_engine = self.proj_factory(scripts)
        projections = proj_engine.build_projections()

        while self.is_live:
            news = self.check_news(slate, projections)
            if news:
                print(f"[LateSwap] News detected: {news}")
                # Update slate based on news
                for game in slate:
                    for player in game.get("players", []):
                        pid = player.get("id")
                        if pid in news and news[pid]["status"] == "OUT":
                            player["projection"] = 0
                            player["status"] = "OUT"
                # Resim
                scripts = self.simulator.run(slate)
                proj_engine = self.proj_factory(scripts)
                projections = proj_engine.build_projections()
                if callback:
                    callback({"scripts": scripts, "projections": projections, "news": news})
            time.sleep(poll_interval)
