# zoo_reflex_rc44.py
# ------------------
# rc44: State-conditioned stacking meta-policy over top-4 rc's.
#
# rc45 does a weighted vote with a *fixed* weight vector (empirical WR).
# rc44 upgrades by making weights **state-conditional** on a 4-class
# partition of game states. In each class, the historically best-fit
# member carries extra weight; members that don't fit the class get
# downweighted.
#
# State classes (computed per-turn, each agent independently):
#   offense_carry  : we are Pacman and carrying >= 3 food
#   defense_rush   : an invader is visible and we're on home side
#   endgame        : remaining game moves (approximated by timer) < 300
#   normal         : everything else
#
# Per-class weights (hand-tuned from pm23 batches 1-3 top rcs):
#   offense_carry:  A1 1.2,  rc02 0.5,  rc16 1.2,  rc32 0.8
#     - A1/rc16 are strongest at safe food return; rc02 (defense-focused)
#       is mostly irrelevant during offense carry, rc32 (pincer) as well.
#   defense_rush:   A1 0.8,  rc02 1.3,  rc16 0.9,  rc32 1.3
#     - rc02 + rc32 both shine in defensive situations.
#   endgame:        A1 1.0,  rc02 1.0,  rc16 1.2,  rc32 0.9
#     - rc16's territorial control dominates late game.
#   normal:         A1 0.8,  rc02 1.0,  rc16 1.0,  rc32 0.9
#     - roughly equal; mildly favor rc02/rc16 (both 100%).
#
# Implementation: each base policy casts its argmax action. Winning
# action = argmax over (sum_{member} weight_member(class) *
# 1[member.vote == action]). Tie-break by total weight.
#
# Unlike rc45, rc44 does NOT require all 4 members to complete — a
# failed member (returns None) simply casts 0 votes.

from __future__ import annotations

import time
from collections import defaultdict

from zoo_reflex_A1 import ReflexA1Agent
from zoo_reflex_rc02 import ReflexRC02Agent, _articulation_points
from zoo_reflex_rc16 import ReflexRC16Agent
from zoo_reflex_rc32 import ReflexRC32Agent
from game import Directions


RC44_TIME_BUDGET_WARN = 0.80

# Per-class weight table. Keys are class names; values are dicts
# keyed by member name. Anchored on pm23 40-game WR.
RC44_WEIGHTS = {
    "offense_carry": {"a1": 1.2,  "rc02": 0.5, "rc16": 1.2, "rc32": 0.8},
    "defense_rush":  {"a1": 0.8,  "rc02": 1.3, "rc16": 0.9, "rc32": 1.3},
    "endgame":       {"a1": 1.0,  "rc02": 1.0, "rc16": 1.2, "rc32": 0.9},
    "normal":        {"a1": 0.8,  "rc02": 1.0, "rc16": 1.0, "rc32": 0.9},
}

RC44_CARRY_MIN = 3
RC44_ENDGAME_MOVES_LEFT = 300    # rough heuristic; data.timeleft fallback


class ReflexRC44Agent(ReflexA1Agent):
    """State-conditioned stacking over A1 + rc02 + rc16 + rc32."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        try:
            self.tarjan_aps = _articulation_points(gameState.getWalls())
        except Exception:
            self.tarjan_aps = frozenset()
        self._rc44_turn = 0

    def _classify_state(self, gameState):
        """Return one of 'offense_carry', 'defense_rush', 'endgame', 'normal'."""
        try:
            my_state = gameState.getAgentState(self.index)
            my_pos = gameState.getAgentPosition(self.index)

            # Endgame: uses self._rc44_turn (incremented each chooseAction).
            # Roughly 4-agent interleaving: 1200 total → 300 per agent.
            # Endgame kicks in when our turn count > 225 (last quarter).
            if self._rc44_turn > 225:
                return "endgame"

            # Offense carry: we're Pacman, carrying ≥ 3.
            try:
                carrying = int(getattr(my_state, "numCarrying", 0) or 0)
            except Exception:
                carrying = 0
            if getattr(my_state, "isPacman", False) and carrying >= RC44_CARRY_MIN:
                return "offense_carry"

            # Defense rush: visible invader + we're on home.
            if not getattr(my_state, "isPacman", False):
                for opp_idx in self.getOpponents(gameState):
                    try:
                        ost = gameState.getAgentState(opp_idx)
                        if getattr(ost, "isPacman", False):
                            p = gameState.getAgentPosition(opp_idx)
                            if p is not None:
                                return "defense_rush"
                    except Exception:
                        continue

            return "normal"
        except Exception:
            return "normal"

    def _vote(self, cls, fn, gameState):
        try:
            return fn(self, gameState)
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        t0 = time.time()
        self._rc44_turn += 1

        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        try:
            cls = self._classify_state(gameState)
        except Exception:
            cls = "normal"
        weights = RC44_WEIGHTS.get(cls, RC44_WEIGHTS["normal"])

        votes = {
            "a1":   self._vote(cls, ReflexA1Agent._chooseActionImpl, gameState),
            "rc02": self._vote(cls, ReflexRC02Agent._chooseActionImpl, gameState),
            "rc16": self._vote(cls, ReflexRC16Agent._chooseActionImpl, gameState),
            "rc32": self._vote(cls, ReflexRC32Agent._chooseActionImpl, gameState),
        }

        tallies = defaultdict(float)
        for name, act in votes.items():
            if act is None or act not in legal:
                continue
            tallies[act] += weights.get(name, 0.0)

        if not tallies:
            return Directions.STOP if Directions.STOP in legal else legal[0]

        chosen = max(tallies.items(), key=lambda kv: kv[1])[0]

        dt = time.time() - t0
        if dt > RC44_TIME_BUDGET_WARN:
            try:
                print(f"[rc44] warn: turn took {dt:.3f}s cls={cls}")
            except Exception:
                pass
        return chosen


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC44Agent", second="ReflexRC44Agent"):
    return [ReflexRC44Agent(firstIndex), ReflexRC44Agent(secondIndex)]
