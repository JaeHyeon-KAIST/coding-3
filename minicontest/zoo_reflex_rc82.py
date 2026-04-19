# zoo_reflex_rc82.py
# ------------------
# rc82: rc44 state-conditioned stacking + rc29 REVERSE disruption.
#
# Both rc29 (92.5%) and rc44 (92.5%) are top pm24 winners. rc29 is a
# narrow, threat-conditioned tactical override (REVERSE when herded
# by a close ghost). rc44 is a broad, state-conditioned meta-vote
# over multiple base policies. The two are largely orthogonal — one
# triggers on local tactical state, the other on global game phase.
#
# rc82 layers them: run rc44's state-stacking to pick the "base"
# action, then check rc29's herding condition and potentially
# override with REVERSE if it fits in rc44's candidate-safe band.
#
# Fire semantics of REVERSE override:
#   - last N=3 consecutive actions were the same non-STOP direction,
#   - we are Pacman AND a non-scared ghost is within 4 cells,
#   - REVERSE is a legal action.
# Otherwise defer to rc44's stacked vote. Gentle combination: rc29
# fires rarely (only when herded), so rc44's stacking drives the
# overwhelming majority of turns.

from __future__ import annotations

from collections import deque

from zoo_reflex_rc44 import ReflexRC44Agent
from game import Directions, Actions


RC82_HIST_LEN = 4
RC82_SAME_DIR_MIN = 3
RC82_GHOST_TRIGGER = 4


def _reverse_of(action):
    try:
        if action is None or action == Directions.STOP:
            return None
        return Actions.reverseDirection(action)
    except Exception:
        return None


class ReflexRC82Agent(ReflexRC44Agent):
    """rc44 meta-stack + rc29 REVERSE-under-threat disruption."""

    def registerInitialState(self, gameState):
        super().registerInitialState(gameState)
        self._rc82_hist = deque(maxlen=RC82_HIST_LEN)

    def _should_reverse(self, gameState, legal):
        try:
            hist = getattr(self, "_rc82_hist", None)
            if hist is None or len(hist) < RC82_SAME_DIR_MIN:
                return None
            last = list(hist)[-RC82_SAME_DIR_MIN:]
            if any(a == Directions.STOP or a is None for a in last):
                return None
            if not all(a == last[0] for a in last):
                return None

            my_pos = gameState.getAgentPosition(self.index)
            my_state = gameState.getAgentState(self.index)
            if my_pos is None:
                return None
            if not getattr(my_state, "isPacman", False):
                return None

            threat = False
            for opp_idx in self.getOpponents(gameState):
                try:
                    ost = gameState.getAgentState(opp_idx)
                    if getattr(ost, "isPacman", False):
                        continue
                    if int(getattr(ost, "scaredTimer", 0) or 0) > 0:
                        continue
                    opp_pos = gameState.getAgentPosition(opp_idx)
                    if opp_pos is None:
                        continue
                    d = self.getMazeDistance(my_pos, opp_pos)
                    if d <= RC82_GHOST_TRIGGER:
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
            chosen = Directions.STOP
            self._record(chosen)
            return chosen

        # Run rc44 first.
        try:
            chosen = super()._chooseActionImpl(gameState)
        except Exception:
            chosen = Directions.STOP

        # Overlay rc29 REVERSE disruption if applicable.
        try:
            disrupt = self._should_reverse(gameState, legal)
            if disrupt is not None and disrupt in legal:
                chosen = disrupt
        except Exception:
            pass

        self._record(chosen)
        return chosen

    def _record(self, action):
        try:
            if not hasattr(self, "_rc82_hist"):
                self._rc82_hist = deque(maxlen=RC82_HIST_LEN)
            self._rc82_hist.append(action)
        except Exception:
            pass


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC82Agent", second="ReflexRC82Agent"):
    return [ReflexRC82Agent(firstIndex), ReflexRC82Agent(secondIndex)]
