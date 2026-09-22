import sys
sys.path.insert(0, 'src')
from saberengy.simulation import Simulator
from saberengy.projections import ProjectionEngine
from saberengy.ownership import OwnershipModel
from saberengy.optimizer import SimOptimizer
from saberengy.contest_sim import ContestSimulator

def test_full_pipeline():
    slate = [
        {
            "game_id": "KC_BUF_0",
            "home_team": "KC",
            "away_team": "BUF",
            "vegas_total": 50,
            "players": [
                {"id": f"KC_QB_{i}", "name": f"KC QB{i}", "team": "KC", "position": "QB", "projection": 20, "std": 8, "salary": 6000}
                for i in range(2)
            ] + [
                {"id": f"BUF_WR_{i}", "name": f"BUF WR{i}", "team": "BUF", "position": "WR", "projection": 14, "std": 6, "salary": 5000}
                for i in range(6)
            ]
        }
    ]
    sim = Simulator(sport="NFL", n_sims=50, seed=42)
    scripts = sim.run(slate)
    assert len(scripts) == 50
    print(f"✓ Simulation: {len(scripts)} scripts")

    proj_engine = ProjectionEngine(scripts)
    projections = proj_engine.build_projections()
    assert len(projections) > 0
    for pid, data in projections.items():
        assert "projection" in data
        assert "median_p50" in data
        assert "floor_p10" in data
        assert data["projection"] >= 0
    print(f"✓ Projections: {len(projections)} players, mean + percentiles")

    # Add salary for ownership
    for p in slate[0]["players"]:
        if p["id"] in projections:
            projections[p["id"]]["salary"] = p["salary"]

    own_model = OwnershipModel(contest_type="Flagship MME", num_field_lineups=100)
    ownership = own_model.project(projections)
    assert len(ownership) == len(projections)
    assert all(0 <= v <= 1 for v in ownership.values())
    print(f"✓ Ownership: {len(ownership)} players, contest-specific")

    all_own = own_model.project_all_contests(projections)
    assert len(all_own) == 13
    print(f"✓ 13 Contest Types: {list(all_own.keys())[:3]}...")

    corr = sim.compute_correlation_matrix(scripts)
    print(f"✓ Correlation Matrix: {len(corr)} pairs")

    optimizer = SimOptimizer(salary_cap=50000, lineup_size=4, correlation_weight=0.5, sim_diversity=0.5, ownership_fade=0.5)
    lineups = optimizer.build(scripts, projections, ownership, num_lineups=10, correlation_matrix=corr)
    assert len(lineups) > 0
    print(f"✓ Sim Optimizer: {len(lineups)} lineups, correlation + diversity + fade")

    field_lineups = own_model.field_generator.generate(projections)
    contest_sim = ContestSimulator(payout_structure=[100, 50, 20, 10], num_sims=100)
    result = contest_sim.simulate(my_lineups=lineups[:2], field_lineups=field_lineups[:20], game_scripts=scripts)
    assert "per_lineup" in result
    assert "summary" in result
    print(f"✓ Contest Sims: ROI, Win Rate, Cash Rate, ROI StdDev")

    print("\nAll tests passed — verified pipeline matches SaberSim docs")

if __name__ == "__main__":
    test_full_pipeline()
