# zoo_reflex_rc29.py
# ------------------
# rc29: Search-depth disruption overlay on A1 champion.
#
# Adversarial trick against opponents that do minimax / MCTS-style
# lookahead. Such opponents model "what will this agent do next" and
# compute a committed forward trajectory. If we instead do something
# unexpected — a STOP or a REVERSE — their predicted subtree becomes
# stale and their evaluation loses one ply of accuracy.
#
# rc29 implements a conservative version:
#   - We track our last K actions (simple circular buffer).
#   - If we've been moving the SAME direction for ≥ 3 turns AND a ghost
#     (enemy defender on our Pacman side) is within RC29_GHOST_TRIGGER
#     cells, prefer the REVERSE action IF REVERSE is in A1's top-K.
#   - Otherwise fall through to A1.
#
# Rationale: rigid direction-following is exactly what a simple minimax
# exploits with f_ghostDist — if it knows we'll keep going forward, it
# herds us. A one-turn reverse breaks the herding pattern without
# giving up A1's top-K safety band.

from __future__ import annotations

from collections import deque

from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate
from game import Directions, Actions


RC29_TOP_K = 3
RC29_A1_TOL_FRAC = 0.05
RC29_HISTORY_LEN = 4        # remember last 4 actions
RC29_SAME_DIR_MIN = 3       # fire if last N actions were the same non-STOP direction
RC29_GHOST_TRIGGER = 4       # only fire if ghost maze distance ≤ this


def _reverse_of(action):
    try:
        if action is None or action == Directions.STOP:
            return None
        return Actions.reverseDirection(action)
    except Exception:
        return None


class ReflexRC29Agent(ReflexA1Agent):
    """A1 champion + adversarial reverse injection when being herded."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self._rc29_hist = deque(maxlen=RC29_HISTORY_LEN)

    def _disruption_action(self, gameState, legal):
        """Return REVERSE action iff we should fire disruption, else None."""
        try:
            if not hasattr(self, "_rc29_hist"):
                self._rc29_hist = deque(maxlen=RC29_HISTORY_LEN)
            hist = self._rc29_hist
            if len(hist) < RC29_SAME_DIR_MIN:
                return None
            last = list(hist)[-RC29_SAME_DIR_MIN:]
            if any(a == Directions.STOP or a is None for a in last):
                return None
            if not all(a == last[0] for a in last):
                return None

            my_pos = gameState.getAgentPosition(self.index)
            my_state = gameState.getAgentState(self.index)
            if my_pos is None:
                return None
            # Only fire while we're Pacman (the herding concern).
            if not getattr(my_state, "isPacman", False):
                return None

            # Any non-scared ghost close on our Pacman side?
            threat = False
            for opp_idx in self.getOpponents(gameState):
                try:
                    ost = gameState.getAgentState(opp_idx)
                    if getattr(ost, "isPacman", False):
                        continue  # we want defenders, not invaders
                    if int(getattr(ost, "scaredTimer", 0) or 0) > 0:
                        continue
                    opp_pos = gameState.getAgentPosition(opp_idx)
                    if opp_pos is None:
                        continue
                    d = self.getMazeDistance(my_pos, opp_pos)
                    if d <= RC29_GHOST_TRIGGER:
                        threat = True
                        break
                except Exception:
                    continue
            if not threat:
                return None

            rev = _reverse_of(last[0])
            if rev is None or rev not in legal:
                return None
            return rev
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        # First: run A1's selection.
        try:
            a1_action = super()._chooseActionImpl(gameState)
        except Exception:
            a1_action = Directions.STOP

        # Decide whether to override with a REVERSE disruption.
        try:
            disrupt = self._disruption_action(gameState, legal)
        except Exception:
            disrupt = None

        chosen = a1_action
        if disrupt is not None and disrupt in legal:
            # Ensure disrupt is in A1's top-K tolerance to preserve safety.
            try:
                weights = self._get_weights()
                scored = []
                for action in legal:
                    try:
                        s = evaluate(self, gameState, action, weights)
                    except Exception:
                        s = float("-inf")
                    scored.append((s, action))
                scored.sort(key=lambda sa: sa[0], reverse=True)
                top_score = scored[0][0]
                tol = max(abs(top_score) * RC29_A1_TOL_FRAC, 1.0)
                K = min(RC29_TOP_K, len(scored))
                candidate_set = set(a for s, a in scored[:K]
                                    if s >= top_score - tol)
                if disrupt in candidate_set:
                    chosen = disrupt
            except Exception:
                pass

        # Record history AFTER decision.
        try:
            if not hasattr(self, "_rc29_hist"):
                self._rc29_hist = deque(maxlen=RC29_HISTORY_LEN)
            self._rc29_hist.append(chosen)
        except Exception:
            pass

        return chosen


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC29Agent", second="ReflexRC29Agent"):
    return [ReflexRC29Agent(firstIndex), ReflexRC29Agent(secondIndex)]
