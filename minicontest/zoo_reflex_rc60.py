# zoo_reflex_rc60.py
# ------------------
# rc60: Difference Rewards / Aristocrat Utility for teammate coordination.
#
# Paradigm (Tumer & Wolpert, 2008): "What would have happened if I had
# done nothing?" The aristocrat utility D_i(s, a) = U(s, a_i, a_-i) -
# U(s, a_null, a_-i) credits agent i ONLY for the delta it personally
# contributes. In a 2v2 team, this reduces my tendency to duplicate
# what my teammate is already doing and pushes me toward complementary
# actions.
#
# Implementation (reflex-level, 1-step lookahead):
#   1. Run A1 reflex argmax → get my top-K candidate actions (tolerance
#      band 5% of top score).
#   2. Estimate teammate's LIKELY next action (their own A1 argmax at
#      THEIR state).
#   3. For each of my candidates a_i, compute:
#        D(a_i) = evaluate(self, succ_after_me+mate, a_i, weights)
#                 - evaluate(self, succ_after_mate_only, STOP, weights)
#      Effectively: "what does my action add beyond teammate's?"
#   4. Pick argmax D. Tie-break by A1 preference order.
#
# When teammate's inferred action overlaps with my region of movement,
# this rewards me for FINDING A DIFFERENT angle (less duplication).
#
# Tier 3 (category: Multi-agent coordination / Credit assignment).

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent, _A1_OVERRIDE
from zoo_features import (
    evaluate,
    SEED_WEIGHTS_OFFENSIVE,
    SEED_WEIGHTS_DEFENSIVE,
    _ACTION_PREFERENCE,
)
from zoo_core import TEAM
from game import Directions


RC60_TOP_K = 4
RC60_A1_TOL_FRAC = 0.05


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC60Agent", second="ReflexRC60Agent"):
    return [ReflexRC60Agent(firstIndex), ReflexRC60Agent(secondIndex)]


class ReflexRC60Agent(ReflexA1Agent):
    """A1 + Difference Reward overlay for teammate coordination."""

    def _weights_for(self, idx):
        try:
            role = TEAM.role.get(idx, "OFFENSE")
        except Exception:
            role = "OFFENSE"
        if _A1_OVERRIDE.get("w_off") and _A1_OVERRIDE.get("w_def"):
            return _A1_OVERRIDE["w_def"] if role == "DEFENSE" else _A1_OVERRIDE["w_off"]
        return SEED_WEIGHTS_DEFENSIVE if role == "DEFENSE" else SEED_WEIGHTS_OFFENSIVE

    def _teammate_index(self, gameState):
        try:
            team = sorted(list(self.getTeam(gameState)))
            mates = [i for i in team if i != self.index]
            return mates[0] if mates else None
        except Exception:
            return None

    def _infer_teammate_action(self, gameState, mate_idx):
        """Teammate's A1 argmax at current state (without overlays)."""
        try:
            legal = gameState.getLegalActions(mate_idx)
        except Exception:
            return None
        if not legal:
            return None
        weights = self._weights_for(mate_idx)
        # Proxy: evaluate from self's perspective (slight bias but cheap).
        best = float("-inf")
        best_a = legal[0]
        try:
            ordered = sorted(
                legal,
                key=lambda a: (_ACTION_PREFERENCE.index(a)
                               if a in _ACTION_PREFERENCE
                               else len(_ACTION_PREFERENCE)),
            )
        except Exception:
            ordered = list(legal)
        for a in ordered:
            try:
                # Create a quick successor-under-mate and evaluate from self
                # perspective. We do NOT actually apply the successor here
                # — we just need a rough score for the aristocrat baseline.
                v = evaluate(self, gameState, a, weights)
            except Exception:
                continue
            if v > best:
                best = v
                best_a = a
        return best_a

    def _chooseActionImpl(self, gameState):
        try:
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP

            my_weights = self._get_weights()

            # A1 baseline scoring.
            scored = []
            for action in legal:
                try:
                    s = evaluate(self, gameState, action, my_weights)
                except Exception:
                    s = float("-inf")
                scored.append((s, action))
            scored.sort(key=lambda sa: sa[0], reverse=True)
            if not scored or scored[0][0] == float("-inf"):
                return Directions.STOP

            top_score = scored[0][0]
            tol = max(abs(top_score) * RC60_A1_TOL_FRAC, 1.0)
            K = min(RC60_TOP_K, len(scored))
            candidates = [(s, a) for s, a in scored[:K] if s >= top_score - tol]

            if len(candidates) <= 1:
                return candidates[0][1] if candidates else scored[0][1]

            mate_idx = self._teammate_index(gameState)
            if mate_idx is None:
                return scored[0][1]

            mate_action = self._infer_teammate_action(gameState, mate_idx)
            if mate_action is None:
                return scored[0][1]

            # Build baseline "null-me" state: teammate moves, I STOP.
            try:
                mate_succ = gameState.generateSuccessor(mate_idx, mate_action)
            except Exception:
                return scored[0][1]
            baseline = None
            try:
                baseline = evaluate(self, mate_succ, Directions.STOP, my_weights)
            except Exception:
                pass
            if baseline is None:
                return scored[0][1]

            # Aristocrat score for each of my top-K.
            best_d = float("-inf")
            best_action = scored[0][1]
            for s, a in candidates:
                # Apply my action AFTER teammate: approximate by evaluating
                # my action against mate_succ (i.e., "my delta over null").
                try:
                    v = evaluate(self, mate_succ, a, my_weights)
                except Exception:
                    v = float("-inf")
                diff = v - baseline
                if diff > best_d:
                    best_d = diff
                    best_action = a

            if best_action not in legal:
                return scored[0][1]
            return best_action
        except Exception:
            try:
                legal = gameState.getLegalActions(self.index)
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP
            except Exception:
                return Directions.STOP
