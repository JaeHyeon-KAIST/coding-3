# zoo_approxq_v2_deeper.py
# ------------------------
# Approximate Q-learning agent (v2, deeper): 25-feature linear model with
# cross-product (non-linear via feature interactions) and game-phase features.
# Frozen weights; no online updates at match time.
#
# Design: builds on the v1 10-feature base, then adds:
#   - 5 cross-product features (pairwise interactions)
#   - 10 game-phase / situation-aware features
#
# Feature set is DELIBERATELY different from zoo_features.py (reflex basis)
# to support the methodological contrast in the report.  In-module only;
# does NOT import from zoo_features.
#
# Q(s,a) = dot(WEIGHTS_V2, features(s,a))

from __future__ import annotations

import math

from zoo_core import CoreCaptureAgent, TEAM, Directions

# ---------------------------------------------------------------------------
# Feature list (25 total)
# ---------------------------------------------------------------------------

FEATURES_V2 = [
    # Base 10 (same semantics as v1)
    'bias',
    'eats_food',
    'closest_food',
    'ghost_dist_1step',
    'num_carrying',
    'dist_to_home_carrying',
    'capsule_dist',
    'on_defense_bias',
    'invader_present',
    'scared_and_safe',
    # Cross-product 5
    'closest_food_times_safe',      # closest_food * (1 - ghost_dist_1step)
    'carrying_times_home_dist',     # num_carrying * (dist_to_home / max_width)
    'ghost_dist_squared',           # ghost_dist_1step ^ 2
    'capsule_when_ghost_near',      # capsule_dist * ghost_dist_1step
    'home_dist_scaled',             # dist_to_nearest_home / max_maze_width
    # Game-phase 10
    'phase_early',                  # food_remaining/total_food > 0.8
    'phase_mid',                    # 0.4 < food_remaining/total_food <= 0.8
    'phase_late',                   # food_remaining/total_food <= 0.4
    'carrying_urgency',             # num_carrying * phase_late
    'ghost_near_and_carrying',      # ghost_dist_1step * num_carrying
    'safe_to_eat',                  # eats_food * (1 - ghost_dist_1step)
    'defense_with_invader',         # on_defense_bias * invader_present
    'offense_in_enemy_territory',   # isPacman * (1 - invader_present)
    'capsule_urgency',              # capsule_dist * ghost_dist_1step * num_carrying
    'retreat_signal',               # dist_to_home_carrying * ghost_dist_1step
]

# ---------------------------------------------------------------------------
# Frozen weights (hand-calibrated; balanced between offense and defense).
# Exploration-friendly: neither too aggressive nor too defensive.
# ---------------------------------------------------------------------------

WEIGHTS_V2 = {
    # Base features
    'bias': 0.0,
    'eats_food': 2.0,
    'closest_food': -0.8,
    'ghost_dist_1step': -4.0,
    'num_carrying': 0.4,
    'dist_to_home_carrying': -0.4,
    'capsule_dist': -0.3,
    'on_defense_bias': 2.5,
    'invader_present': 4.0,
    'scared_and_safe': 1.2,
    # Cross-product features
    'closest_food_times_safe': 1.5,     # safe food eating is good
    'carrying_times_home_dist': -1.0,   # penalise wandering far when carrying
    'ghost_dist_squared': -2.0,         # quadratic ghost proximity penalty
    'capsule_when_ghost_near': 2.0,     # seek capsule when ghost is close
    'home_dist_scaled': -0.6,           # mild push toward home
    # Game-phase features
    'phase_early': 0.5,                 # slight exploration bonus early
    'phase_mid': 0.0,                   # neutral mid-game
    'phase_late': -0.3,                 # slightly cautious late
    'carrying_urgency': 1.0,            # return food urgently late game
    'ghost_near_and_carrying': -3.0,    # extra danger if carrying + ghost near
    'safe_to_eat': 1.8,                 # reward safe food eating
    'defense_with_invader': 3.0,        # strong defence when invader present
    'offense_in_enemy_territory': 0.8,  # mild reward for pressing forward
    'capsule_urgency': 3.5,             # high priority to capsule when threatened
    'retreat_signal': -0.8,             # push home when carrying + ghost near
}

# Preferred action order for deterministic tiebreak.
_ACTION_PREFERENCE = [
    Directions.NORTH,
    Directions.EAST,
    Directions.SOUTH,
    Directions.WEST,
    Directions.STOP,
]

_CLIP = 1e6


def _clip(v):
    """Clip float to [-1e6, 1e6] and guard inf/NaN."""
    try:
        if math.isnan(v) or math.isinf(v):
            return 0.0
        return max(-_CLIP, min(_CLIP, float(v)))
    except Exception:
        return 0.0


def _extract_features_v2(agent, gameState, action):
    """Compute the 25-feature dict for (agent, gameState, action).

    All individual computations are wrapped in try/except returning 0.0.
    """
    feats = {k: 0.0 for k in FEATURES_V2}
    feats['bias'] = 1.0

    # --- Compute successor state ---
    try:
        successor = gameState.generateSuccessor(agent.index, action)
        try:
            from util import nearestPoint
            pos_raw = successor.getAgentState(agent.index).getPosition()
            if pos_raw != nearestPoint(pos_raw):
                successor = successor.generateSuccessor(agent.index, action)
        except Exception:
            pass
    except Exception:
        successor = gameState

    # --- Snapshot of successor ---
    try:
        snap = agent.snapshot(successor)
    except Exception:
        snap = {
            'myPos': None, 'myState': None, 'isPacman': False,
            'scaredTimer': 0, 'numCarrying': 0, 'foodList': [],
            'defendFoodList': [], 'capsuleList': [], 'opponentPositions': {},
            'teamPositions': {}, 'walls': None,
        }

    myPos = snap.get('myPos')
    isPacman = snap.get('isPacman', False)
    numCarrying = snap.get('numCarrying', 0)
    foodList = snap.get('foodList', [])
    capsuleList = snap.get('capsuleList', [])
    opponentPositions = snap.get('opponentPositions', {})

    # Layout dimensions for normalisation.
    try:
        walls = snap.get('walls')
        if walls is not None:
            max_width = float(max(walls.width, 1))
            max_dist = float(walls.width + walls.height)
        else:
            max_width = 32.0
            max_dist = 64.0
    except Exception:
        max_width = 32.0
        max_dist = 64.0

    # --- Food counts for game-phase features ---
    try:
        total_food = float(len(agent.getFood(gameState).asList()) +
                           len(agent.getFoodYouAreDefending(gameState).asList()))
        total_food = max(total_food, 1.0)
        remaining_food = float(len(foodList))
        food_ratio = remaining_food / total_food  # in [0, 1]
    except Exception:
        food_ratio = 0.5

    # =========================================================================
    # Base 10 features (same semantics as v1)
    # =========================================================================

    # bias already set to 1.0

    # eats_food
    try:
        prior_food = set(agent.getFood(gameState).asList())
        feats['eats_food'] = 1.0 if (myPos is not None and myPos in prior_food) else 0.0
    except Exception:
        feats['eats_food'] = 0.0

    # closest_food: -min_dist / max_dist in [-1, 0]
    try:
        if myPos is not None and foodList:
            min_d = min(agent.getMazeDistance(myPos, f) for f in foodList)
            feats['closest_food'] = _clip(-float(min_d) / max(max_dist, 1.0))
        else:
            feats['closest_food'] = 0.0
    except Exception:
        feats['closest_food'] = 0.0

    # ghost_dist_1step: 1 if active ghost at dist <= 1
    try:
        ghost_adj = 0.0
        if myPos is not None:
            for opp_idx, opp_pos in opponentPositions.items():
                if opp_pos is None:
                    continue
                try:
                    opp_state = successor.getAgentState(opp_idx)
                    opp_pacman = getattr(opp_state, 'isPacman', False)
                    opp_scared = int(getattr(opp_state, 'scaredTimer', 0) or 0)
                    if opp_pacman or opp_scared > 0:
                        continue
                    if agent.getMazeDistance(myPos, opp_pos) <= 1:
                        ghost_adj = 1.0
                        break
                except Exception:
                    continue
        feats['ghost_dist_1step'] = ghost_adj
    except Exception:
        feats['ghost_dist_1step'] = 0.0

    # num_carrying
    try:
        feats['num_carrying'] = float(numCarrying)
    except Exception:
        feats['num_carrying'] = 0.0

    # dist_to_home_carrying: raw dist * numCarrying (v1 style)
    try:
        homeFrontier = agent.homeFrontier if agent.homeFrontier else []
        if myPos is not None and numCarrying > 0 and homeFrontier:
            min_home = min(agent.getMazeDistance(myPos, h) for h in homeFrontier)
            feats['dist_to_home_carrying'] = float(min_home) * float(numCarrying)
        else:
            feats['dist_to_home_carrying'] = 0.0
    except Exception:
        feats['dist_to_home_carrying'] = 0.0

    # capsule_dist: 1/max(min_cap_dist, 1)
    try:
        if myPos is not None and capsuleList:
            min_cap = min(agent.getMazeDistance(myPos, c) for c in capsuleList)
            feats['capsule_dist'] = 1.0 / max(float(min_cap), 1.0)
        else:
            feats['capsule_dist'] = 0.0
    except Exception:
        feats['capsule_dist'] = 0.0

    # on_defense_bias
    try:
        feats['on_defense_bias'] = 0.0 if isPacman else 1.0
    except Exception:
        feats['on_defense_bias'] = 0.0

    # invader_present
    try:
        inv = 0.0
        for opp_idx, opp_pos in opponentPositions.items():
            if opp_pos is None:
                continue
            try:
                opp_state = successor.getAgentState(opp_idx)
                if getattr(opp_state, 'isPacman', False):
                    inv = 1.0
                    break
            except Exception:
                continue
        feats['invader_present'] = inv
    except Exception:
        feats['invader_present'] = 0.0

    # scared_and_safe: 1 if in enemy territory and any enemy is scared
    try:
        if isPacman:
            any_scared = 0.0
            for opp_idx in opponentPositions:
                try:
                    opp_state = successor.getAgentState(opp_idx)
                    if int(getattr(opp_state, 'scaredTimer', 0) or 0) > 0:
                        any_scared = 1.0
                        break
                except Exception:
                    continue
            feats['scared_and_safe'] = any_scared
        else:
            feats['scared_and_safe'] = 0.0
    except Exception:
        feats['scared_and_safe'] = 0.0

    # =========================================================================
    # Cross-product features (5)
    # =========================================================================

    cf = feats['closest_food']       # in [-1, 0]
    gd = feats['ghost_dist_1step']   # 0 or 1
    nc = feats['num_carrying']
    cd = feats['capsule_dist']

    # closest_food_times_safe = closest_food * (1 - ghost_dist_1step)
    try:
        feats['closest_food_times_safe'] = _clip(cf * (1.0 - gd))
    except Exception:
        feats['closest_food_times_safe'] = 0.0

    # carrying_times_home_dist = num_carrying * (dist_to_home / max_width)
    try:
        homeFrontier = agent.homeFrontier if agent.homeFrontier else []
        if myPos is not None and homeFrontier and nc > 0:
            min_home = min(agent.getMazeDistance(myPos, h) for h in homeFrontier)
            feats['carrying_times_home_dist'] = _clip(nc * (float(min_home) / max(max_width, 1.0)))
        else:
            feats['carrying_times_home_dist'] = 0.0
    except Exception:
        feats['carrying_times_home_dist'] = 0.0

    # ghost_dist_squared = ghost_dist_1step ^ 2
    try:
        feats['ghost_dist_squared'] = _clip(gd ** 2)
    except Exception:
        feats['ghost_dist_squared'] = 0.0

    # capsule_when_ghost_near = capsule_dist * ghost_dist_1step
    try:
        feats['capsule_when_ghost_near'] = _clip(cd * gd)
    except Exception:
        feats['capsule_when_ghost_near'] = 0.0

    # home_dist_scaled = dist_to_nearest_home / max_maze_width
    try:
        homeFrontier = agent.homeFrontier if agent.homeFrontier else []
        if myPos is not None and homeFrontier:
            min_home = min(agent.getMazeDistance(myPos, h) for h in homeFrontier)
            feats['home_dist_scaled'] = _clip(float(min_home) / max(max_width, 1.0))
        else:
            feats['home_dist_scaled'] = 0.0
    except Exception:
        feats['home_dist_scaled'] = 0.0

    # =========================================================================
    # Game-phase features (10)
    # =========================================================================

    # Phase flags based on food_remaining / total_food.
    try:
        feats['phase_early'] = 1.0 if food_ratio > 0.8 else 0.0
        feats['phase_mid'] = 1.0 if 0.4 < food_ratio <= 0.8 else 0.0
        feats['phase_late'] = 1.0 if food_ratio <= 0.4 else 0.0
    except Exception:
        feats['phase_early'] = 0.0
        feats['phase_mid'] = 1.0
        feats['phase_late'] = 0.0

    # carrying_urgency = num_carrying * phase_late
    try:
        feats['carrying_urgency'] = _clip(nc * feats['phase_late'])
    except Exception:
        feats['carrying_urgency'] = 0.0

    # ghost_near_and_carrying = ghost_dist_1step * num_carrying
    try:
        feats['ghost_near_and_carrying'] = _clip(gd * nc)
    except Exception:
        feats['ghost_near_and_carrying'] = 0.0

    # safe_to_eat = eats_food * (1 - ghost_dist_1step)
    try:
        feats['safe_to_eat'] = _clip(feats['eats_food'] * (1.0 - gd))
    except Exception:
        feats['safe_to_eat'] = 0.0

    # defense_with_invader = on_defense_bias * invader_present
    try:
        feats['defense_with_invader'] = _clip(
            feats['on_defense_bias'] * feats['invader_present'])
    except Exception:
        feats['defense_with_invader'] = 0.0

    # offense_in_enemy_territory = isPacman * (1 - invader_present)
    try:
        feats['offense_in_enemy_territory'] = _clip(
            (1.0 if isPacman else 0.0) * (1.0 - feats['invader_present']))
    except Exception:
        feats['offense_in_enemy_territory'] = 0.0

    # capsule_urgency = capsule_dist * ghost_dist_1step * num_carrying
    try:
        feats['capsule_urgency'] = _clip(cd * gd * nc)
    except Exception:
        feats['capsule_urgency'] = 0.0

    # retreat_signal = dist_to_home_carrying * ghost_dist_1step
    try:
        feats['retreat_signal'] = _clip(feats['dist_to_home_carrying'] * gd)
    except Exception:
        feats['retreat_signal'] = 0.0

    # Final clip pass.
    for k in feats:
        feats[k] = _clip(feats[k])

    return feats


def _qvalue_v2(agent, gameState, action):
    """Q(s,a) = dot(WEIGHTS_V2, features_v2(s,a)). Returns float."""
    try:
        feats = _extract_features_v2(agent, gameState, action)
        return sum(WEIGHTS_V2.get(f, 0.0) * v for f, v in feats.items())
    except Exception:
        return float('-inf')


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------

class ApproxQV2DeeperAgent(CoreCaptureAgent):
    """Approximate Q-learning agent with a 25-feature linear model.

    Extends v1 with cross-product interactions and game-phase awareness.
    Offline-trained frozen weights; no online updates at match time.
    """

    def _chooseActionImpl(self, gameState):
        legal = gameState.getLegalActions(self.index)
        if not legal:
            return Directions.STOP

        best_score = float('-inf')
        best_action = None

        # Evaluate in tiebreak-preference order so first tie-winner wins.
        ordered = sorted(
            legal,
            key=lambda a: _ACTION_PREFERENCE.index(a)
            if a in _ACTION_PREFERENCE else len(_ACTION_PREFERENCE),
        )

        for action in ordered:
            try:
                score = _qvalue_v2(self, gameState, action)
            except Exception:
                score = float('-inf')
            if score > best_score:
                best_score = score
                best_action = action

        if best_action is None or best_action not in legal:
            non_stop = [a for a in legal if a != Directions.STOP]
            return non_stop[0] if non_stop else Directions.STOP

        return best_action


def createTeam(firstIndex, secondIndex, isRed,
               first='ApproxQV2DeeperAgent', second='ApproxQV2DeeperAgent'):
    return [eval(first)(firstIndex), eval(second)(secondIndex)]
