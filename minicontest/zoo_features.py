# zoo_features.py
# ---------------
# Shared feature extractor module for zoo reflex-family agents.
# Implements the 20-feature set from STRATEGY.md §4.1.
#
# All feature computations are wrapped in try/except returning 0.0 on failure.
# Final values are clipped to [-1e6, 1e6]. No inf/NaN emitted.
#
# Usage:
#   from zoo_features import extract_features, evaluate, SEED_WEIGHTS_OFFENSIVE, SEED_WEIGHTS_DEFENSIVE

from __future__ import annotations

import math
from game import Directions

# ---------------------------------------------------------------------------
# Seed weight dictionaries (gen-0 of CEM evolution)
# ---------------------------------------------------------------------------

SEED_WEIGHTS_OFFENSIVE = {
    'f_bias': 0.0,
    'f_successorScore': 100.0,
    'f_distToFood': 10.0,
    'f_distToCapsule': 8.0,
    'f_numCarrying': 5.0,
    'f_distToHome': 4.0,
    'f_ghostDist1': -50.0,
    'f_ghostDist2': -10.0,
    'f_inDeadEnd': -200.0,
    'f_stop': -100.0,
    'f_reverse': -2.0,
    'f_numInvaders': -1000.0,
    'f_invaderDist': 30.0,
    'f_onDefense': 100.0,
    'f_patrolDist': 5.0,
    'f_distToCapsuleDefend': -3.0,
    'f_scaredFlee': -1.0,
    # B1 (pm18): 3 new features extending zoo_features from 17 → 20 dims.
    # Seed weights = 0.0 so the current behaviour matches pre-B1 exactly —
    # evolution discovers useful weight magnitudes over Phase 2a/b.
    'f_scaredGhostChase': 0.0,
    'f_returnUrgency': 0.0,
    'f_teammateSpread': 0.0,
}

SEED_WEIGHTS_DEFENSIVE = {
    'f_bias': 0.0,
    'f_successorScore': 50.0,
    'f_distToFood': 2.0,
    'f_distToCapsule': 2.0,
    'f_numCarrying': 1.0,
    'f_distToHome': 1.0,
    'f_ghostDist1': -5.0,
    'f_ghostDist2': -1.0,
    'f_inDeadEnd': -50.0,
    'f_stop': -100.0,
    'f_reverse': -2.0,
    'f_numInvaders': -2000.0,
    'f_invaderDist': 80.0,
    'f_onDefense': 200.0,
    'f_patrolDist': 30.0,
    'f_distToCapsuleDefend': -20.0,
    'f_scaredFlee': -10.0,
    # B1 (pm18): see SEED_WEIGHTS_OFFENSIVE comment.
    'f_scaredGhostChase': 0.0,
    'f_returnUrgency': 0.0,
    'f_teammateSpread': 0.0,
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
    """Clip a float to [-1e6, 1e6] and guard against inf/NaN."""
    try:
        if math.isnan(v) or math.isinf(v):
            return 0.0
        return max(-_CLIP, min(_CLIP, float(v)))
    except Exception:
        return 0.0


def extract_features(agent, gameState, action):
    """Compute the 20-feature dict for (agent, gameState, action).

    Uses agent.snapshot(), agent.getMazeDistance(), agent.bottlenecks,
    agent.deadEnds, agent.homeFrontier, and agent.red.

    All individual features are wrapped in try/except returning 0.0.
    Final dict values are clipped to [-1e6, 1e6] with no inf/NaN.

    Returns dict[str, float].
    """
    features = {
        'f_bias': 1.0,
        'f_successorScore': 0.0,
        'f_distToFood': 0.0,
        'f_distToCapsule': 0.0,
        'f_numCarrying': 0.0,
        'f_distToHome': 0.0,
        'f_ghostDist1': 0.0,
        'f_ghostDist2': 0.0,
        'f_inDeadEnd': 0.0,
        'f_stop': 0.0,
        'f_reverse': 0.0,
        'f_numInvaders': 0.0,
        'f_invaderDist': 0.0,
        'f_onDefense': 0.0,
        'f_patrolDist': 0.0,
        'f_distToCapsuleDefend': 0.0,
        'f_scaredFlee': 0.0,
        # B1 (pm18): zero-defaults; computed below before the clip pass.
        'f_scaredGhostChase': 0.0,
        'f_returnUrgency': 0.0,
        'f_teammateSpread': 0.0,
    }

    # --- Compute successor state ---
    try:
        successor = gameState.generateSuccessor(agent.index, action)
        # If only half a grid step was covered, advance one more step.
        from util import nearestPoint
        pos_raw = successor.getAgentState(agent.index).getPosition()
        if pos_raw != nearestPoint(pos_raw):
            successor = successor.generateSuccessor(agent.index, action)
    except Exception:
        successor = gameState  # fallback: evaluate current state

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
    myState = snap.get('myState')
    isPacman = snap.get('isPacman', False)
    scaredTimer = snap.get('scaredTimer', 0)
    numCarrying = snap.get('numCarrying', 0)
    foodList = snap.get('foodList', [])
    capsuleList = snap.get('capsuleList', [])
    opponentPositions = snap.get('opponentPositions', {})

    # -----------------------------------------------------------------------
    # f_bias
    # -----------------------------------------------------------------------
    features['f_bias'] = 1.0

    # -----------------------------------------------------------------------
    # f_successorScore = -len(remaining food to eat)
    # -----------------------------------------------------------------------
    try:
        features['f_successorScore'] = float(-len(foodList))
    except Exception:
        features['f_successorScore'] = 0.0

    # -----------------------------------------------------------------------
    # f_distToFood = 1 / max(min_dist_to_remaining_food, 1); 0 if no food
    # -----------------------------------------------------------------------
    try:
        if myPos is not None and foodList:
            min_food_dist = min(agent.getMazeDistance(myPos, f) for f in foodList)
            features['f_distToFood'] = 1.0 / max(min_food_dist, 1)
        else:
            features['f_distToFood'] = 0.0
    except Exception:
        features['f_distToFood'] = 0.0

    # -----------------------------------------------------------------------
    # f_distToCapsule = 1 / max(min_dist_to_capsule, 1); 0 if no capsule
    # -----------------------------------------------------------------------
    try:
        if myPos is not None and capsuleList:
            min_cap_dist = min(agent.getMazeDistance(myPos, c) for c in capsuleList)
            features['f_distToCapsule'] = 1.0 / max(min_cap_dist, 1)
        else:
            features['f_distToCapsule'] = 0.0
    except Exception:
        features['f_distToCapsule'] = 0.0

    # -----------------------------------------------------------------------
    # f_numCarrying
    # -----------------------------------------------------------------------
    try:
        features['f_numCarrying'] = float(numCarrying)
    except Exception:
        features['f_numCarrying'] = 0.0

    # -----------------------------------------------------------------------
    # f_distToHome = 1/max(dist_to_nearest_home_frontier, 1) * numCarrying
    # Only meaningful when carrying; 0 if not carrying or no frontier.
    # -----------------------------------------------------------------------
    try:
        homeFrontier = agent.homeFrontier if agent.homeFrontier else []
        if myPos is not None and numCarrying > 0 and homeFrontier:
            min_home_dist = min(agent.getMazeDistance(myPos, h) for h in homeFrontier)
            features['f_distToHome'] = (1.0 / max(min_home_dist, 1)) * numCarrying
        else:
            features['f_distToHome'] = 0.0
    except Exception:
        features['f_distToHome'] = 0.0

    # -----------------------------------------------------------------------
    # Ghost distances: find active (non-scared) enemy ghosts visible to us.
    # f_ghostDist1 = -1/max(nearest_active_ghost_dist, 1); 0 if none
    # f_ghostDist2 = -1/max(second_nearest, 1); 0 if fewer than 2
    # -----------------------------------------------------------------------
    try:
        active_ghost_dists = []
        if myPos is not None:
            for opp_idx, opp_pos in opponentPositions.items():
                if opp_pos is None:
                    continue
                try:
                    opp_state = successor.getAgentState(opp_idx)
                    opp_is_pacman = getattr(opp_state, 'isPacman', False)
                    opp_scared = int(getattr(opp_state, 'scaredTimer', 0) or 0)
                    if opp_is_pacman:
                        continue  # they are Pacman, not a ghost threat
                    if opp_scared > 0:
                        continue  # scared ghost is not a threat
                    dist = agent.getMazeDistance(myPos, opp_pos)
                    active_ghost_dists.append(dist)
                except Exception:
                    continue
        active_ghost_dists.sort()
        if len(active_ghost_dists) >= 1:
            features['f_ghostDist1'] = -1.0 / max(active_ghost_dists[0], 1)
        else:
            features['f_ghostDist1'] = 0.0
        if len(active_ghost_dists) >= 2:
            features['f_ghostDist2'] = -1.0 / max(active_ghost_dists[1], 1)
        else:
            features['f_ghostDist2'] = 0.0
    except Exception:
        features['f_ghostDist1'] = 0.0
        features['f_ghostDist2'] = 0.0

    # -----------------------------------------------------------------------
    # f_inDeadEnd: 1.0 if successor position is in a dead-end cell AND
    # an active enemy ghost is within distance 4; else 0.
    # -----------------------------------------------------------------------
    try:
        deadEnds = agent.deadEnds if agent.deadEnds else frozenset()
        in_dead = (myPos in deadEnds) if myPos is not None else False
        if in_dead and active_ghost_dists and active_ghost_dists[0] <= 4:
            features['f_inDeadEnd'] = 1.0
        else:
            features['f_inDeadEnd'] = 0.0
    except Exception:
        features['f_inDeadEnd'] = 0.0

    # -----------------------------------------------------------------------
    # f_stop: 1.0 if action == STOP
    # -----------------------------------------------------------------------
    try:
        features['f_stop'] = 1.0 if action == Directions.STOP else 0.0
    except Exception:
        features['f_stop'] = 0.0

    # -----------------------------------------------------------------------
    # f_reverse: 1.0 if action reverses current direction
    # -----------------------------------------------------------------------
    try:
        cur_dir = gameState.getAgentState(agent.index).configuration.direction
        rev_dir = Directions.REVERSE[cur_dir]
        features['f_reverse'] = 1.0 if action == rev_dir else 0.0
    except Exception:
        features['f_reverse'] = 0.0

    # -----------------------------------------------------------------------
    # Defensive features
    # -----------------------------------------------------------------------

    # f_numInvaders: count of opponent Pacmen on our side
    # f_invaderDist: 1 / max(min_invader_dist, 1) — defender chases
    # -----------------------------------------------------------------------
    try:
        invader_dists = []
        for opp_idx, opp_pos in opponentPositions.items():
            if opp_pos is None:
                continue
            try:
                opp_state = successor.getAgentState(opp_idx)
                if getattr(opp_state, 'isPacman', False):
                    if myPos is not None:
                        d = agent.getMazeDistance(myPos, opp_pos)
                        invader_dists.append(d)
            except Exception:
                continue
        features['f_numInvaders'] = float(len(invader_dists))
        if invader_dists:
            features['f_invaderDist'] = 1.0 / max(min(invader_dists), 1)
        else:
            features['f_invaderDist'] = 0.0
    except Exception:
        features['f_numInvaders'] = 0.0
        features['f_invaderDist'] = 0.0

    # -----------------------------------------------------------------------
    # f_onDefense: 1.0 if successor agent is NOT Pacman (i.e. on home side)
    # -----------------------------------------------------------------------
    try:
        features['f_onDefense'] = 0.0 if isPacman else 1.0
    except Exception:
        features['f_onDefense'] = 0.0

    # -----------------------------------------------------------------------
    # f_patrolDist: 1/max(dist_to_rotating_patrol_anchor, 1)
    # Anchor = closest bottleneck cell from homeFrontier (or nearest
    # homeFrontier cell if no bottlenecks overlap).
    # -----------------------------------------------------------------------
    try:
        homeFrontier = agent.homeFrontier if agent.homeFrontier else []
        bottlenecks = agent.bottlenecks if agent.bottlenecks else frozenset()

        anchor = None
        if myPos is not None and homeFrontier:
            # Prefer bottleneck cells on the home frontier as patrol anchors.
            frontier_bottlenecks = [c for c in homeFrontier if c in bottlenecks]
            if frontier_bottlenecks:
                # Rotating anchor: pick the one closest to myPos.
                anchor = min(frontier_bottlenecks, key=lambda c: agent.getMazeDistance(myPos, c))
            else:
                # Fall back to nearest frontier cell.
                anchor = min(homeFrontier, key=lambda c: agent.getMazeDistance(myPos, c))

        if anchor is not None and myPos is not None:
            d = agent.getMazeDistance(myPos, anchor)
            features['f_patrolDist'] = 1.0 / max(d, 1)
        else:
            features['f_patrolDist'] = 0.0
    except Exception:
        features['f_patrolDist'] = 0.0

    # -----------------------------------------------------------------------
    # f_distToCapsuleDefend: -1/max(dist_to_our_defending_capsule, 1)
    # "Our defending capsule" = capsule on our side (getCapsulesYouAreDefending).
    # Defender wants enemies AWAY from our capsule (hence negative: the closer
    # the defender is to the capsule, the higher the negative penalty → the
    # weight must be negative to make being close desirable).
    # Actually the feature is negative when close — agent should apply a
    # negative weight to push away, OR be close to intercept.
    # Per plan: f_distToCapsuleDefend = -1/max(dist, 1) so with weight -3,
    # value is +3/dist → agent is rewarded for being close to our capsule.
    # -----------------------------------------------------------------------
    try:
        if myPos is not None:
            defend_caps = list(agent.getCapsulesYouAreDefending(successor))
            if defend_caps:
                min_dcap_dist = min(agent.getMazeDistance(myPos, c) for c in defend_caps)
                features['f_distToCapsuleDefend'] = -1.0 / max(min_dcap_dist, 1)
            else:
                features['f_distToCapsuleDefend'] = 0.0
        else:
            features['f_distToCapsuleDefend'] = 0.0
    except Exception:
        features['f_distToCapsuleDefend'] = 0.0

    # -----------------------------------------------------------------------
    # f_scaredFlee: if scaredTimer > 0, flip sign of f_invaderDist (flee).
    # When scared, defender should flee from invaders rather than chase.
    # -----------------------------------------------------------------------
    try:
        if scaredTimer > 0:
            # Positive f_invaderDist means agent is close to invader (= good when chasing).
            # Flip sign so that being close is bad (flee).
            features['f_scaredFlee'] = -features['f_invaderDist']
        else:
            features['f_scaredFlee'] = 0.0
    except Exception:
        features['f_scaredFlee'] = 0.0

    # -----------------------------------------------------------------------
    # f_scaredGhostChase (B1, pm18): 1/dist to nearest SCARED enemy ghost.
    # Positive value = closer to scared ghost. Evolved +weight → chase for
    # points & ghost-kill. Currently no other feature captures this bonus.
    # -----------------------------------------------------------------------
    try:
        scared_ghost_dists = []
        if myPos is not None:
            for opp_idx, opp_pos in opponentPositions.items():
                if opp_pos is None:
                    continue
                try:
                    opp_state = successor.getAgentState(opp_idx)
                    if getattr(opp_state, 'isPacman', False):
                        continue
                    opp_scared = int(getattr(opp_state, 'scaredTimer', 0) or 0)
                    if opp_scared <= 0:
                        continue
                    d = agent.getMazeDistance(myPos, opp_pos)
                    scared_ghost_dists.append(d)
                except Exception:
                    continue
        if scared_ghost_dists:
            features['f_scaredGhostChase'] = 1.0 / max(min(scared_ghost_dists), 1)
        else:
            features['f_scaredGhostChase'] = 0.0
    except Exception:
        features['f_scaredGhostChase'] = 0.0

    # -----------------------------------------------------------------------
    # f_returnUrgency (B1, pm18): non-linear return-home pressure.
    #   numCarrying² × (1/home_dist) × (0.5 + time_factor)
    # time_factor = 1 − timeleft/1200 grows 0→1 as the game advances; the
    # 0.5 floor keeps baseline return pressure present from move 0, and the
    # squared carrying term lets a large hoard dominate the expression even
    # at long home distances. Existing f_distToHome is linear in both;
    # this gives evolution an extra lever for late-game scoring rushes.
    # -----------------------------------------------------------------------
    try:
        try:
            time_left = int(gameState.data.timeleft)
        except Exception:
            time_left = 1200
        time_factor = 1.0 - (max(0, min(time_left, 1200)) / 1200.0)
        homeFrontier = agent.homeFrontier if agent.homeFrontier else []
        if myPos is not None and numCarrying > 0 and homeFrontier:
            min_home_dist = min(agent.getMazeDistance(myPos, h) for h in homeFrontier)
            features['f_returnUrgency'] = (
                (float(numCarrying) ** 2)
                * (1.0 / max(min_home_dist, 1))
                * (0.5 + time_factor)
            )
        else:
            features['f_returnUrgency'] = 0.0
    except Exception:
        features['f_returnUrgency'] = 0.0

    # -----------------------------------------------------------------------
    # f_teammateSpread (B1, pm18): 1/dist to the closest teammate. A
    # NEGATIVE weight → the agent disperses (being close is bad). Prevents
    # both offense agents from dogpiling the same food path. No existing
    # feature expresses teammate geometry.
    # -----------------------------------------------------------------------
    try:
        teammate_dists = []
        if myPos is not None:
            try:
                team_indices = list(agent.getTeam(successor))
            except Exception:
                team_indices = []
            for tm_idx in team_indices:
                if tm_idx == agent.index:
                    continue
                try:
                    tm_pos = successor.getAgentPosition(tm_idx)
                    if tm_pos is None:
                        continue
                    d = agent.getMazeDistance(myPos, tm_pos)
                    teammate_dists.append(d)
                except Exception:
                    continue
        if teammate_dists:
            features['f_teammateSpread'] = 1.0 / max(min(teammate_dists), 1)
        else:
            features['f_teammateSpread'] = 0.0
    except Exception:
        features['f_teammateSpread'] = 0.0

    # -----------------------------------------------------------------------
    # Final clip pass — ensure no inf/NaN in output.
    # -----------------------------------------------------------------------
    for k in features:
        features[k] = _clip(features[k])

    return features


def evaluate(agent, gameState, action, weights):
    """Compute weighted sum of features. Returns float.

    Returns -inf on any unexpected exception so argmax skips the broken action.
    """
    try:
        feats = extract_features(agent, gameState, action)
        return sum(weights.get(f, 0.0) * v for f, v in feats.items())
    except Exception:
        return float('-inf')
