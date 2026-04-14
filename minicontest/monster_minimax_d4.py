# monster_minimax_d4.py
# ---------------------
# Monster reference agent #3 — Adaptive Exploiter (minimax α-β depth 4).
# EVALUATION-ONLY. Never submitted. Used in the training opponent pool (STRATEGY §6.9).
#
# Strategic profile: observe the opponent for the first 50 ticks, classify
# their playstyle as AGGRESSIVE (most of their time in our territory),
# DEFENSIVE (most of their time in their own territory), or BALANCED, then
# lock into a counter-strategy:
#
#   Enemy AGGRESSIVE  -> our team goes DEFENSIVE (both defend, heavy invader chase).
#   Enemy DEFENSIVE   -> our team goes AGGRESSIVE (both attack, capsule-heavy).
#   Enemy BALANCED    -> our team splits 1/1 but weights the attacker more.
#
# Classification is written into TEAM singleton once (tick ≥ 50), so both
# teammates agree. Before classification, agents play a baseline role split
# (lower-index OFFENSE, higher-index DEFENSE).
#
# Search: α-β minimax depth 4 with opponent reduction (closer enemy only,
# farther enemy frozen). Move ordering helps prune. Leaf evaluator uses
# SEED_WEIGHTS with per-strategy modulation.
#
# Time discipline: HARD DEPTH CAP ONLY. No signal, no time polling. This
# agent may be slow (≥1.5s/move on large layouts) — that is explicitly OK,
# per STRATEGY §6.9: "too slow for submission but fine for training."
#
# Inherits CoreCaptureAgent for crash-proof wrapping, APSP, frontier, etc.

from __future__ import annotations

import random

from zoo_core import CoreCaptureAgent, TEAM, Directions
from zoo_features import (
    evaluate,
    SEED_WEIGHTS_OFFENSIVE,
    SEED_WEIGHTS_DEFENSIVE,
)


# ---------------------------------------------------------------------------
# Configuration constants (hand-set monster values, NOT evolvable).
# ---------------------------------------------------------------------------
_DEPTH = 4
_OBSERVATION_WINDOW = 50  # ticks spent classifying the enemy
_AGGRESSIVE_RATIO = 0.30  # enemy-spent-in-our-territory fraction above this → AGGRESSIVE
_DEFENSIVE_RATIO = 0.10  # ...below this → DEFENSIVE; between is BALANCED

_NEG_INF = float('-inf')
_POS_INF = float('inf')


# ---------------------------------------------------------------------------
# createTeam factory
# ---------------------------------------------------------------------------

def createTeam(firstIndex, secondIndex, isRed,
               first='MonsterMinimaxD4Agent', second='MonsterMinimaxD4Agent'):
    return [eval(first)(firstIndex), eval(second)(secondIndex)]


# ---------------------------------------------------------------------------
# Weight construction per team strategy. Modulates SEED_WEIGHTS.
# ---------------------------------------------------------------------------

def _weights_team_defensive():
    """Both agents defend hard. Amplify invader chase. Dampen attack."""
    w = dict(SEED_WEIGHTS_DEFENSIVE)
    w['f_numInvaders'] = w['f_numInvaders'] * 2.0   # already -2000 → -4000
    w['f_invaderDist'] = w['f_invaderDist'] * 1.5   # chase harder
    w['f_onDefense'] = w['f_onDefense'] * 1.5
    w['f_patrolDist'] = w['f_patrolDist'] * 1.5
    w['f_distToFood'] = 0.0   # don't bother chasing food
    w['f_numCarrying'] = 0.0
    w['f_distToHome'] = 0.0
    return w


def _weights_team_aggressive():
    """Both agents attack hard. Amplify food and carrying. Capsule matters."""
    w = dict(SEED_WEIGHTS_OFFENSIVE)
    w['f_distToFood'] = w['f_distToFood'] * 1.5
    w['f_distToCapsule'] = w['f_distToCapsule'] * 2.0  # use capsule to bypass
    w['f_numCarrying'] = w['f_numCarrying'] * 2.0
    w['f_distToHome'] = w['f_distToHome'] * 0.5         # don't go home too soon
    w['f_ghostDist1'] = w['f_ghostDist1'] * 0.7         # accept more risk
    w['f_onDefense'] = 0.0
    w['f_numInvaders'] = 0.0
    return w


def _weights_balanced_offense():
    """Balanced-mode attacker: more aggressive than vanilla offense."""
    w = dict(SEED_WEIGHTS_OFFENSIVE)
    w['f_distToFood'] = w['f_distToFood'] * 1.25
    w['f_numCarrying'] = w['f_numCarrying'] * 1.5
    return w


def _weights_balanced_defense():
    """Balanced-mode defender: vanilla defense."""
    return dict(SEED_WEIGHTS_DEFENSIVE)


# ---------------------------------------------------------------------------
# Adaptive Exploiter agent
# ---------------------------------------------------------------------------

class MonsterMinimaxD4Agent(CoreCaptureAgent):
    """Minimax α-β depth 4 with a 50-tick opponent-observation preamble."""

    def __init__(self, index, timeForComputing=0.1):
        CoreCaptureAgent.__init__(self, index, timeForComputing)
        # Observation window counters. Written into TEAM singleton so both
        # teammates accumulate into the same dict.

    # ------------------------------------------------------------------
    # Observation & classification
    # ------------------------------------------------------------------

    def _obs(self):
        """Return the observation counters dict stored in TEAM. Creates one
        if missing. Uses attribute access (not items) so we do not collide
        with TEAM.role / TEAM.last_seen_enemy."""
        obs = getattr(TEAM, 'monster_minimax_obs', None)
        if obs is None:
            obs = {
                'enemy_pacman_ticks': 0,   # enemy observed as Pacman
                'enemy_ghost_ticks': 0,    # enemy observed as Ghost (home side)
                'total_obs_ticks': 0,      # total observation steps
                'strategy': None,          # 'DEFENSIVE'|'AGGRESSIVE'|'BALANCED'
                'classified_at_tick': None,
            }
            try:
                TEAM.monster_minimax_obs = obs
            except Exception:
                pass
        return obs

    def _update_observations(self, gameState):
        """Increment the TEAM.monster_minimax_obs counters for one tick of
        visible enemy state. Idempotent per tick: both teammates running on
        the same tick will each add an observation, which is fine (we're
        classifying a ratio, not a count)."""
        obs = self._obs()
        if obs.get('strategy') is not None:
            return  # already locked in
        try:
            for idx in self.getOpponents(gameState):
                try:
                    opp_state = gameState.getAgentState(idx)
                    if opp_state is None:
                        continue
                    pos = opp_state.getPosition()
                    # We only count ticks where we can see the enemy at all.
                    if pos is None:
                        continue
                    obs['total_obs_ticks'] = obs.get('total_obs_ticks', 0) + 1
                    if getattr(opp_state, 'isPacman', False):
                        obs['enemy_pacman_ticks'] = obs.get('enemy_pacman_ticks', 0) + 1
                    else:
                        obs['enemy_ghost_ticks'] = obs.get('enemy_ghost_ticks', 0) + 1
                except Exception:
                    continue
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Weight selection
    # ------------------------------------------------------------------

    def _weights(self):
        """Pick weight dict based on observed strategy and per-agent role."""
        obs = self._obs()
        strat = obs.get('strategy', None)
        try:
            role = TEAM.role.get(self.index, 'OFFENSE')
        except Exception:
            role = 'OFFENSE'

        if strat == 'DEFENSIVE':
            return _weights_team_defensive()
        if strat == 'AGGRESSIVE':
            return _weights_team_aggressive()
        if strat == 'BALANCED':
            return _weights_balanced_defense() if role == 'DEFENSE' \
                else _weights_balanced_offense()
        # Pre-classification default: use role-based seeds.
        return SEED_WEIGHTS_DEFENSIVE if role == 'DEFENSE' else SEED_WEIGHTS_OFFENSIVE

    # ------------------------------------------------------------------
    # Minimax α-β (opponent reduction, closer enemy only)
    # ------------------------------------------------------------------

    def _closer_enemy(self, gameState):
        """(idx, pos) of nearest visible enemy or (None, None)."""
        try:
            opponents = self.getOpponents(gameState)
            my_pos = gameState.getAgentPosition(self.index)
            best = None
            best_d = 10**9
            for idx in opponents:
                try:
                    pos = gameState.getAgentPosition(idx)
                    if pos is None:
                        continue
                    if my_pos is None:
                        return idx, pos
                    d = self.getMazeDistance(my_pos, pos)
                    if d < best_d:
                        best_d = d
                        best = (idx, pos)
                except Exception:
                    continue
            if best is None:
                return None, None
            return best
        except Exception:
            return None, None

    def _leaf_eval(self, gameState, action, weights):
        try:
            return evaluate(self, gameState, action, weights)
        except Exception:
            return _NEG_INF

    def _order_actions(self, gameState, agent_idx, actions, weights, self_action,
                       ascending):
        """Sort actions by quick evaluate() lookup (ascending for MIN, descending for MAX).

        We evaluate the action by generating the successor then evaluating
        with a STOP placeholder (self_action if agent_idx == self.index,
        else use self_action which is the root-time self action)."""
        try:
            scored = []
            for a in actions:
                try:
                    succ = gameState.generateSuccessor(agent_idx, a)
                    sa = a if agent_idx == self.index else self_action
                    v = evaluate(self, succ, sa, weights)
                except Exception:
                    v = 0.0
                scored.append((v, a))
            scored.sort(key=lambda x: x[0], reverse=not ascending)
            return [a for _, a in scored]
        except Exception:
            return actions

    def _alphabeta(self, gameState, depth, alpha, beta,
                   ply_agents, ply_idx, weights, self_action):
        """α-β search over a predefined ply sequence.

        ply_agents: list of (agent_idx, is_max) tuples. Typically for depth 4
        with 1-enemy reduction this is:
          [(self, MAX), (enemy, MIN), (self, MAX), (enemy, MIN)]
        and we enter with ply_idx = 0 pointing at "enemy MIN" since the
        root-level self-MAX is handled in _chooseActionImpl.
        """
        if depth <= 0 or ply_idx >= len(ply_agents):
            return self._leaf_eval(gameState, self_action, weights)

        agent_idx, is_max = ply_agents[ply_idx]

        try:
            legal = gameState.getLegalActions(agent_idx)
        except Exception:
            return self._leaf_eval(gameState, self_action, weights)

        if not legal:
            return self._leaf_eval(gameState, self_action, weights)

        legal = self._order_actions(
            gameState, agent_idx, legal, weights, self_action,
            ascending=not is_max,
        )

        if is_max:
            best = _NEG_INF
            for a in legal:
                try:
                    succ = gameState.generateSuccessor(agent_idx, a)
                except Exception:
                    continue
                sa = a if agent_idx == self.index else self_action
                val = self._alphabeta(succ, depth - 1, alpha, beta,
                                      ply_agents, ply_idx + 1, weights, sa)
                if val > best:
                    best = val
                alpha = max(alpha, best)
                if alpha >= beta:
                    break
            return best
        else:
            worst = _POS_INF
            for a in legal:
                try:
                    succ = gameState.generateSuccessor(agent_idx, a)
                except Exception:
                    continue
                val = self._alphabeta(succ, depth - 1, alpha, beta,
                                      ply_agents, ply_idx + 1, weights, self_action)
                if val < worst:
                    worst = val
                beta = min(beta, worst)
                if alpha >= beta:
                    break
            return worst

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------

    def _chooseActionImpl(self, gameState):
        # Tick bookkeeping and observation — shared via TEAM singleton.
        try:
            TEAM.tick = int(getattr(TEAM, 'tick', 0) or 0) + 1
        except Exception:
            pass
        tick = int(getattr(TEAM, 'tick', 0) or 0)

        try:
            self._update_observations(gameState)
        except Exception:
            pass

        try:
            obs = self._obs()
            if obs.get('strategy') is None and tick >= _OBSERVATION_WINDOW:
                total = max(1, obs.get('total_obs_ticks', 0))
                pac_ratio = obs.get('enemy_pacman_ticks', 0) / total
                if pac_ratio >= _AGGRESSIVE_RATIO:
                    obs['strategy'] = 'DEFENSIVE'
                elif pac_ratio <= _DEFENSIVE_RATIO:
                    obs['strategy'] = 'AGGRESSIVE'
                else:
                    obs['strategy'] = 'BALANCED'
                obs['classified_at_tick'] = tick
        except Exception:
            pass

        # ---- Minimax search ----
        try:
            weights = self._weights()
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP

            enemy_idx, enemy_pos = self._closer_enemy(gameState)

            # Build ply sequence. If we have a visible enemy, we alternate
            # self (MAX) and enemy (MIN) to depth _DEPTH. The root level is
            # handled in this function's loop (depth = _DEPTH - 1 into the
            # alphabeta recursion because we already expanded one MAX ply).
            ply_agents = []
            if enemy_idx is not None:
                # After root: (enemy MIN, self MAX, enemy MIN) for depth=4.
                for _ in range((_DEPTH - 1) // 2 + 1):
                    ply_agents.append((enemy_idx, False))
                    ply_agents.append((self.index, True))
                # Trim to _DEPTH - 1 (we already consumed one MAX at root).
                ply_agents = ply_agents[:_DEPTH - 1]

            # Move ordering for root self-MAX.
            ordered_legal = self._order_actions(
                gameState, self.index, legal, weights, None, ascending=False,
            )

            best_action = None
            best_val = _NEG_INF
            alpha = _NEG_INF
            beta = _POS_INF

            for action in ordered_legal:
                try:
                    succ = gameState.generateSuccessor(self.index, action)
                except Exception:
                    continue

                if ply_agents:
                    val = self._alphabeta(
                        succ, _DEPTH - 1, alpha, beta,
                        ply_agents, 0, weights, action,
                    )
                else:
                    val = self._leaf_eval(succ, action, weights)

                if val > best_val:
                    best_val = val
                    best_action = action
                alpha = max(alpha, best_val)

            if best_action is not None and best_action in legal:
                return best_action
        except Exception:
            pass

        # Fallback: greedy static evaluate.
        try:
            legal = gameState.getLegalActions(self.index)
            if not legal:
                return Directions.STOP
            weights = self._weights()
            best = max(
                legal,
                key=lambda a: self._leaf_eval(gameState, a, weights),
                default=Directions.STOP,
            )
            if best in legal:
                return best
        except Exception:
            pass

        non_stop = [a for a in (gameState.getLegalActions(self.index) or [])
                    if a != Directions.STOP]
        return non_stop[0] if non_stop else Directions.STOP
