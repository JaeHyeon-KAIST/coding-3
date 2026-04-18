# zoo_reflex_rc09.py
# ------------------
# rc09: A1 + 4 new features → 24-dim composite (vs 20-dim A1).
#
# A1 was CEM-evolved on the 17-dim reflex weights (before pm18's B1 added
# f_scaredGhostChase/f_returnUrgency/f_teammateSpread, bringing the shared
# extractor to 20 features). rc09 extends the extractor to 24 features by
# adding four more heuristic-weighted fields that capture signals A1's
# evolution never saw:
#
#   f_enemyDistToHome  — how far the closest enemy Pacman is from their home.
#                        Larger = they're deep in our side, defender gains
#                        time to intercept; smaller = shallow raid / bait.
#   f_ourCarrierDist   — my TEAMMATE's carrier distance to home (not mine).
#                        Signals "my teammate is hauling, I should escort /
#                        cover" rather than dogpile onto the same food path.
#   f_capsuleProximity — a capsule-availability multiplier when an active
#                        ghost is also within a threat distance. Different
#                        from A1's f_distToCapsule (which is always on).
#   f_chokePoint       — binary: am I standing on one of the approximate
#                        articulation points (self.bottlenecks)?
#
# The original 20 features use A1's evolved weights. The 4 new features
# use hand-tuned seed weights (no CEM re-run). This is a stopgap diversity
# candidate — the "proper" path is Order 3/4 evolving on the full 24-dim
# vector, which is future work.
#
# Design note: to avoid breaking the shared `zoo_features.extract_features`
# (used by every other agent including A1 flattened submission), rc09
# delegates to the base extractor and then augments the dict. No change to
# the framework-shared module.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import extract_features as _base_extract_features
from game import Directions


# Hand-tuned seed weights for the 4 new features. Chosen to be O(10) so
# they participate meaningfully next to A1's |w|≈10-100 range but don't
# dominate. Offensive and defensive versions diverge mainly on
# f_enemyDistToHome (matters more for defense).
_RC09_EXTRA_OFF = {
    "f_enemyDistToHome": 5.0,
    "f_ourCarrierDist": 3.0,
    "f_capsuleProximity": 8.0,
    "f_chokePoint": 1.0,
}
_RC09_EXTRA_DEF = {
    "f_enemyDistToHome": 15.0,
    "f_ourCarrierDist": 1.0,
    "f_capsuleProximity": 5.0,
    "f_chokePoint": 3.0,
}

_CAPSULE_GHOST_THRESHOLD = 4       # "active ghost near" distance
_ENEMY_HOME_MAX = 30.0              # distance cap for stable normalization


def _extract_rc09_extra(agent, gameState, action):
    """Compute the 4 new rc09-only feature values for the successor of
    (gameState, action). Returns a dict. All errors → 0.0."""
    extra = {
        "f_enemyDistToHome": 0.0,
        "f_ourCarrierDist": 0.0,
        "f_capsuleProximity": 0.0,
        "f_chokePoint": 0.0,
    }
    try:
        # Walk the successor state, matching zoo_features.extract_features.
        successor = gameState.generateSuccessor(agent.index, action)
        try:
            from util import nearestPoint
            pos_raw = successor.getAgentState(agent.index).getPosition()
            if pos_raw != nearestPoint(pos_raw):
                successor = successor.generateSuccessor(agent.index, action)
        except Exception:
            pass

        try:
            my_pos_raw = successor.getAgentState(agent.index).getPosition()
            my_pos = (int(my_pos_raw[0]), int(my_pos_raw[1])) if my_pos_raw else None
        except Exception:
            my_pos = None
    except Exception:
        return extra

    # --- f_enemyDistToHome ---
    # Nearest enemy Pacman's distance to their home column.
    try:
        walls = successor.getWalls()
        width = walls.width
        # Enemy home column = NOT our side.
        if agent.red:
            enemy_home_x = width // 2  # blue side first column
        else:
            enemy_home_x = width // 2 - 1  # red side last column
        ed = float("inf")
        for opp_idx in agent.getOpponents(successor):
            try:
                opp_pos = successor.getAgentPosition(opp_idx)
                if opp_pos is None:
                    continue
                opp_state = successor.getAgentState(opp_idx)
                if not getattr(opp_state, "isPacman", False):
                    continue
                d_to_home = abs(int(opp_pos[0]) - enemy_home_x)
                if d_to_home < ed:
                    ed = d_to_home
            except Exception:
                continue
        if ed != float("inf"):
            extra["f_enemyDistToHome"] = min(ed, _ENEMY_HOME_MAX) / _ENEMY_HOME_MAX
    except Exception:
        pass

    # --- f_ourCarrierDist ---
    try:
        my_team = list(agent.getTeam(successor))
        home = list(agent.homeFrontier) if agent.homeFrontier else []
        if home:
            for tm in my_team:
                if tm == agent.index:
                    continue
                try:
                    tm_state = successor.getAgentState(tm)
                    carry = int(getattr(tm_state, "numCarrying", 0) or 0)
                    if carry <= 0:
                        continue
                    tm_pos = successor.getAgentPosition(tm)
                    if tm_pos is None:
                        continue
                    d = min(agent.getMazeDistance(tm_pos, h) for h in home)
                    extra["f_ourCarrierDist"] = float(carry) / max(d, 1)
                    break
                except Exception:
                    continue
    except Exception:
        pass

    # --- f_capsuleProximity ---
    try:
        if my_pos is not None:
            capsules = list(agent.getCapsules(successor))
            if capsules:
                ghost_close = False
                for opp_idx in agent.getOpponents(successor):
                    try:
                        opp_pos = successor.getAgentPosition(opp_idx)
                        if opp_pos is None:
                            continue
                        opp_state = successor.getAgentState(opp_idx)
                        if getattr(opp_state, "isPacman", False):
                            continue
                        if int(getattr(opp_state, "scaredTimer", 0) or 0) > 0:
                            continue
                        if agent.getMazeDistance(my_pos, opp_pos) <= _CAPSULE_GHOST_THRESHOLD:
                            ghost_close = True
                            break
                    except Exception:
                        continue
                if ghost_close:
                    d_cap = min(agent.getMazeDistance(my_pos, c) for c in capsules)
                    extra["f_capsuleProximity"] = 1.0 / max(d_cap, 1)
    except Exception:
        pass

    # --- f_chokePoint ---
    try:
        bns = agent.bottlenecks if agent.bottlenecks else frozenset()
        if my_pos is not None and my_pos in bns:
            extra["f_chokePoint"] = 1.0
    except Exception:
        pass

    return extra


class ReflexRC09Agent(ReflexA1Agent):
    """A1 champion + 4 new heuristic-weighted features."""

    def _get_weights(self):
        base = super()._get_weights()
        try:
            role = TEAM.role.get(self.index, "OFFENSE")
        except Exception:
            role = "OFFENSE"
        extra = _RC09_EXTRA_DEF if role == "DEFENSE" else _RC09_EXTRA_OFF
        combined = dict(base)
        for k, v in extra.items():
            combined[k] = v
        return combined

    def _chooseActionImpl(self, gameState):
        # We do not override _chooseActionImpl; we override the scoring by
        # injecting the 4 extra features via a custom eval path.
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        weights = self._get_weights()

        best_score = float("-inf")
        best_action = None
        # Preference order consistent with ReflexTunedAgent's argmax ordering.
        try:
            from zoo_features import _ACTION_PREFERENCE
            ordered = sorted(
                legal,
                key=lambda a: (_ACTION_PREFERENCE.index(a)
                               if a in _ACTION_PREFERENCE
                               else len(_ACTION_PREFERENCE)),
            )
        except Exception:
            ordered = list(legal)

        for action in ordered:
            try:
                feats = _base_extract_features(self, gameState, action)
                extra = _extract_rc09_extra(self, gameState, action)
                feats.update(extra)
                score = sum(weights.get(k, 0.0) * v for k, v in feats.items())
            except Exception:
                score = float("-inf")
            if score > best_score:
                best_score = score
                best_action = action

        if best_action is None or best_action not in legal:
            non_stop = [a for a in legal if a != Directions.STOP]
            return non_stop[0] if non_stop else Directions.STOP
        return best_action


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC09Agent", second="ReflexRC09Agent"):
    return [ReflexRC09Agent(firstIndex), ReflexRC09Agent(secondIndex)]
