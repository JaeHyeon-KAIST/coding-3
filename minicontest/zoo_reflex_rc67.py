# zoo_reflex_rc67.py
# ------------------
# rc67: Counterfactual Regret Minimization lite (bucketed regret).
#
# Standard MCCFR learns regrets across game histories; infeasible in
# Pacman's huge state space without extensive training. rc67 uses a
# small hand-designed state-abstraction bucket and maintains regret
# online during game-play, adjusting policy toward positive-regret
# actions.
#
# State abstraction (coarse; ~8 bucket classes):
#   (my_is_pacman, ghost_close, carry_high, score_lead)
# each a binary → 2^4 = 16 buckets. Bucket key = int(0..15).
#
# At each turn:
#   1. Get legal actions, rank by A1 evaluator.
#   2. Compute regret for top-K actions relative to the argmax:
#        regret[bucket][a] += max(0, value_best - value_a)
#      (inversely: actions that were clearly worse accumulate no
#      regret; close seconds accumulate some.)
#   3. Pick action with probability proportional to max(0, regret)
#      over top-K (RM+ rule). If all regrets 0, fall back to argmax.
#
# Inference-only: no training phase — regrets accumulate within a
# single game and reset across games. Not as powerful as offline-
# trained CFR but provides stochastic exploration around A1 baseline.
#
# Tier 3 (H category: CFR family).

from __future__ import annotations

import random as _random
from collections import defaultdict

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate, _ACTION_PREFERENCE
from zoo_core import TEAM
from game import Directions


RC67_TOP_K = 3
RC67_EPSILON_EXPLORE = 0.05


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC67Agent", second="ReflexRC67Agent"):
    return [ReflexRC67Agent(firstIndex), ReflexRC67Agent(secondIndex)]


class ReflexRC67Agent(ReflexA1Agent):
    """A1 + bucketed online regret-minimization (RM+ policy)."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        # Per-bucket per-action cumulative regret.
        self._rc67_regret = defaultdict(lambda: defaultdict(float))
        self._rc67_rng = _random.Random(0xCAFE + self.index)

    def _bucket(self, gameState):
        try:
            my_pos = gameState.getAgentPosition(self.index)
            my_state = gameState.getAgentState(self.index)
            is_pacman = getattr(my_state, "isPacman", False)
            carry = int(getattr(my_state, "numCarrying", 0) or 0)
            # Ghost-close: any opponent within 4 cells.
            ghost_close = False
            for opp in self.getOpponents(gameState):
                try:
                    p = gameState.getAgentPosition(opp)
                    if p is None or my_pos is None:
                        continue
                    if self.getMazeDistance(my_pos, p) <= 4:
                        ghost_close = True
                        break
                except Exception:
                    continue
            # Score lead: my_score > 0.
            try:
                sc = gameState.getScore()
                score = sc if self.red else -sc
            except Exception:
                score = 0
            lead = score > 0
            carry_high = carry >= 3
            # 4-bit bucket.
            b = (
                (1 if is_pacman else 0)
                | ((1 if ghost_close else 0) << 1)
                | ((1 if carry_high else 0) << 2)
                | ((1 if lead else 0) << 3)
            )
            return b
        except Exception:
            return 0

    def _chooseActionImpl(self, gameState):
        try:
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP

            weights = self._get_weights()
            try:
                ordered = sorted(
                    legal,
                    key=lambda a: (_ACTION_PREFERENCE.index(a)
                                   if a in _ACTION_PREFERENCE
                                   else len(_ACTION_PREFERENCE)),
                )
            except Exception:
                ordered = list(legal)

            scored = []
            for a in ordered:
                try:
                    s = evaluate(self, gameState, a, weights)
                except Exception:
                    s = float("-inf")
                scored.append((s, a))
            scored.sort(key=lambda sa: sa[0], reverse=True)
            if not scored or scored[0][0] == float("-inf"):
                return Directions.STOP

            top_score = scored[0][0]
            top_action = scored[0][1]
            K = min(RC67_TOP_K, len(scored))
            top_k = scored[:K]

            # Update regrets: actions that came close to argmax accrue
            # regret (indicates we might have chosen them given different
            # game states in this bucket).
            bucket = self._bucket(gameState)
            for s, a in top_k:
                reg = max(0.0, s - top_score + 3.0)  # +3.0 to soften
                self._rc67_regret[bucket][a] += reg

            # RM+ policy: sample proportional to positive regret among
            # top-K; epsilon-fallback to A1 argmax.
            if self._rc67_rng.random() < RC67_EPSILON_EXPLORE:
                chosen_action = self._rc67_rng.choice([a for _, a in top_k])
            else:
                pos_regs = [(max(0.0, self._rc67_regret[bucket][a]), a)
                            for _, a in top_k]
                total = sum(r for r, _ in pos_regs)
                if total <= 1e-6:
                    chosen_action = top_action
                else:
                    draw = self._rc67_rng.random() * total
                    running = 0.0
                    chosen_action = top_action
                    for r, a in pos_regs:
                        running += r
                        if draw <= running:
                            chosen_action = a
                            break

            if chosen_action not in legal:
                chosen_action = top_action
            return chosen_action
        except Exception:
            try:
                return super()._chooseActionImpl(gameState)
            except Exception:
                legal = gameState.getLegalActions(self.index)
                non_stop = [a for a in legal if a != Directions.STOP]
                return non_stop[0] if non_stop else Directions.STOP
