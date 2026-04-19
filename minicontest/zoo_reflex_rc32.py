# zoo_reflex_rc32.py
# ------------------
# rc32: Pincer maneuver overlay on A1 champion.
#
# When exactly one invader is visible and we have BOTH defenders (or one
# defender + one offense that can turn ghost on home side) capable of
# reaching the invader, we deliberately approach from opposite sides:
# the invader's only escape direction is back toward their home, and we
# converge from both sides of that path.
#
# Heuristic implementation (no full MCTS):
#   1. Find the visible invader.
#   2. Compute the invader's shortest path to their nearest home cell
#      (approximated by column = midline on their side).
#   3. Pick TWO "pincer anchors" — cells along that path on opposite
#      sides of the invader (one ahead toward their home, one behind
#      blocking their advance into our food).
#   4. This agent goes to whichever anchor minimizes (our arrival time
#      − teammate arrival time) when teammate takes the other.
#
# Fires only when:
#   - exactly one invader visible,
#   - both of our agents have known positions,
#   - we're not scared (we can threaten kill),
#   - current role allows engagement (any role — offense can return).
#
# Everything is top-K-safe within A1's action ranking (tolerance band)
# just like rc04/rc06/rc08.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent
from zoo_features import evaluate
from game import Directions


RC32_TOP_K = 3
RC32_A1_TOL_FRAC = 0.05


class ReflexRC32Agent(ReflexA1Agent):
    """A1 champion + 2-agent pincer maneuver against single invader."""

    def _pincer_target(self, gameState):
        """Return (target_cell_for_me, reason) or (None, None)."""
        try:
            my_pos = gameState.getAgentPosition(self.index)
            if my_pos is None:
                return None
            my_state = gameState.getAgentState(self.index)
            if int(getattr(my_state, "scaredTimer", 0) or 0) > 0:
                return None  # scared ghost can't threaten

            my_team = sorted(list(self.getTeam(gameState)))
            mates = [i for i in my_team if i != self.index]
            if not mates:
                return None
            mate = mates[0]
            try:
                mate_pos = gameState.getAgentPosition(mate)
            except Exception:
                mate_pos = None
            if mate_pos is None:
                return None

            # Find exactly one visible invader.
            invaders = []
            for opp_idx in self.getOpponents(gameState):
                try:
                    p = gameState.getAgentPosition(opp_idx)
                    if p is None:
                        continue
                    st = gameState.getAgentState(opp_idx)
                    if getattr(st, "isPacman", False):
                        invaders.append(p)
                except Exception:
                    continue
            if len(invaders) != 1:
                return None
            inv_pos = invaders[0]
            inv_x, inv_y = int(inv_pos[0]), int(inv_pos[1])

            walls = gameState.getWalls()
            W, H = walls.width, walls.height

            # Enemy home column (where invader wants to retreat to).
            if self.red:
                enemy_home_x = W // 2
            else:
                enemy_home_x = W // 2 - 1

            # Two candidate anchor cells near the invader.
            # Anchor A ("ahead") — between invader and enemy home (escape cut).
            # Anchor B ("behind") — between invader and our food (advance cut).
            # Approximated by stepping along x toward enemy_home (anchor A)
            # and away (anchor B), keeping y=invader's y.
            dx = 1 if enemy_home_x > inv_x else -1
            anchor_a = None
            anchor_b = None
            for step in range(2, 6):
                ax, ay = inv_x + step * dx, inv_y
                if 0 <= ax < W and 0 <= ay < H and not walls[ax][ay]:
                    anchor_a = (ax, ay)
                    break
            for step in range(2, 6):
                bx, by = inv_x - step * dx, inv_y
                if 0 <= bx < W and 0 <= by < H and not walls[bx][by]:
                    anchor_b = (bx, by)
                    break
            if anchor_a is None or anchor_b is None:
                return None

            # Assign anchors: I take the one I can reach faster than my
            # mate WOULD take the other.
            d_me_a = self.getMazeDistance(my_pos, anchor_a)
            d_me_b = self.getMazeDistance(my_pos, anchor_b)
            d_mate_a = self.getMazeDistance(mate_pos, anchor_a)
            d_mate_b = self.getMazeDistance(mate_pos, anchor_b)
            # Option 1: me=A, mate=B. Cost = max(d_me_a, d_mate_b)
            # Option 2: me=B, mate=A. Cost = max(d_me_b, d_mate_a)
            opt1 = max(d_me_a, d_mate_b)
            opt2 = max(d_me_b, d_mate_a)
            return anchor_a if opt1 <= opt2 else anchor_b
        except Exception:
            return None

    def _chooseActionImpl(self, gameState):
        try:
            target = self._pincer_target(gameState)
        except Exception:
            target = None
        if target is None:
            return super()._chooseActionImpl(gameState)

        try:
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP
            weights = self._get_weights()
            scored = []
            for action in legal:
                try:
                    s = evaluate(self, gameState, action, weights)
                except Exception:
                    s = float("-inf")
                scored.append((s, action))
            scored.sort(key=lambda sa: sa[0], reverse=True)
            if not scored or scored[0][0] == float("-inf"):
                return super()._chooseActionImpl(gameState)

            top_score = scored[0][0]
            tol = max(abs(top_score) * RC32_A1_TOL_FRAC, 1.0)
            K = min(RC32_TOP_K, len(scored))
            candidates = [a for s, a in scored[:K]
                          if s >= top_score - tol]
            if len(candidates) < 2:
                return scored[0][1]

            from util import nearestPoint
            best_action = candidates[0]
            best_dist = float("inf")
            for action in candidates:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                    raw = succ.getAgentState(self.index).getPosition()
                    if raw is None:
                        continue
                    sp = nearestPoint(raw)
                    sp = (int(sp[0]), int(sp[1]))
                    d = self.getMazeDistance(sp, target)
                    if d < best_dist:
                        best_dist = d
                        best_action = action
                except Exception:
                    continue
            return best_action
        except Exception:
            return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC32Agent", second="ReflexRC32Agent"):
    return [ReflexRC32Agent(firstIndex), ReflexRC32Agent(secondIndex)]
