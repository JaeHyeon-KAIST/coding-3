# zoo_reflex_capsule.py
# ---------------------
# Inherits ReflexTunedAgent but overrides capsule policy per STRATEGY.md §5.3.
# Capsule is eaten ONLY when a triggering condition fires; otherwise, the
# f_distToCapsule weight is reduced (agent is less eager to chase the capsule).
#
# Trigger conditions (eat capsule):
#   (a) Active enemy ghost within dist 3 AND no 2-step escape path
#   (b) numCarrying >= 5 AND capsule closer than home + 2
#   (c) Entering a bottleneck cell with an active enemy ghost pursuing
#
# Implementation: adjust f_distToCapsule bias before calling evaluate().

from __future__ import annotations

import copy

from zoo_core import TEAM
from zoo_reflex_tuned import ReflexTunedAgent
from zoo_features import (
    extract_features, SEED_WEIGHTS_OFFENSIVE, SEED_WEIGHTS_DEFENSIVE,
    _ACTION_PREFERENCE,
)
from game import Directions


def createTeam(firstIndex, secondIndex, isRed,
               first='ReflexCapsuleAgent', second='ReflexCapsuleAgent'):
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


# Capsule weight when trigger is NOT firing (be less eager).
_CAPSULE_WEIGHT_LOW = 1.0
# Capsule weight when trigger IS firing (amplify urgency to eat).
_CAPSULE_WEIGHT_HIGH = 80.0


class ReflexCapsuleAgent(ReflexTunedAgent):
    """Reflex agent with conditional capsule eating policy."""

    def _capsule_trigger(self, gameState):
        """Return True if any capsule-eating condition fires.

        Conditions (any one is sufficient):
          (a) Active enemy ghost within dist 3 AND no 2-step escape.
          (b) numCarrying >= 5 AND capsule closer than nearest home frontier + 2.
          (c) Current position is a bottleneck AND active ghost within dist 5.
        """
        try:
            snap = self.snapshot(gameState)
            myPos = snap.get('myPos')
            numCarrying = snap.get('numCarrying', 0)
            capsuleList = snap.get('capsuleList', [])
            opponentPositions = snap.get('opponentPositions', {})

            if myPos is None or not capsuleList:
                return False

            # Collect active ghost distances.
            active_ghost_dists = []
            for opp_idx, opp_pos in opponentPositions.items():
                if opp_pos is None:
                    continue
                try:
                    opp_state = gameState.getAgentState(opp_idx)
                    if getattr(opp_state, 'isPacman', False):
                        continue
                    if int(getattr(opp_state, 'scaredTimer', 0) or 0) > 0:
                        continue
                    dist = self.getMazeDistance(myPos, opp_pos)
                    active_ghost_dists.append(dist)
                except Exception:
                    continue

            # Condition (a): active ghost within 3 AND no 2-step escape.
            if active_ghost_dists and min(active_ghost_dists) <= 3:
                # Check for a 2-step escape: a legal action that leads to a
                # cell with no active ghost within 3.
                try:
                    legal = gameState.getLegalActions(self.index)
                    has_escape = False
                    for a in legal:
                        if a == Directions.STOP:
                            continue
                        try:
                            succ1 = gameState.generateSuccessor(self.index, a)
                            succ_pos = succ1.getAgentState(self.index).getPosition()
                            if succ_pos is None:
                                continue
                            succ_pos = (int(succ_pos[0]), int(succ_pos[1]))
                            # Check if ghosts are still within 3 at successor.
                            still_threatened = any(
                                self.getMazeDistance(succ_pos, opp_pos) <= 3
                                for opp_pos in opponentPositions.values()
                                if opp_pos is not None
                            )
                            if not still_threatened:
                                has_escape = True
                                break
                        except Exception:
                            continue
                    if not has_escape:
                        return True  # trigger (a)
                except Exception:
                    pass

            # Condition (b): numCarrying >= 5 AND capsule closer than home + 2.
            if numCarrying >= 5:
                try:
                    homeFrontier = self.homeFrontier if self.homeFrontier else []
                    if homeFrontier and capsuleList:
                        min_cap_dist = min(self.getMazeDistance(myPos, c) for c in capsuleList)
                        min_home_dist = min(self.getMazeDistance(myPos, h) for h in homeFrontier)
                        if min_cap_dist < min_home_dist + 2:
                            return True  # trigger (b)
                except Exception:
                    pass

            # Condition (c): current pos is bottleneck AND active ghost within 5.
            try:
                bottlenecks = self.bottlenecks if self.bottlenecks else frozenset()
                if myPos in bottlenecks and active_ghost_dists and min(active_ghost_dists) <= 5:
                    return True  # trigger (c)
            except Exception:
                pass

        except Exception:
            pass

        return False

    def _chooseActionImpl(self, gameState):
        """Like ReflexTunedAgent but adjusts f_distToCapsule weight based on trigger."""
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        # Get base weights and adjust capsule weight.
        try:
            role = TEAM.role.get(self.index, 'OFFENSE')
        except Exception:
            role = 'OFFENSE'

        base_weights = SEED_WEIGHTS_OFFENSIVE if role != 'DEFENSE' else SEED_WEIGHTS_DEFENSIVE
        weights = dict(base_weights)  # shallow copy

        try:
            trigger = self._capsule_trigger(gameState)
        except Exception:
            trigger = False

        weights['f_distToCapsule'] = _CAPSULE_WEIGHT_HIGH if trigger else _CAPSULE_WEIGHT_LOW

        best_score = float('-inf')
        best_action = None

        ordered = sorted(legal, key=lambda a: _ACTION_PREFERENCE.index(a)
                         if a in _ACTION_PREFERENCE else len(_ACTION_PREFERENCE))

        for action in ordered:
            try:
                feats = extract_features(self, gameState, action)
                score = sum(weights.get(f, 0.0) * v for f, v in feats.items())
            except Exception:
                score = float('-inf')
            if score > best_score:
                best_score = score
                best_action = action

        if best_action is None or best_action not in legal:
            non_stop = [a for a in legal if a != Directions.STOP]
            return non_stop[0] if non_stop else Directions.STOP

        return best_action
