# zoo_reflex_rc33.py
# ------------------
# rc33: Persona-shifting overlay on A1 champion.
#
# Three tactical personas, selected per turn based on immediate game
# state (mirroring Gemini #17):
#
#   BULLY   — score = opponent-score + 0 and we have a scared ghost in
#             sight. We "bully" — chase kills aggressively. Multiplies
#             f_scaredGhostChase up, damps food attraction (we're
#             hunting, not harvesting).
#   COWARD  — we're a Pacman carrying ≥ 3 food on enemy side with an
#             active ghost within 5 distance. Amplifies ghost fear, damps
#             food greed, amplifies return-home urgency.
#   GHOST   — we're on our home side AND an invader is visible. Behaves
#             like a dedicated defender even if our role is nominally
#             offense — temporarily flips role.
#   DEFAULT — none of the above → pure A1.
#
# Persona is a per-turn decision (no hysteresis needed because each
# persona is self-consistent about when it fires, and triggers are
# stable within a tick).
#
# Like other overlays, no new features are introduced — we just scale
# A1's evolved weights inside `_get_weights`.

from __future__ import annotations

from zoo_core import TEAM
from zoo_reflex_A1 import ReflexA1Agent


# Persona weight multipliers.
_PERSONA_BULLY = {
    "f_scaredGhostChase": 2.5,
    "f_distToFood": 0.6,
    "f_distToCapsule": 0.7,
    "f_successorScore": 0.8,
    "f_ghostDist1": 0.3,  # reduce avoidance (we are hunting, ghost is scared)
    "f_ghostDist2": 0.3,
}
_PERSONA_COWARD = {
    "f_ghostDist1": 2.5,
    "f_ghostDist2": 2.0,
    "f_inDeadEnd": 2.0,
    "f_returnUrgency": 2.0,
    "f_distToHome": 1.8,
    "f_distToFood": 0.4,
    "f_distToCapsule": 0.5,
}
_PERSONA_GHOST = {
    # Flip to defender-ish. Defender weights live in DEFENSE dict
    # but rc33 layers on top of the active weight dict the agent's role
    # normally gets. So amplify defense-oriented terms:
    "f_invaderDist": 2.5,
    "f_numInvaders": 1.5,
    "f_patrolDist": 2.0,
    "f_onDefense": 2.0,
    "f_distToFood": 0.3,
    "f_successorScore": 0.4,
}


def _classify_persona(agent, gameState):
    """Return 'bully' / 'coward' / 'ghost' / 'default'. Never raises."""
    try:
        my_pos = gameState.getAgentPosition(agent.index)
        if my_pos is None:
            return "default"
        my_state = gameState.getAgentState(agent.index)
        carry = int(getattr(my_state, "numCarrying", 0) or 0)
        is_pacman = bool(getattr(my_state, "isPacman", False))

        # Scan opponents.
        has_scared_ghost = False
        nearest_active_ghost_dist = float("inf")
        has_invader = False
        for opp_idx in agent.getOpponents(gameState):
            try:
                opp_pos = gameState.getAgentPosition(opp_idx)
                if opp_pos is None:
                    continue
                opp_state = gameState.getAgentState(opp_idx)
                if getattr(opp_state, "isPacman", False):
                    has_invader = True
                    continue
                scared = int(getattr(opp_state, "scaredTimer", 0) or 0)
                d = agent.getMazeDistance(my_pos, opp_pos)
                if scared > 0:
                    if d <= 10:
                        has_scared_ghost = True
                else:
                    if d < nearest_active_ghost_dist:
                        nearest_active_ghost_dist = d
            except Exception:
                continue

        # BULLY — scared ghost nearby and we are Pacman (can actually land
        # on the ghost to eat it).
        if is_pacman and has_scared_ghost:
            return "bully"

        # COWARD — we are Pacman carrying enough, with active ghost within
        # 5 steps.
        if is_pacman and carry >= 3 and nearest_active_ghost_dist <= 5:
            return "coward"

        # GHOST — on home side with invader visible. (is_pacman==False is
        # "we're on our side".)
        if (not is_pacman) and has_invader:
            return "ghost"

        return "default"
    except Exception:
        return "default"


class ReflexRC33Agent(ReflexA1Agent):
    """A1 champion + 3-persona tactical weight modulation."""

    def _chooseActionImpl(self, gameState):
        self._rc33_persona = _classify_persona(self, gameState)
        return super()._chooseActionImpl(gameState)

    def _get_weights(self):
        base = super()._get_weights()
        persona = getattr(self, "_rc33_persona", "default")
        if persona == "default":
            return base
        if persona == "bully":
            mult = _PERSONA_BULLY
        elif persona == "coward":
            mult = _PERSONA_COWARD
        elif persona == "ghost":
            mult = _PERSONA_GHOST
        else:
            return base
        adj = dict(base)
        for k, m in mult.items():
            if k in adj:
                adj[k] = adj[k] * m
        return adj


def createTeam(firstIndex, secondIndex, isRed,
               first="ReflexRC33Agent", second="ReflexRC33Agent"):
    return [ReflexRC33Agent(firstIndex), ReflexRC33Agent(secondIndex)]
