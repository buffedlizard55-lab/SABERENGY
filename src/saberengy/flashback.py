"""
Contest Flashback — study past slates.

Verified from:
- https://support.sabersim.com/en/articles/12079605-using-contest-flashback
  "How It Works: All lineups are collected. After a DraftKings contest completes, SaberSim takes all of the real lineups that were actually played in that contest. Re-simulation. These real lineups are run through 100,000 slate simulations using SaberSim’s play-by-play game engine. Performance measurement. Each lineup is tested against realistic outcomes across thousands of game scripts"
  "What is Sim ROI and how should I use it? Sim ROI is the primary metric for evaluating DFS play. It shows the average return you’d expect if the contest were played out 100,000 times"

This class does not download DraftKings contest files. The caller must supply
lineups. The default 100,000 simulations is the count named on SaberSim's
page, not a benchmark that this process finishes in 30 seconds.
"""

from typing import List, Dict
from .contest_sim import ContestSimulator
from .simulation import GameScript

class FlashbackAnalyzer:
    def __init__(self, game_scripts: List[GameScript], payout_structure: List[float]):
        self.game_scripts = game_scripts
        self.payout_structure = payout_structure
        self.simulator = ContestSimulator(payout_structure, num_sims=100000)

    def analyze_contest(self, real_lineups: List[List[str]], contest_id: str = "unknown") -> Dict:
        """
        real_lineups: list of actual lineups played in contest (from DK CSV)
        Returns Sim ROI per lineup, plus top players analysis.

        Source: DK CSV download — verified via https://www.reddit.com/r/dfsports/comments/1741d6h/is_there_anywhere_to_find_ownership_results/
        "download the CSV file from draftkings. can do it by individual contests"
        """
        result = self.simulator.flashback_sim(real_lineups, self.game_scripts)

        # Additional analysis: which players appeared in top ROI lineups?
        per_lineup = result["per_lineup"]
        # Sort by ROI descending
        sorted_lineups = sorted(per_lineup.values(), key=lambda x: x["roi"], reverse=True)

        # Top 10% lineups
        top_n = max(1, len(sorted_lineups) // 10)
        top_lineups = sorted_lineups[:top_n]

        # Count player frequency in top lineups
        from collections import Counter
        counter = Counter()
        for entry in top_lineups:
            for pid in entry["lineup"]:
                counter[pid] += 1

        return {
            "contest_id": contest_id,
            "total_lineups": len(real_lineups),
            "sim_results": result,
            "top_lineups": top_lineups[:10],  # top 10
            "player_frequency_in_top": dict(counter.most_common(20)),
            "summary": result["summary"],
        }

    def compare_ownership_vs_actual(self, projected_ownership: Dict[str, float], real_ownership: Dict[str, float]) -> Dict:
        """
        Compare projected ownership vs actual ownership from contest CSV.
        Helps validate ownership model.
        """
        comparison = {}
        for pid in set(list(projected_ownership.keys()) + list(real_ownership.keys())):
            proj = projected_ownership.get(pid, 0)
            real = real_ownership.get(pid, 0)
            comparison[pid] = {
                "projected": proj,
                "actual": real,
                "diff": real - proj,
                "abs_diff": abs(real - proj),
            }
        # Sort by abs diff descending — biggest misses
        sorted_diff = sorted(comparison.items(), key=lambda x: x[1]["abs_diff"], reverse=True)
        return {
            "per_player": comparison,
            "biggest_misses": sorted_diff[:20],
            "avg_abs_error": sum(v["abs_diff"] for v in comparison.values()) / len(comparison) if comparison else 0,
        }
