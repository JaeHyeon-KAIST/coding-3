# zoo_reflex_A1_D2.py
# -------------------
# A1 champion weights + D2 capsule tactics state machine.
#
# Combines three CCG-sourced ideas:
#   (1) D2 timing rule (pm17 plan): don't eat capsule immediately when far
#       from a threatening ghost — waste of SCARED_TIME=40.
#   (2) Gemini capsule proxy camping: stay ADJACENT to capsule (not ON it,
#       since capture.py auto-consumes on step-through — verified capture.py
#       lines 555-566). Only step onto capsule when ghost is within threshold.
#   (3) Codex post-capsule dead-end trap: once enemy is scared, chase toward
#       dead-end cells so they have no escape before scaredTimer runs out.
#
# State machine (evaluated each turn):
#   IDLE                  -> default A1 argmax
#   PRE_CAPSULE_WAIT      -> adjacent to capsule, no close threat, no lead
#                             urgency. Override: pick action that KEEPS us
#                             adjacent (not stepping onto capsule).
#   POST_CAPSULE_HUNT     -> scared enemy ghost exists. Override: chase
#                             toward ghost, with dead-end cornering bonus.
#
# Transitions are pure functions of current gameState + snapshot — no per-
# agent persistent state beyond base class. Idempotent, safe under CS188's
# sequential turn model.

from __future__ import annotations

from zoo_core import TEAM, Directions
from zoo_reflex_A1 import ReflexA1Agent

# Trigger thresholds (pm20 defaults; tune later after larger HTH).
D2_GHOST_CLOSE_THRESHOLD = 5      # adjacent+no-ghost-within-this -> PRE_CAPSULE_WAIT
D2_EAT_NOW_THRESHOLD = 3           # ghost within this -> transition to eat (no override)
D2_HUNT_DIST_MAX = 15              # chase only if scared ghost within this distance
D2_DEADEND_BONUS = 5.0             # successor-in-deadend heuristic bonus
D2_LEAD_URGENCY_TIMELEFT = 300     # if leading+low timeleft, skip camping — bank score


class ReflexA1D2Agent(ReflexA1Agent):
    """A1 weights + capsule proxy-camp + post-capsule dead-end hunt."""

    STATE_IDLE = 0
    STATE_PRE_CAPSULE_WAIT = 1
    STATE_POST_CAPSULE_HUNT = 2

    # ---------------- state classification -------------------------

    def _classify_state(self, gameState, snap) -> int:
        """Return one of STATE_*. Never raises."""
        try:
            my_pos = snap.get("myPos")
            if my_pos is None:
                return self.STATE_IDLE

            # (A) POST_CAPSULE_HUNT takes precedence — scared enemy exists?
            nearest_scared_dist = float("inf")
            for opp_idx, opp_pos in (snap.get("opponentPositions") or {}).items():
                if opp_pos is None:
                    continue
                try:
                    opp_state = gameState.getAgentState(opp_idx)
                    scared = int(getattr(opp_state, "scaredTimer", 0) or 0)
                    if scared <= 0:
                        continue
                    d = self.getMazeDistance(my_pos, opp_pos)
                    if d < nearest_scared_dist:
                        nearest_scared_dist = d
                except Exception:
                    continue
            if nearest_scared_dist <= D2_HUNT_DIST_MAX:
                return self.STATE_POST_CAPSULE_HUNT

            # Skip camping if leading + low timeleft (D3-aligned; bank the score).
            try:
                score = int(self.getScore(gameState))
                timeleft = int(getattr(gameState.data, "timeleft", 1200) or 1200)
                if score >= 1 and timeleft < D2_LEAD_URGENCY_TIMELEFT:
                    return self.STATE_IDLE
            except Exception:
                pass

            # (B) PRE_CAPSULE_WAIT — adjacent to enemy's capsule AND no close
            # active ghost.
            try:
                capsules = list(self.getCapsules(gameState))
            except Exception:
                capsules = []
            if not capsules:
                return self.STATE_IDLE

            adjacent_to_capsule = False
            for cap in capsules:
                if self.getMazeDistance(my_pos, cap) == 1:
                    adjacent_to_capsule = True
                    break
            if not adjacent_to_capsule:
                return self.STATE_IDLE

            # Active ghost close? If yes, let A1 eat capsule (exit camp).
            for opp_idx, opp_pos in (snap.get("opponentPositions") or {}).items():
                if opp_pos is None:
                    continue
                try:
                    opp_state = gameState.getAgentState(opp_idx)
                    if getattr(opp_state, "isPacman", False):
                        continue
                    scared = int(getattr(opp_state, "scaredTimer", 0) or 0)
                    if scared > 0:
                        continue
                    d = self.getMazeDistance(my_pos, opp_pos)
                    if d <= D2_EAT_NOW_THRESHOLD:
                        return self.STATE_IDLE  # eat now — trigger A1 evaluator
                except Exception:
                    continue

            # No close active ghost AND ghost must be "somewhere" within the
            # wider threshold to make waiting meaningful. If no ghost visible
            # at all, camping is pointless — ghosts aren't in sensor range.
            any_ghost_visible_mid_range = False
            for opp_idx, opp_pos in (snap.get("opponentPositions") or {}).items():
                if opp_pos is None:
                    continue
                try:
                    opp_state = gameState.getAgentState(opp_idx)
                    if getattr(opp_state, "isPacman", False):
                        continue
                    scared = int(getattr(opp_state, "scaredTimer", 0) or 0)
                    if scared > 0:
                        continue
                    d = self.getMazeDistance(my_pos, opp_pos)
                    if d <= D2_GHOST_CLOSE_THRESHOLD + 5:
                        any_ghost_visible_mid_range = True
                        break
                except Exception:
                    continue
            if not any_ghost_visible_mid_range:
                return self.STATE_IDLE  # camping doesn't help if no visible target

            return self.STATE_PRE_CAPSULE_WAIT
        except Exception:
            return self.STATE_IDLE

    # ---------------- PRE_CAPSULE_WAIT action ---------------------

    def _pre_capsule_wait_action(self, gameState, snap):
        """Pick action that keeps us adjacent to capsule without stepping onto it.
        Returns legal action or None (falls back to A1 evaluator)."""
        try:
            my_pos = snap.get("myPos")
            if my_pos is None:
                return None
            capsules = list(self.getCapsules(gameState))
            if not capsules:
                return None

            legal = gameState.getLegalActions(self.index)
            if not legal:
                return None

            # Rank actions by successor position that is (a) NOT on a capsule,
            # (b) still adjacent to a capsule (dist 1), (c) prefer STOP when
            # already well-positioned.
            try:
                from util import nearestPoint
            except Exception:
                return None

            ranked = []  # (score, action)
            for action in legal:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                    succ_pos_raw = succ.getAgentState(self.index).getPosition()
                    if succ_pos_raw is None:
                        continue
                    succ_pos = nearestPoint(succ_pos_raw)
                    succ_pos = (int(succ_pos[0]), int(succ_pos[1]))
                except Exception:
                    continue

                if succ_pos in capsules:
                    continue  # would eat the capsule — skip
                min_dist_to_cap = min(
                    self.getMazeDistance(succ_pos, cap) for cap in capsules
                )
                # Want adjacent (dist=1). Prefer STOP over oscillating.
                score = -abs(min_dist_to_cap - 1) * 10.0
                if action == Directions.STOP and min_dist_to_cap == 1:
                    score += 2.0  # prefer holding position
                ranked.append((score, action))

            if not ranked:
                return None
            # argmax by score
            ranked.sort(key=lambda t: (-t[0], Directions.STOP == t[1]))
            return ranked[0][1]
        except Exception:
            return None

    # ---------------- POST_CAPSULE_HUNT action --------------------

    def _post_capsule_hunt_action(self, gameState, snap):
        """Chase nearest scared enemy ghost; bonus for successors in dead-ends.
        Returns legal action or None."""
        try:
            my_pos = snap.get("myPos")
            if my_pos is None:
                return None

            scared_positions = []
            for opp_idx, opp_pos in (snap.get("opponentPositions") or {}).items():
                if opp_pos is None:
                    continue
                try:
                    opp_state = gameState.getAgentState(opp_idx)
                    if int(getattr(opp_state, "scaredTimer", 0) or 0) > 0:
                        scared_positions.append(opp_pos)
                except Exception:
                    continue
            if not scared_positions:
                return None

            try:
                from util import nearestPoint
            except Exception:
                return None

            legal = gameState.getLegalActions(self.index)
            if not legal:
                return None

            dead_ends = self.deadEnds if self.deadEnds else frozenset()
            best_action = None
            best_score = float("-inf")
            for action in legal:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                    succ_pos_raw = succ.getAgentState(self.index).getPosition()
                    if succ_pos_raw is None:
                        continue
                    succ_pos = nearestPoint(succ_pos_raw)
                    succ_pos = (int(succ_pos[0]), int(succ_pos[1]))
                    min_dist = min(
                        self.getMazeDistance(succ_pos, g) for g in scared_positions
                    )
                    # Closer to scared ghost -> higher score.
                    score = -float(min_dist)
                    # Trap bonus: moving into dead-end when ghost is near.
                    if succ_pos in dead_ends and min_dist <= 4:
                        score += D2_DEADEND_BONUS
                    if score > best_score:
                        best_score = score
                        best_action = action
                except Exception:
                    continue
            return best_action
        except Exception:
            return None

    # ---------------- main override --------------------------------

    def _chooseActionImpl(self, gameState):
        try:
            snap = self.snapshot(gameState)
        except Exception:
            return super()._chooseActionImpl(gameState)

        try:
            state = self._classify_state(gameState, snap)
        except Exception:
            state = self.STATE_IDLE

        if state == self.STATE_POST_CAPSULE_HUNT:
            action = self._post_capsule_hunt_action(gameState, snap)
            if action is not None:
                return action
        elif state == self.STATE_PRE_CAPSULE_WAIT:
            action = self._pre_capsule_wait_action(gameState, snap)
            if action is not None:
                return action

        return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexA1D2Agent", second="ReflexA1D2Agent"):
    return [ReflexA1D2Agent(firstIndex), ReflexA1D2Agent(secondIndex)]
