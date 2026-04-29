## Handoff: team-plan → team-exec

- **Decided**: Tri-advisor parallel consultation (no shared visibility — each gives independent view, then lead synthesizes). Workers: claude-analyst (independent algorithmic analysis), codex-cli (external Codex CLI consult), gemini-cli (external Gemini CLI consult). Lead synthesizes.
- **Rejected**:
  - Sequential consultation (analyst sees CLI outputs first) — would bias analyst toward CLI hypotheses, defeating "independent perspective" purpose.
  - Spawning codex/gemini as tmux CLI workers via team skill — Claude executor calling Bash directly is simpler, retains team-message channel for results.
  - Adding code-reviewer/critic to verify synthesis — synthesis is a recommendation document, not a code change. Acceptance is user-driven (next step is "pick which improvements to implement").
- **Risks**:
  - CLI advisors may hallucinate file paths or code structure → workers must NOT execute CLI suggestions, only collect and summarize them. Implementation is a separate user decision.
  - Codex/Gemini CLI prompts must include enough context (CAPX code excerpt, defender weakness data) — too thin = generic answers; too thick = token waste.
  - Codex CLI may take 2-5 min per consult; gemini similar. Schedule 8 min wall budget per worker.
- **Files**: 
  - Reference (read-only for workers): `minicontest/zoo_reflex_rc_tempo_capx.py`, `.omc/plans/omc-pm46-v2-capsule-only-attacker.md`, `.omc/wiki/pm46-v2-FINAL-recovery-17-of-17.md`, `.omc/wiki/pm46-v2-capx-code-review-phase4-tuning.md`
  - Output (worker → lead): `.omc/research/pm46-v2-ccg/{claude-analyst,codex,gemini}-summary.md`
  - Output (lead → user): `.omc/wiki/pm46-v2-ccg-improvement-consultation.md`
- **Remaining**:
  - team-exec: spawn 3 workers in parallel; collect 3 summary docs.
  - team-verify (lead-only): synthesize → ranked list with implementation cost estimates.
  - Shutdown + TeamDelete after wiki commit (commit deferred — user reviews first).

## Out-of-scope (per user reframing in SESSION_RESUME)
- Submission code modification (`your_best.py`, `20200492.py`).
- ABS attacker code change.
- pm47 integration decision (separate session).

## Weak-defender focus (per SESSION_RESUME)
- zoo_reflex_capsule (40% eat_alive)
- zoo_reflex_tuned (40% eat_alive)
- zoo_reflex_aggressive (50% eat_alive, 6.7% died_pre_eat — highest)

## Code-review queue (from `.omc/wiki/pm46-v2-capx-code-review-phase4-tuning.md`)
- 1 HIGH (cross-game state pollution — mitigated by 1-game-per-process harness)
- 4 MEDIUM (`_p_survive` off-by-one, A* cache origin tag, `_safest_step_toward` defender-weight, scared ghost filter)
- 4 LOW (cap-eaten Manhattan, mission-complete STOP forever, no wall-time circuit breaker)
