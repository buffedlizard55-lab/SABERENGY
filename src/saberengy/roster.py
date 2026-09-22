"""Roster rules transcribed from public DraftKings classic rules pages.

NFL: https://www.draftkings.com/help/rules/1/1
  - 9 players: 1 QB, 2 RB, 3 WR, 1 TE, 1 FLEX (RB/WR/TE), 1 DST
  - salary cap $50,000
  - players from at least 2 different NFL games
  The fetched rules page does not state an 8-player team cap. A third-party
  guide claims that cap. It is NOT enforced here. See LIMITATIONS.md.

MLB: https://www.draftkings.com/help/rules/2/2
  - 10 players: 2 P, 1 C, 1 1B, 1 2B, 1 3B, 1 SS, 3 OF
  - salary cap $50,000
  - at least 2 different MLB games
  - no more than 5 hitters from any one team
  DH is not a classic slot. Primary-position DH players are not forced
  into a field slot. DraftKings position eligibility is DK's discretion
  and is not in the MLB Stats API response.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Slot:
    name: str
    eligible: frozenset


@dataclass(frozen=True)
class RosterRules:
    site: str
    sport: str
    salary_cap: int
    slots: Tuple[Slot, ...]
    min_games: int
    max_hitters_per_team: Optional[int]
    source_url: str
    hitter_positions: frozenset = frozenset()

    @property
    def lineup_size(self) -> int:
        return len(self.slots)


DK_NFL_CLASSIC = RosterRules(
    site="DraftKings",
    sport="NFL",
    salary_cap=50_000,
    slots=(
        Slot("QB", frozenset({"QB"})),
        Slot("RB1", frozenset({"RB"})),
        Slot("RB2", frozenset({"RB"})),
        Slot("WR1", frozenset({"WR"})),
        Slot("WR2", frozenset({"WR"})),
        Slot("WR3", frozenset({"WR"})),
        Slot("TE", frozenset({"TE"})),
        Slot("FLEX", frozenset({"RB", "WR", "TE"})),
        Slot("DST", frozenset({"DST"})),
    ),
    min_games=2,
    max_hitters_per_team=None,
    source_url="https://www.draftkings.com/help/rules/1/1",
)

DK_MLB_CLASSIC = RosterRules(
    site="DraftKings",
    sport="MLB",
    salary_cap=50_000,
    slots=(
        Slot("P1", frozenset({"P"})),
        Slot("P2", frozenset({"P"})),
        Slot("C", frozenset({"C"})),
        Slot("1B", frozenset({"1B"})),
        Slot("2B", frozenset({"2B"})),
        Slot("3B", frozenset({"3B"})),
        Slot("SS", frozenset({"SS"})),
        Slot("OF1", frozenset({"OF"})),
        Slot("OF2", frozenset({"OF"})),
        Slot("OF3", frozenset({"OF"})),
    ),
    min_games=2,
    max_hitters_per_team=5,
    source_url="https://www.draftkings.com/help/rules/2/2",
    hitter_positions=frozenset({"C", "1B", "2B", "3B", "SS", "OF"}),
)

MLB_POSITION_MAP = {
    "P": "P",
    "SP": "P",
    "RP": "P",
    "C": "C",
    "1B": "1B",
    "2B": "2B",
    "3B": "3B",
    "SS": "SS",
    "OF": "OF",
    "LF": "OF",
    "CF": "OF",
    "RF": "OF",
    "DH": "DH",
}


def normalize_position(sport: str, position: str) -> str:
    pos = (position or "").upper().strip()
    if sport.upper() == "MLB":
        return MLB_POSITION_MAP.get(pos, pos)
    if pos in {"DEF", "D", "D/ST", "DST"}:
        return "DST"
    return pos


def validate_lineup(
    player_ids: Sequence[str],
    players: Dict[str, dict],
    rules: RosterRules,
    *,
    enforce_salary: bool = True,
) -> Tuple[bool, str]:
    """Return (ok, reason). Reason is empty when ok."""
    if len(player_ids) != rules.lineup_size:
        return False, f"size {len(player_ids)} != {rules.lineup_size}"
    if len(set(player_ids)) != len(player_ids):
        return False, "duplicate player"
    assigned = _assign_slots(player_ids, players, rules)
    if assigned is None:
        return False, "position slots cannot be filled"
    if enforce_salary and rules.salary_cap:
        salary = sum(int(players[pid].get("salary") or 0) for pid in player_ids)
        if any(players[pid].get("salary") is None for pid in player_ids):
            return False, "salary missing while salary cap is enforced"
        if salary > rules.salary_cap:
            return False, f"salary {salary} exceeds {rules.salary_cap}"
    games = {players[pid].get("game_id") for pid in player_ids}
    games.discard(None)
    if rules.min_games and len(games) < rules.min_games:
        return False, f"games {len(games)} < {rules.min_games}"
    if rules.max_hitters_per_team:
        from collections import Counter

        counts = Counter()
        for pid in player_ids:
            pos = normalize_position(rules.sport, players[pid].get("position", ""))
            if pos in rules.hitter_positions:
                counts[players[pid].get("team")] += 1
        if any(n > rules.max_hitters_per_team for n in counts.values()):
            return False, "hitter team cap exceeded"
    return True, ""


def _assign_slots(
    player_ids: Sequence[str],
    players: Dict[str, dict],
    rules: RosterRules,
) -> Optional[List[str]]:
    """Greedy slot assignment, scarcest eligibility first. None if impossible."""
    remaining = list(player_ids)
    order = sorted(range(len(rules.slots)), key=lambda i: len(rules.slots[i].eligible))
    assignment = [""] * len(rules.slots)
    for index in order:
        slot = rules.slots[index]
        match = None
        for pid in remaining:
            pos = normalize_position(rules.sport, players[pid].get("position", ""))
            if pos in slot.eligible:
                match = pid
                break
        if match is None:
            return None
        remaining.remove(match)
        assignment[index] = match
    return assignment


def slot_order(rules: RosterRules) -> List[int]:
    """Fill scarce slots first so FLEX/OF are not consumed early."""
    return sorted(range(len(rules.slots)), key=lambda i: (len(rules.slots[i].eligible), i))


def games_represented(player_ids: Iterable[str], players: Dict[str, dict]) -> int:
    return len({players[pid].get("game_id") for pid in player_ids if players.get(pid)})
