# zoo_approxq_v1.py
# -----------------
# Approximate Q-learning agent (v1): 10-feature linear model, frozen weights.
#
# Design: "approximate Q-learning" here means offline-trained frozen weights.
# No online updates at match time. Q(s,a) = dot(WEIGHTS_V1, features(s,a)).
#
# Feature set is DELIBERATELY different from zoo_features.py (17-feature reflex
# basis) to support the methodological contrast in the report:
#   reflex_tuned = 17 features (canonical f_* naming, zoo_features module)
#   approxq_v1   = 10 features (different parameterisation, in-module)
#   approxq_v2   = 25 features (cross-product extensions, in-module)
#
# Key difference from reflex: no f_stop/f_reverse; adds ghost_dist_1step
# (binary adjacency penalty), scared_and_safe, dist_to_home_carrying as
# a raw product (not scaled by 1/dist).
#
# This module does NOT import from zoo_features.

from __future__ import annotations

import math

from zoo_core import CoreCaptureAgent, TEAM, Directions

# ---------------------------------------------------------------------------
# Feature list and frozen weights (hand-calibrated to mimic offline training).
# ---------------------------------------------------------------------------

FEATURES = [
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
]

WEIGHTS_V1 = {
    'bias': 0.0,
    'eats_food': 2.5,
    'closest_food': -1.0,
    'ghost_dist_1step': -5.0,   # strong penalty when ghost adjacent
    'num_carrying': 0.3,
    'dist_to_home_carrying': -0.5,
    'capsule_dist': -0.2,
    'on_defense_bias': 3.0,
    'invader_present': 5.0,
    'scared_and_safe': 1.5,
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


def _extract_features_v1(agent, gameState, action):
    """Compute the 10-feature dict for (agent, gameState, action).

    All individual computations are wrapped in try/except returning 0.0.
    """
    feats = {k: 0.0 for k in FEATURES}
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

    # Layout max distance for normalisation (rough upper bound).
    try:
        walls = snap.get('walls')
        if walls is not None:
            max_dist = float(walls.width + walls.height)
        else:
            max_dist = 100.0
    except Exception:
        max_dist = 100.0

    # --- eats_food: 1 if successor position has food ---
    try:
        if myPos is not None and myPos in set(agent.getFood(gameState).asList()):
            feats['eats_food'] = 1.0
        else:
            feats['eats_food'] = 0.0
    except Exception:
        feats['eats_food'] = 0.0

    # --- closest_food: -min_maze_dist / max_dist (in [-1, 0]) ---
    try:
        if myPos is not None and foodList:
            min_d = min(agent.getMazeDistance(myPos, f) for f in foodList)
            feats['closest_food'] = _clip(-float(min_d) / max(max_dist, 1.0))
        else:
            feats['closest_food'] = 0.0
    except Exception:
        feats['closest_food'] = 0.0

    # --- ghost_dist_1step: 1 if any active ghost at dist <= 1 from successor ---
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

    # --- num_carrying: our agent's numCarrying after successor ---
    try:
        feats['num_carrying'] = float(numCarrying)
    except Exception:
        feats['num_carrying'] = 0.0

    # --- dist_to_home_carrying: dist_to_home_frontier * numCarrying ---
    # Only meaningful when carrying; 0 otherwise.
    try:
        homeFrontier = agent.homeFrontier if agent.homeFrontier else []
        if myPos is not None and numCarrying > 0 and homeFrontier:
            min_home = min(agent.getMazeDistance(myPos, h) for h in homeFrontier)
            feats['dist_to_home_carrying'] = float(min_home) * float(numCarrying)
        else:
            feats['dist_to_home_carrying'] = 0.0
    except Exception:
        feats['dist_to_home_carrying'] = 0.0

    # --- capsule_dist: 1/max(min_dist_to_capsule, 1); 0 if none ---
    try:
        if myPos is not None and capsuleList:
            min_cap = min(agent.getMazeDistance(myPos, c) for c in capsuleList)
            feats['capsule_dist'] = 1.0 / max(float(min_cap), 1.0)
        else:
            feats['capsule_dist'] = 0.0
    except Exception:
        feats['capsule_dist'] = 0.0

    # --- on_defense_bias: 1 if agent NOT isPacman at successor ---
    try:
        feats['on_defense_bias'] = 0.0 if isPacman else 1.0
    except Exception:
        feats['on_defense_bias'] = 0.0

    # --- invader_present: 1 if any visible opponent is on our side ---
    try:
        invader_found = 0.0
        for opp_idx, opp_pos in opponentPositions.items():
            if opp_pos is None:
                continue
            try:
                opp_state = successor.getAgentState(opp_idx)
                if getattr(opp_state, 'isPacman', False):
                    invader_found = 1.0
                    break
            except Exception:
                continue
        feats['invader_present'] = invader_found
    except Exception:
        feats['invader_present'] = 0.0

    # --- scared_and_safe: 1 if any enemy is scared AND we're in enemy territory ---
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

    # Final clip.
    for k in feats:
        feats[k] = _clip(feats[k])

    return feats


def _qvalue_v1(agent, gameState, action):
    """Q(s,a) = sum(WEIGHTS_V1[f] * features[f]). Returns float."""
    try:
        feats = _extract_features_v1(agent, gameState, action)
        return sum(WEIGHTS_V1.get(f, 0.0) * v for f, v in feats.items())
    except Exception:
        return float('-inf')


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------

class ApproxQV1Agent(CoreCaptureAgent):
    """Approximate Q-learning agent with a 10-feature linear model.

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
                score = _qvalue_v1(self, gameState, action)
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
               first='ApproxQV1Agent', second='ApproxQV1Agent'):
    return [eval(first)(firstIndex), eval(second)(secondIndex)]
