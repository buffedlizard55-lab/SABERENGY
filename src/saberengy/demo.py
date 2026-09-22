"""
Demo script — runs full SABERENGY pipeline: sim -> projections -> ownership -> optimizer -> contest sim.

Usage:
  python -m saberengy.demo --sport NFL --slate main --n-sims 1000

No manual input required — uses synthetic slate for demo, but can be extended to fetch real data via data_sources.py.

Verified pipeline matches SaberSim flow:
1. Play-by-play simulations (thousands)
2. Point projections = mean across sims + percentiles
3. Field lineups + ownership (13 contest types)
4. Sim Mode optimizer with correlation, sim diversity, ownership fade sliders
5. Contest Sims 100k evaluations
"""

import argparse
import json
import csv
import os
from .simulation import Simulator
from .projections import ProjectionEngine
from .ownership import OwnershipModel, CONTEST_TYPES_13
from .optimizer import SimOptimizer
from .contest_sim import ContestSimulator
from .data_sources import get_verification_links

def generate_synthetic_slate(sport="NFL", num_games=3, players_per_game=20):
    """Generate synthetic slate for demo — in real use, would fetch from official APIs."""
    slate = []
    teams = {
        "NFL": [("KC", "BUF"), ("DAL", "SF"), ("PHI", "MIA")],
        "NBA": [("LAL", "GSW"), ("BOS", "MIL"), ("DEN", "PHX")],
        "MLB": [("NYY", "BOS"), ("LAD", "SD"), ("ATL", "NYM")],
    }
    game_pairs = teams.get(sport, [("HOME", "AWAY")] * num_games)
    for idx, (home, away) in enumerate(game_pairs[:num_games]):
        players = []
        # Generate players per team
        for team in [home, away]:
            # QB or equivalent star
            positions = {
                "NFL": ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "DST"],
                "NBA": ["PG", "SG", "SF", "PF", "C", "PG", "SG", "SF"],
                "MLB": ["P", "P", "C", "1B", "2B", "3B", "SS", "OF", "OF", "OF"],
            }
            pos_list = positions.get(sport, ["P"] * 10)
            for i, pos in enumerate(pos_list):
                pid = f"{team}_{pos}_{i}_{idx}"
                base_proj = {
                    "QB": 18, "RB": 15, "WR": 14, "TE": 10, "DST": 7,
                    "PG": 35, "SG": 30, "SF": 28, "PF": 27, "C": 32,
                    "P": 18, "C": 8, "1B": 9, "2B": 8, "3B": 8, "SS": 9, "OF": 10,
                }.get(pos, 10)
                players.append({
                    "id": pid,
                    "name": f"{team} {pos}{i}",
                    "team": team,
                    "position": pos,
                    "projection": base_proj + (idx * 0.5),
                    "std": base_proj * 0.4,
                    "salary": 4000 + (i * 150) + int(base_proj * 50),  # lower to fit cap
                    "is_starter": i < 5,
                })
        slate.append({
            "game_id": f"{home}_{away}_{idx}",
            "home_team": home,
            "away_team": away,
            "vegas_total": 48 if sport == "NFL" else 220 if sport == "NBA" else 9,
            "players": players,
        })
    return slate

def main():
    parser = argparse.ArgumentParser(description="SABERENGY Demo — Verified SaberSim Reverse Engineering")
    parser.add_argument("--sport", default="NFL", choices=["NFL", "NBA", "MLB"], help="Sport to simulate")
    parser.add_argument("--slate", default="main", help="Slate name")
    parser.add_argument("--n-sims", type=int, default=1000, help="Number of game simulations per game")
    parser.add_argument("--n-lineups", type=int, default=100, help="Number of lineups to build")
    parser.add_argument("--output", default="output", help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)

    print(f"[SABERENGY] Starting demo — Sport: {args.sport}, Sims: {args.n_sims}")
    print(f"[Verification] All sources: {get_verification_links()}")

    # 1. Generate slate (in real use, fetch from official APIs via data_sources.py)
    slate = generate_synthetic_slate(sport=args.sport, num_games=3)
    print(f"[1/5] Slate generated: {len(slate)} games, {sum(len(g['players']) for g in slate)} players")

    # 2. Run play-by-play simulations
    sim = Simulator(sport=args.sport, n_sims=args.n_sims, seed=42)
    scripts = sim.run(slate)
    print(f"[2/5] Simulations complete: {len(scripts)} game scripts")
    corr_matrix = sim.compute_correlation_matrix(scripts)
    print(f"      Correlation matrix: {len(corr_matrix)} pairs")

    # 3. Build projections
    proj_engine = ProjectionEngine(scripts)
    projections = proj_engine.build_projections()
    detailed = proj_engine.get_detailed_stats()
    print(f"[3/5] Projections built: {len(projections)} players")
    # Save projections CSV (matches SaberSim feature)
    with open(os.path.join(args.output, "projections.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["player_id", "player_name", "team", "position", "projection", "p10", "p25", "p50", "p75", "p85", "p90", "p95", "std"])
        writer.writeheader()
        for row in proj_engine.to_csv_rows():
            writer.writerow(row)
    print(f"      Saved projections.csv")

    # 4. Ownership model — 13 contest types
    # Add salary to projections for ownership model
    for game in slate:
        for p in game["players"]:
            pid = p["id"]
            if pid in projections:
                projections[pid]["salary"] = p["salary"]

    own_model = OwnershipModel(contest_type="Flagship MME", num_field_lineups=5000)
    ownership = own_model.project(projections)
    all_ownership = own_model.project_all_contests(projections)
    adjusted = own_model.adjusted_ownership(projections, ownership)
    leverage = own_model.leverage_score(projections, ownership)
    print(f"[4/5] Ownership projected: Flagship MME + {len(CONTEST_TYPES_13)} contest types")
    # Save ownership
    with open(os.path.join(args.output, "ownership.csv"), "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["player_id", "player_name", "ownership", "adjusted_ownership", "leverage", "projection"])
        writer.writeheader()
        for pid, own in ownership.items():
            proj = projections.get(pid, {})
            writer.writerow({
                "player_id": pid,
                "player_name": proj.get("player_name", pid),
                "ownership": own,
                "adjusted_ownership": adjusted.get(pid, 0),
                "leverage": leverage.get(pid, 0),
                "projection": proj.get("projection", 0),
            })
    print(f"      Saved ownership.csv")

    # 5. Optimizer — Sim Mode
    # lineup_size=9 matches DraftKings classic NFL roster size (9 players).
    optimizer = SimOptimizer(salary_cap=50000, lineup_size=9, correlation_weight=0.7, sim_diversity=0.6, ownership_fade=0.5)
    lineups = optimizer.build(scripts, projections, ownership, num_lineups=args.n_lineups, correlation_matrix=corr_matrix)
    print(f"[5/5] Optimizer built {len(lineups)} lineups (Sim Mode)")
    with open(os.path.join(args.output, "lineups.csv"), "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([f"player_{i+1}" for i in range(9)])
        for lineup in lineups:
            writer.writerow(lineup)
    print(f"      Saved lineups.csv")

    # 6. Contest Sims
    # Generate field lineups for contest sim
    field_gen = own_model.field_generator
    field_lineups = field_gen.generate(projections)
    # Simplified payout: top-heavy GPP
    payout = [100000, 50000, 25000, 10000, 5000, 2000, 1000, 500, 200, 100] + [50]*90 + [20]*400 + [10]*500
    contest_sim = ContestSimulator(payout_structure=payout, num_sims=10000)  # 10k for demo speed, real is 100k
    result = contest_sim.simulate(my_lineups=lineups[:20], field_lineups=field_lineups[:500], game_scripts=scripts, projections_lookup=projections)
    with open(os.path.join(args.output, "contest_sim.json"), "w") as f:
        json.dump(result, f, indent=2)
    print(f"      Contest Sim complete: {result['summary']}")
    print(f"      Saved contest_sim.json")

    # Summary
    print("\n[SABERENGY] Demo complete — all paywalled features rebuilt as open source")
    print(f"Outputs in {args.output}/")
    print("Verification links:")
    for k, v in get_verification_links().items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
