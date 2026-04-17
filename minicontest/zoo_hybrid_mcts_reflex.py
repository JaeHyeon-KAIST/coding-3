# zoo_hybrid_mcts_reflex.py
# -------------------------
# Path 3 paradigm hybrid (pm20, per CCG Codex+Gemini): heterogeneous team of
# MCTSQGuidedAgent on OFFENSE slot + ReflexA1Agent on DEFENSE slot.
#
# Rationale:
#   - Offense and defense are algorithmically different tasks. Offense is
#     pathfinding under threat (MCTS shines — tree search picks safe routes
#     through ghost zones to food clusters).
#   - Defense is interception of visible invaders (reflex argmax with
#     good weights suffices — f_invaderDist + f_onDefense + f_patrolDist).
#   - A1's W_OFF and W_DEF were CEM-tuned for this task-family split.
#
# Architecture:
#   firstIndex (lower)  -> MCTSQGuidedAgent with A1 W_OFF injected (OFFENSE)
#   secondIndex (higher) -> ReflexA1Agent (DEFENSE role via TEAM.role;
#                           _get_weights returns A1 W_DEF when role=DEFENSE)
#
# Time safety (pm20):
#   - MCTSQGuidedAgent budget (submission-time) = 0.80s < 1s turn limit
#   - ReflexA1Agent evaluator = O(N_legal * N_features) << 1ms
#   - Combined wall <0.81s per turn, never triggers framework warning
#
# Training-time safety (for future CEM of hybrid):
#   - Set env var ZOO_MCTS_MOVE_BUDGET=0.1 so MCTS wall stays under run_match
#     120s per-game timeout. Submission behavior unchanged.
#
# Never MCTS-evolves in this file — weights are A1 frozen. A future Order
# (Order 6+) could CEM-train offense-only MCTS weights with defense fixed.

from __future__ import annotations

from zoo_mcts_q_guided import MCTSQGuidedAgent
from zoo_reflex_A1 import ReflexA1Agent, _A1_OVERRIDE


def _pin_a1_weights(agent):
    """Attach A1 champion's (w_off, w_def, params) override dict to the
    agent so its `_get_weights()` returns A1 weights instead of seed."""
    if _A1_OVERRIDE.get("w_off"):
        agent._weights_override = _A1_OVERRIDE


def createTeam(firstIndex, secondIndex, isRed,
               first="MCTSQGuidedAgent", second="ReflexA1Agent"):
    """Construct a heterogeneous hybrid team.

    Slot assignment follows TEAM.role convention (lower-index = OFFENSE):
      - firstIndex (lower) -> MCTSQGuidedAgent pinned to A1 W_OFF.
      - secondIndex (higher) -> ReflexA1Agent (already loads A1 weights at
        init; uses W_DEF when TEAM.role[self.index]='DEFENSE').

    `first`/`second` kwargs are retained for CS188-harness compatibility but
    are not honored — slot classes are fixed for this hybrid identity. Any
    variant would be a separate file (e.g. zoo_hybrid_mcts_mcts.py).
    """
    offense = MCTSQGuidedAgent(firstIndex)
    _pin_a1_weights(offense)

    defense = ReflexA1Agent(secondIndex)
    # ReflexA1Agent's __init__ already attaches _A1_OVERRIDE if the weights
    # file is reachable; no further action needed.

    return [offense, defense]
