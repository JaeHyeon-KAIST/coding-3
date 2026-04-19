# zoo_reflex_rc127.py
# ------------------
# rc127: Plain A1 OFF + rc82 DEF.
#
# Control test for the discovered pattern. If rc82 DEF alone carries
# compositions to 100%, then even the plainest A1 offense should
# reach 100%. A1 solo was 79% (pm19 HTH). rc127 isolates the DEF
# contribution.

from __future__ import annotations

from zoo_reflex_A1 import ReflexA1Agent
from zoo_reflex_rc82 import ReflexRC82Agent


def createTeam(firstIndex, secondIndex, isRed,
               first="rc127-offense", second="rc127-defense"):
    return [ReflexA1Agent(firstIndex), ReflexRC82Agent(secondIndex)]
