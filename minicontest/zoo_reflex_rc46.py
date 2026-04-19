# zoo_reflex_rc46.py
# ------------------
# rc46: Online opponent-type classifier (user's ⭐ pick).
#
# A more rigorous version of pm20's T4: instead of three hand-tuned
# threshold rules on ratios, we maintain a 4-dimensional observation
# vector from the first RC46_OBSERVE_TICKS ticks, classify into one of
# four opponent archetypes by nearest-centroid (Euclidean), and apply
# per-archetype A1-weight multipliers.
#
# Observation vector (normalized to [0,1] each):
#   v0 = pacman_obs_ratio       (opponent seen as Pacman / total seen)
#   v1 = invader_crossings / 3  (ghost→pacman transitions, capped)
#   v2 = mean_pacman_depth      (how deep invaders go into our territory)
#   v3 = our_food_eaten_ratio   (food we've taken / initial food count)
#
# Archetype centroids (chosen from prior-agent stereotypes):
#   RUSH       (0.75, 0.66, 0.60, 0.25)  many invaders, our food lagging
#   TURTLE     (0.10, 0.00, 0.00, 0.50)  nothing crosses, neutral eating
#   CHOKE      (0.35, 0.33, 0.20, 0.15)  defender holds chokes, we lag
#   NEUTRAL    (0.50, 0.33, 0.30, 0.40)  middle — A1 default range
#
# Counter-policy multipliers per archetype:
#   RUSH    → boost defense (invader / patrol), damp offense
#   TURTLE  → boost offense (food / capsule / successor score)
#   CHOKE   → boost offense + boost our dead-end / ghost avoidance
#   NEUTRAL → no adjustment (A1 default)
#
# Classification fires ONCE at tick >= RC46_OBSERVE_TICKS and stays
# fixed for the rest of the game (same no-hysteresis pattern as T4).

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent


RC46_OBSERVE_TICKS = 60       # our-turn count; ~120 game ticks of obs
ARCH_RUSH = "RUSH"
ARCH_TURTLE = "TURTLE"
ARCH_CHOKE = "CHOKE"
ARCH_NEUTRAL = "NEUTRAL"

_CENTROIDS = {
    ARCH_RUSH:    (0.75, 0.66, 0.60, 0.25),
    ARCH_TURTLE:  (0.10, 0.00, 0.00, 0.50),
    ARCH_CHOKE:   (0.35, 0.33, 0.20, 0.15),
    ARCH_NEUTRAL: (0.50, 0.33, 0.30, 0.40),
}

_COUNTER = {
    ARCH_RUSH: {
        "f_invaderDist": 1.8,
        "f_numInvaders": 1.6,
        "f_patrolDist": 1.5,
        "f_onDefense": 1.5,
        "f_distToFood": 0.7,
        "f_distToCapsule": 0.7,
    },
    ARCH_TURTLE: {
        "f_distToFood": 1.6,
        "f_distToCapsule": 1.5,
        "f_successorScore": 1.4,
        "f_numInvaders": 0.5,  # barely any invaders in this world
        "f_patrolDist": 0.6,
    },
    ARCH_CHOKE: {
        "f_distToFood": 1.4,
        "f_distToCapsule": 1.4,
        "f_successorScore": 1.3,
        "f_ghostDist1": 1.3,
        "f_ghostDist2": 1.3,
        "f_inDeadEnd": 1.3,
    },
    ARCH_NEUTRAL: {},  # no-op
}


def _ensure_rc46_state():
    try:
        if not hasattr(TEAM, "rc46_stats"):
            TEAM.rc46_stats = {
                "tick": 0,
                "pacman_obs": 0,
                "ghost_obs": 0,
                "invader_crossings": 0,
                "last_is_pacman": {},
                "pacman_xs": [],     # x-coords of invader-pacmen when observed
                "initial_food": None,
            }
        if not hasattr(TEAM, "rc46_arch"):
            TEAM.rc46_arch = ARCH_NEUTRAL
        if not hasattr(TEAM, "rc46_classified"):
            TEAM.rc46_classified = False
    except Exception:
        pass


def _observe(agent, gameState):
    _ensure_rc46_state()
    try:
        stats = TEAM.rc46_stats
        stats["tick"] += 1
        if stats.get("initial_food") is None:
            try:
                stats["initial_food"] = len(agent.getFood(gameState).asList())
            except Exception:
                stats["initial_food"] = 20  # reasonable default

        walls = gameState.getWalls()
        mid_x = walls.width // 2
        our_side_is_left = agent.red

        for opp_idx in agent.getOpponents(gameState):
            try:
                opp_pos = gameState.getAgentPosition(opp_idx)
                if opp_pos is None:
                    continue
                st = gameState.getAgentState(opp_idx)
                is_pacman = bool(getattr(st, "isPacman", False))
                if is_pacman:
                    stats["pacman_obs"] += 1
                    # Depth: how far into OUR side (positive = deeper).
                    opp_x = int(opp_pos[0])
                    if our_side_is_left:
                        depth = max(mid_x - 1 - opp_x, 0)
                    else:
                        depth = max(opp_x - mid_x, 0)
                    stats["pacman_xs"].append(depth)
                else:
                    stats["ghost_obs"] += 1
                prev = stats["last_is_pacman"].get(opp_idx)
                if prev is False and is_pacman:
                    stats["invader_crossings"] += 1
                stats["last_is_pacman"][opp_idx] = is_pacman
            except Exception:
                continue
    except Exception:
        pass


def _classify(agent, gameState):
    _ensure_rc46_state()
    try:
        if TEAM.rc46_classified:
            return
        stats = TEAM.rc46_stats
        if stats["tick"] < RC46_OBSERVE_TICKS:
            return

        total = stats["pacman_obs"] + stats["ghost_obs"]
        if total == 0:
            TEAM.rc46_arch = ARCH_NEUTRAL
            TEAM.rc46_classified = True
            return

        v0 = stats["pacman_obs"] / total
        v1 = min(stats["invader_crossings"] / 3.0, 1.0)
        depths = stats.get("pacman_xs") or []
        if depths:
            # Normalize by mid-width (approx); clamp to [0,1].
            try:
                walls = gameState.getWalls()
                half_w = walls.width // 2
                v2 = min(sum(depths) / (len(depths) * max(half_w, 1)), 1.0)
            except Exception:
                v2 = 0.3
        else:
            v2 = 0.0

        try:
            current_food = len(agent.getFood(gameState).asList())
            init_food = stats.get("initial_food", 20)
            eaten = max(init_food - current_food, 0)
            v3 = min(eaten / max(init_food, 1), 1.0)
        except Exception:
            v3 = 0.3

        obs = (v0, v1, v2, v3)
        # Nearest centroid by squared Euclidean.
        best_arch = ARCH_NEUTRAL
        best_dist = float("inf")
        for arch, cent in _CENTROIDS.items():
            d = sum((obs[i] - cent[i]) ** 2 for i in range(4))
            if d < best_dist:
                best_dist = d
                best_arch = arch
        TEAM.rc46_arch = best_arch
        TEAM.rc46_classified = True
    except Exception:
        TEAM.rc46_classified = True
        TEAM.rc46_arch = ARCH_NEUTRAL


class ReflexRC46Agent(ReflexA1Agent):
    """A1 champion + K-centroid opponent classifier + counter policy."""

    def _chooseActionImpl(self, gameState):
        try:
            _observe(self, gameState)
            _classify(self, gameState)
        except Exception:
            pass
        return super()._chooseActionImpl(gameState)

    def _get_weights(self):
        base = super()._get_weights()
        try:
            if not getattr(TEAM, "rc46_classified", False):
                return base
            arch = getattr(TEAM, "rc46_arch", ARCH_NEUTRAL)
            mult = _COUNTER.get(arch, {})
            if not mult:
                return base
            adj = dict(base)
            for k, m in mult.items():
                if k in adj:
                    adj[k] = adj[k] * m
            return adj
        except Exception:
            return base


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC46Agent", second="ReflexRC46Agent"):
    return [ReflexRC46Agent(firstIndex), ReflexRC46Agent(secondIndex)]
