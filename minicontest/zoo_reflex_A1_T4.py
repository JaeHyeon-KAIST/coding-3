# zoo_reflex_A1_T4.py
# -------------------
# A1 champion weights + T4 online opponent classification.
#
# Observes enemy behavior for the first 50 ticks of a game, classifies them
# as AGGRESSIVE / DEFENSIVE / BALANCED, then applies per-mode multiplicative
# weight scaling on top of A1's evolved weights. Observation + classification
# state lives on the TEAM singleton so both our agents share it.
#
# Classification axes:
#   - enemy_pacman_ratio = pacman_obs / total_obs (how often enemies seen as
#     Pacman -> they're on our side = aggressive raiders)
#   - invader_crossings = count of transitions (ghost -> pacman), i.e.
#     enemy crossing into our territory
#   - enemy_ghost_ratio = ghost_obs / total_obs
#
# Modes:
#   AGGRESSIVE_OPP     (pacman_ratio>=0.40 OR invader_crossings>=1):
#                      opponent rushes us -> boost our defensive features
#                      (invader distance, patrol, numInvaders aversion)
#   DEFENSIVE_OPP      (ghost_ratio>=0.80 AND no invader crossings):
#                      opponent turtles -> boost our offensive push
#                      (food, capsule, successor score)
#   BALANCED           (neither): no adjustment (A1 default)
#
# All weight adjustments are multiplicative with safe fallback. Counter-mode
# scaling magnitudes are conservative (1.2-1.6x) to avoid over-correction
# that could destabilize A1's CEM-tuned equilibrium.
#
# The classifier fires ONCE (at tick >= 50) and then holds the mode for the
# remaining ~1150 ticks — no hysteresis, no re-classification. Rationale:
# at 180-student tournament scale, reclassifying mid-game is noisier than
# sticking with the first-50-tick read.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent

# Classification hyperparameters.
T4_OBSERVE_TICKS = 50
T4_AGGRESSIVE_PACMAN_RATIO = 0.40
T4_AGGRESSIVE_INVADER_COUNT = 1
T4_DEFENSIVE_GHOST_RATIO = 0.80

# Mode constants.
MODE_BALANCED = "BALANCED"
MODE_AGGRESSIVE_OPP = "AGGRESSIVE_OPP"
MODE_DEFENSIVE_OPP = "DEFENSIVE_OPP"


def _ensure_t4_state():
    """Initialize TEAM fields for T4 if not present. Idempotent."""
    try:
        if not hasattr(TEAM, "t4_stats"):
            TEAM.t4_stats = {
                "tick": 0,
                "pacman_obs": 0,
                "ghost_obs": 0,
                "invader_crossings": 0,
                # enemy_idx -> last observed isPacman (True/False) or None
                "last_is_pacman": {},
            }
        if not hasattr(TEAM, "t4_mode"):
            TEAM.t4_mode = MODE_BALANCED
        if not hasattr(TEAM, "t4_classified"):
            TEAM.t4_classified = False
    except Exception:
        pass


def _apply_counter_mode(weights: dict, mode: str) -> dict:
    """Return a shallow-copied weight dict adjusted for the given mode.
    Multiplicative scaling on sign-preserving keys; sign-FLIP on f_onDefense
    where necessary to actually stay home against aggressive opponents.
    """
    if mode == MODE_BALANCED:
        return weights
    adj = dict(weights)
    if mode == MODE_AGGRESSIVE_OPP:
        # Opponent rushes -> strengthen our defense.
        if "f_invaderDist" in adj:
            adj["f_invaderDist"] = adj["f_invaderDist"] * 1.5
        if "f_patrolDist" in adj:
            adj["f_patrolDist"] = adj["f_patrolDist"] * 1.4
        if "f_numInvaders" in adj:
            adj["f_numInvaders"] = adj["f_numInvaders"] * 1.5
        # f_onDefense in A1 is NEGATIVE (-7.79 off / -12.12 def) — agent
        # learned attack bias. For aggressive opp, push back toward home by
        # additive positive shift.
        if "f_onDefense" in adj:
            adj["f_onDefense"] = adj["f_onDefense"] + 20.0
        # Slightly reduce greedy offense pull.
        if "f_distToFood" in adj:
            adj["f_distToFood"] = adj["f_distToFood"] * 0.85
        if "f_distToCapsule" in adj:
            adj["f_distToCapsule"] = adj["f_distToCapsule"] * 0.85
    elif mode == MODE_DEFENSIVE_OPP:
        # Opponent turtles -> push harder on offense.
        if "f_distToFood" in adj:
            adj["f_distToFood"] = adj["f_distToFood"] * 1.4
        if "f_distToCapsule" in adj:
            adj["f_distToCapsule"] = adj["f_distToCapsule"] * 1.4
        if "f_successorScore" in adj:
            adj["f_successorScore"] = adj["f_successorScore"] * 1.3
        # Reduce over-aversion — they're not invading anyway.
        if "f_numInvaders" in adj:
            adj["f_numInvaders"] = adj["f_numInvaders"] * 0.6
        if "f_patrolDist" in adj:
            adj["f_patrolDist"] = adj["f_patrolDist"] * 0.7
    return adj


class ReflexA1T4Agent(ReflexA1Agent):
    """A1 weights + online opponent classifier (first 50 ticks)."""

    def _observe(self, gameState):
        """Count enemy observations for this tick. Safe under exceptions."""
        _ensure_t4_state()
        try:
            stats = TEAM.t4_stats
            # Tick counter advances on any agent's observation; we call this
            # only from our own chooseAction so tick = our-turn-count which
            # is ~half of game ticks. T4_OBSERVE_TICKS=50 means ~100 game
            # ticks of observation window (5-10% of a 1200-tick game).
            stats["tick"] += 1

            for opp_idx in self.getOpponents(gameState):
                try:
                    opp_pos = gameState.getAgentPosition(opp_idx)
                    if opp_pos is None:
                        continue  # out of sensor range
                    opp_state = gameState.getAgentState(opp_idx)
                    is_pacman = bool(getattr(opp_state, "isPacman", False))
                    if is_pacman:
                        stats["pacman_obs"] += 1
                    else:
                        stats["ghost_obs"] += 1
                    prev = stats["last_is_pacman"].get(opp_idx)
                    # Transition ghost -> pacman counts as one invader crossing.
                    if prev is False and is_pacman:
                        stats["invader_crossings"] += 1
                    stats["last_is_pacman"][opp_idx] = is_pacman
                except Exception:
                    continue
        except Exception:
            pass

    def _classify_if_ready(self):
        """Run classification once at tick >= T4_OBSERVE_TICKS. Never raises."""
        _ensure_t4_state()
        try:
            if TEAM.t4_classified:
                return
            stats = TEAM.t4_stats
            if stats["tick"] < T4_OBSERVE_TICKS:
                return
            total = stats["pacman_obs"] + stats["ghost_obs"]
            if total == 0:
                TEAM.t4_mode = MODE_BALANCED
            else:
                pacman_ratio = stats["pacman_obs"] / total
                ghost_ratio = stats["ghost_obs"] / total
                if (pacman_ratio >= T4_AGGRESSIVE_PACMAN_RATIO
                        or stats["invader_crossings"] >= T4_AGGRESSIVE_INVADER_COUNT):
                    TEAM.t4_mode = MODE_AGGRESSIVE_OPP
                elif (ghost_ratio >= T4_DEFENSIVE_GHOST_RATIO
                        and stats["invader_crossings"] == 0):
                    TEAM.t4_mode = MODE_DEFENSIVE_OPP
                else:
                    TEAM.t4_mode = MODE_BALANCED
            TEAM.t4_classified = True
        except Exception:
            TEAM.t4_classified = True  # never re-classify on error
            TEAM.t4_mode = MODE_BALANCED

    def _get_weights(self):
        """A1 weights adjusted by TEAM.t4_mode once classified."""
        base_w = super()._get_weights()
        try:
            if not getattr(TEAM, "t4_classified", False):
                return base_w
            mode = getattr(TEAM, "t4_mode", MODE_BALANCED)
            return _apply_counter_mode(base_w, mode)
        except Exception:
            return base_w

    def _chooseActionImpl(self, gameState):
        try:
            self._observe(gameState)
            self._classify_if_ready()
        except Exception:
            pass
        return super()._chooseActionImpl(gameState)


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexA1T4Agent", second="ReflexA1T4Agent"):
    return [ReflexA1T4Agent(firstIndex), ReflexA1T4Agent(secondIndex)]
