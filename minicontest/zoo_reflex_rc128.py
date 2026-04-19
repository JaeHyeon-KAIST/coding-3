# zoo_reflex_rc128.py
# ------------------
# rc128: rc09 (24-dim features) OFF + rc82 DEF.
#
# rc09 solo was 92.5%. Tests the rc82 DEF anchoring pattern with a
# feature-augmented offense.

from __future__ import annotations

from zoo_reflex_rc09 import ReflexRC09Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="rc128-offense", second="rc128-defense"):
    return [ReflexRC09Agent(firstIndex), ReflexRC82Agent(secondIndex)]
