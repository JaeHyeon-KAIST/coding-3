# monster_rule_expert.py
# ----------------------
# Monster reference agent #1 — Territorial Defender (expert-system / rule-based).
# EVALUATION-ONLY. Never submitted. Used in the training opponent pool (STRATEGY §6.9).
#
# Strategic profile: hard defensive team. Both agents are DEFENDERS. They
# stake out chokepoints on the home-frontier, intercept any visible enemy
# Pacman, block between food clusters and the boundary, and rarely attack.
# Attacks only trigger on an emergency (score deficit < -10, no visible
# invader, and a tick counter indicates the opponent is stalling / cashing-in
# slowly).
#
# Decision rule is a hand-authored priority list (no search tree, no MCTS).
# Rules fire in strict order — the first matching rule decides the action.
#
# 1. Visible invader on our side  -> intercept (shortest path)
# 2. Enemy Pacman adjacent to our food cluster -> block between cluster & boundary
# 3. Default: patrol rotation among chokepoints (home-frontier bottlenecks)
# 4. Scared  -> flee perpendicular to the incoming enemy
# 5. Emergency attack: score lead < -10 AND no invader AND >100 ticks  ->
#    lower-index agent raids the nearest enemy food cluster
#
# Layout awareness: if the home-frontier has few cells (narrow central
# corridor), at least one agent stakes out the narrowest frontier cell.
#
# Inherits CoreCaptureAgent for crash-proof wrapping, APSP and bottlenecks.

from __future__ import annotations

import random

from zoo_core import CoreCaptureAgent, TEAM, Directions


# ---------------------------------------------------------------------------
# createTeam factory — required by capture.py
# ---------------------------------------------------------------------------

def createTeam(firstIndex, secondIndex, isRed,
               first='MonsterRuleExpertAgent', second='MonsterRuleExpertAgent'):
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


# Emergency-attack triggers.
_EMERGENCY_DEFICIT = -10
_EMERGENCY_TICK_THRESHOLD = 100
# Narrow-corridor heuristic: if home-frontier has at most this many open cells,
# the layout is a "narrow corridor" and at least one agent should stake it out.
_NARROW_FRONTIER_CELLS = 6


class MonsterRuleExpertAgent(CoreCaptureAgent):
    """Territorial defender — rule-based, priority-ordered decision list."""

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _best_step_toward(self, gameState, target):
        """Return the legal action that most reduces maze distance to `target`.

        Uses generateSuccessor to test each legal action. STOP is only
        considered if no non-STOP action legally exists. Returns None on any
        internal failure so the caller can fall through to the next rule.
        """
        try:
            if target is None:
                return None
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return None
            non_stop = [a for a in legal if a != Directions.STOP]
            if not non_stop:
                return Directions.STOP
            best_action = None
            best_dist = float('inf')
            for action in non_stop:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                    pos = succ.getAgentState(self.index).getPosition()
                    if pos is None:
                        continue
                    pos = (int(pos[0]), int(pos[1]))
                    d = self.getMazeDistance(pos, target)
                    if d < best_dist:
                        best_dist = d
                        best_action = action
                except Exception:
                    continue
            return best_action
        except Exception:
            return None

    def _best_step_away(self, gameState, source):
        """Return the legal action that most increases maze distance from `source`."""
        try:
            if source is None:
                return None
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return None
            non_stop = [a for a in legal if a != Directions.STOP]
            if not non_stop:
                return Directions.STOP
            best_action = None
            best_dist = -1
            for action in non_stop:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                    pos = succ.getAgentState(self.index).getPosition()
                    if pos is None:
                        continue
                    pos = (int(pos[0]), int(pos[1]))
                    d = self.getMazeDistance(pos, source)
                    if d > best_dist:
                        best_dist = d
                        best_action = action
                except Exception:
                    continue
            return best_action
        except Exception:
            return None

    def _visible_invaders(self, gameState):
        """Return list of (idx, pos) for opponents that are currently Pacman
        and whose position is observable to us."""
        out = []
        try:
            for idx in self.getOpponents(gameState):
                try:
                    pos = gameState.getAgentPosition(idx)
                    if pos is None:
                        continue
                    opp_state = gameState.getAgentState(idx)
                    if getattr(opp_state, 'isPacman', False):
                        out.append((idx, (int(pos[0]), int(pos[1]))))
                except Exception:
                    continue
        except Exception:
            pass
        return out

    def _visible_enemies(self, gameState):
        """Return list of (idx, pos, isPacman) for all observable opponents."""
        out = []
        try:
            for idx in self.getOpponents(gameState):
                try:
                    pos = gameState.getAgentPosition(idx)
                    if pos is None:
                        continue
                    opp_state = gameState.getAgentState(idx)
                    is_pac = bool(getattr(opp_state, 'isPacman', False))
                    out.append((idx, (int(pos[0]), int(pos[1])), is_pac))
                except Exception:
                    continue
        except Exception:
            pass
        return out

    def _nearest_home_cell_to(self, target):
        """Nearest home-frontier cell to `target`. Returns None if no frontier
        or target."""
        try:
            if target is None:
                return None
            frontier = self.homeFrontier if self.homeFrontier else []
            if not frontier:
                return None
            return min(frontier, key=lambda c: self.getMazeDistance(c, target))
        except Exception:
            return None

    def _food_cluster_center(self, gameState):
        """Return a cell that roughly represents the largest of our defended
        food clusters (its centroid, rounded to nearest non-wall cell).
        Returns None if no defended food or on failure."""
        try:
            defend = self.getFoodYouAreDefending(gameState).asList()
            if not defend:
                return None
            cx = sum(p[0] for p in defend) / float(len(defend))
            cy = sum(p[1] for p in defend) / float(len(defend))
            # Snap to the defended food cell closest to the centroid.
            centroid = (int(round(cx)), int(round(cy)))
            return min(defend, key=lambda p: (p[0]-centroid[0])**2 + (p[1]-centroid[1])**2)
        except Exception:
            return None

    def _patrol_anchor(self, gameState):
        """Pick a chokepoint on our home-frontier to patrol.

        Preference order:
          (1) frontier cells that are also bottlenecks (articulation points),
          (2) otherwise the "middle" cell of the frontier (narrowest stake-out),
          (3) otherwise the first frontier cell.
        Rotates across ticks so the two teammates don't both sit on the same
        cell — we deterministically offset by self.index.
        """
        try:
            frontier = self.homeFrontier if self.homeFrontier else []
            if not frontier:
                return None
            bottlenecks = self.bottlenecks if self.bottlenecks else frozenset()
            frontier_bottlenecks = [c for c in frontier if c in bottlenecks]
            pool = frontier_bottlenecks if frontier_bottlenecks else frontier
            # Narrow-corridor hint: sort by y so the teammates split N/S.
            pool = sorted(pool, key=lambda c: c[1])
            tick = int(getattr(TEAM, 'tick', 0) or 0)
            # Deterministic offset = self.index makes the two teammates pick
            # different cells whenever the pool has >=2 entries.
            offset = (tick // 12) + (self.index % max(len(pool), 1))
            return pool[offset % len(pool)]
        except Exception:
            try:
                return self.homeFrontier[0] if self.homeFrontier else None
            except Exception:
                return None

    def _nearest_enemy_food(self, gameState):
        """Nearest enemy food cell (we would eat this if attacking). None if
        no food visible or position unknown."""
        try:
            my_pos = gameState.getAgentPosition(self.index)
            if my_pos is None:
                return None
            food = self.getFood(gameState).asList()
            if not food:
                return None
            return min(food, key=lambda f: self.getMazeDistance(my_pos, f))
        except Exception:
            return None

    def _am_scared(self, gameState):
        try:
            my_state = gameState.getAgentState(self.index)
            return int(getattr(my_state, 'scaredTimer', 0) or 0) > 0
        except Exception:
            return False

    def _team_score_for_me(self, gameState):
        """Return our team's signed score (positive = we lead)."""
        try:
            raw = gameState.getScore()
            return raw if self.red else -raw
        except Exception:
            return 0

    # ------------------------------------------------------------------
    # _chooseActionImpl
    # ------------------------------------------------------------------

    def _chooseActionImpl(self, gameState):
        # Monotonic tick increment across both teammates.
        try:
            TEAM.tick = int(getattr(TEAM, 'tick', 0) or 0) + 1
        except Exception:
            pass

        try:
            legal = gameState.getLegalActions(self.index)
        except Exception:
            legal = []
        if not legal:
            return Directions.STOP

        try:
            my_pos = gameState.getAgentPosition(self.index)
            if my_pos is not None:
                my_pos = (int(my_pos[0]), int(my_pos[1]))
        except Exception:
            my_pos = None

        invaders = self._visible_invaders(gameState)
        scared = self._am_scared(gameState)

        # -----------------------------------------------------------
        # Rule 4 (promoted when scared): flee perpendicular from enemy.
        # A scared ghost that walks into an invader hands over capsule
        # momentum — so scared state overrides the chase rule.
        # -----------------------------------------------------------
        if scared and invaders:
            try:
                # Closest invader.
                inv_pos = min(invaders, key=lambda p: self.getMazeDistance(my_pos, p[1]))[1] \
                    if my_pos is not None else invaders[0][1]
                fleer = self._best_step_away(gameState, inv_pos)
                if fleer and fleer in legal:
                    return fleer
            except Exception:
                pass
            # If flee failed, fall through to other rules (no STOP here).

        # -----------------------------------------------------------
        # Rule 1: visible invader — intercept (closest one).
        # -----------------------------------------------------------
        if invaders and not scared:
            try:
                if my_pos is not None:
                    closest = min(invaders, key=lambda p: self.getMazeDistance(my_pos, p[1]))
                else:
                    closest = invaders[0]
                action = self._best_step_toward(gameState, closest[1])
                if action and action in legal:
                    return action
            except Exception:
                pass

        # -----------------------------------------------------------
        # Rule 2: enemy Pacman adjacent to our food cluster.
        # If an enemy ghost is hovering near a food cluster (dist ≤ 3
        # from a defending-food cell), move to the blocker cell between
        # the cluster and the home-frontier.
        # -----------------------------------------------------------
        try:
            defend_food = self.getFoodYouAreDefending(gameState).asList()
            if defend_food and my_pos is not None:
                # Find enemies (ghost or Pacman) near any defended food cell.
                enemies = self._visible_enemies(gameState)
                threatened = None
                best_d = 4  # threshold "adjacent"
                for _, epos, _ in enemies:
                    for fc in defend_food:
                        d = self.getMazeDistance(epos, fc)
                        if d < best_d:
                            best_d = d
                            threatened = fc
                if threatened is not None:
                    anchor = self._nearest_home_cell_to(threatened)
                    # Move toward the home-side bottleneck between cluster and boundary.
                    if anchor is not None:
                        action = self._best_step_toward(gameState, anchor)
                        if action and action in legal:
                            return action
        except Exception:
            pass

        # -----------------------------------------------------------
        # Rule 5: emergency attack — only if we're badly losing and
        # have had no invader for a while. Only one agent (lower index)
        # becomes the raider; the other keeps patrolling.
        # -----------------------------------------------------------
        try:
            score = self._team_score_for_me(gameState)
            tick = int(getattr(TEAM, 'tick', 0) or 0)
            team_indices = list(self.getTeam(gameState))
            is_raider = bool(team_indices) and (self.index == min(team_indices))
            if (score < _EMERGENCY_DEFICIT
                    and not invaders
                    and tick > _EMERGENCY_TICK_THRESHOLD
                    and is_raider):
                target = self._nearest_enemy_food(gameState)
                if target is not None:
                    action = self._best_step_toward(gameState, target)
                    if action and action in legal:
                        return action
        except Exception:
            pass

        # -----------------------------------------------------------
        # Rule 3: default patrol — rotate among chokepoints.
        # -----------------------------------------------------------
        try:
            anchor = self._patrol_anchor(gameState)
            if anchor is not None:
                # If we're already at the anchor, pick a neighbouring anchor
                # (to avoid sitting on STOP).
                if my_pos == anchor:
                    frontier = self.homeFrontier if self.homeFrontier else []
                    if frontier:
                        # Nearest frontier cell that isn't us.
                        alt = [c for c in frontier if c != my_pos]
                        if alt:
                            anchor = random.choice(alt)
                action = self._best_step_toward(gameState, anchor)
                if action and action in legal:
                    return action
        except Exception:
            pass

        # Last-ditch: prefer any non-STOP legal action.
        non_stop = [a for a in legal if a != Directions.STOP]
        if non_stop:
            return non_stop[0]
        return Directions.STOP
