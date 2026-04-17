---
title: "Server Order-queue operational runbook — launch/archive/verify cycle"
tags: ["runbook", "server", "jdl_wsl", "tmux", "order-queue", "archival", "verification", "hth-battery", "pm19"]
created: 2026-04-17T03:47:48.326Z
updated: 2026-04-17T03:47:48.326Z
sources: ["pm18 A1 launch pattern", "pm19 A1 archival + Order 2 launch", "pm19 hth_battery.py absolute-path gotcha"]
links: []
category: pattern
confidence: high
schemaVersion: 1
---

# Server Order-queue operational runbook — launch/archive/verify cycle

# Server Order-queue operational runbook

Canonical cycle for running one evolve `Order N` on server (jdl_wsl) and promoting results.

## 1. Pre-launch verification (~10s)

```bash
ssh jdl_wsl "echo '=== tmux ==='; tmux list-sessions; echo '=== git ==='; cd ~/projects/coding-3 && git log --oneline -3; echo '=== artifacts ==='; ls experiments/artifacts/ | head -20; echo '=== uptime ==='; uptime"
```

Expected:
- `work` session alive
- Git HEAD matches Mac
- `experiments/artifacts/` clean except `genomes/` `__pycache__/` and any previous-Order archive folders
- Load avg reasonable (< 30 usually means no zombie evolve from previous run)

## 2. Pull any new Mac commits (if needed)

```bash
ssh jdl_wsl "cd ~/projects/coding-3 && git status --short"
# If working tree has uncommitted changes (rare):
ssh jdl_wsl "cd ~/projects/coding-3 && git stash push -m 'order-N-prep'"
# Pull:
ssh jdl_wsl "cd ~/projects/coding-3 && git pull origin main 2>&1 | tail -10"
```

If `pull` errors "untracked working tree files would be overwritten" (e.g., from prior `scp`):
```bash
ssh jdl_wsl "cd ~/projects/coding-3 && rm experiments/hth_battery.py"  # or whatever the conflict file is
ssh jdl_wsl "cd ~/projects/coding-3 && git pull origin main"
```

## 3. Archive previous Order's artifacts (CRITICAL — evolve.py overwrites)

```bash
ssh jdl_wsl "cd ~/projects/coding-3 && mkdir -p experiments/artifacts/phase2_<ORDER_TAG>/ && mv experiments/artifacts/2a_gen*.json experiments/artifacts/2b_gen*.json experiments/artifacts/final_weights.py experiments/artifacts/hth_*.{csv,json} experiments/artifacts/phase2_<ORDER_TAG>/"
```

`<ORDER_TAG>` examples: `A1_17dim`, `A1_B1_20dim`, `A2_B1_h1b_init_20dim`.

## 4. Launch next Order via tmux send-keys

**Generic template** (adapt `--init-mean-from` / `--games-per-opponent` / `--opponents`):

```bash
ssh jdl_wsl 'tmux send-keys -t work "cd ~/projects/coding-3 && .venv/bin/python experiments/evolve.py --phase both --master-seed 42 --workers 16 --n-gens-2a 10 --n-gens-2b 20 --pop 40 --rho 0.35 --games-per-opponent-2a 24 --games-per-opponent-2b 16 --init-mean-from h1test --opponents baseline baseline zoo_reflex_h1test zoo_reflex_h1b zoo_reflex_h1c zoo_reflex_aggressive zoo_reflex_defensive zoo_minimax_ab_d2 zoo_minimax_ab_d3_opp zoo_expectimax monster_rule_expert --layouts defaultCapture RANDOM 2>&1 | tee logs/phase2_<NAME>_$(date +%Y%m%d-%H%M).log" Enter'
```

Substitutions:
- `<NAME>`: `A1_B1_20dim`, `A2_B1_h1b_20dim`, etc.
- `--init-mean-from`: `h1test` (A1/A1+B1), `h1b` (A2), or add `hybrid` if evolve.py supports (currently doesn't — use h1test or h1b).

## 5. Post-launch verification (~5s wait then check)

```bash
sleep 4 && ssh jdl_wsl 'echo "=== pgrep ==="; pgrep -af evolve.py | wc -l; echo "=== tmux pane ==="; tmux capture-pane -t work -p | tail -8; echo "=== log ==="; ls logs/phase2_*_$(date +%Y%m%d)*.log 2>/dev/null | tail -3'
```

Expected:
- 18 processes (1 parent + 16 workers + 1 bash child)
- tmux pane shows `[evolve] starting Phase 2a (shared W, 10 gens, pop=40, workers=16, init_mean=h1test)`
- Log file created (just header line initially)

## 6. Set up persistent Monitor (Mac-side)

```python
# Using Claude's Monitor tool
Monitor(
  description="Order N (<desc>) gen completions + errors",
  persistent=True,
  timeout_ms=3600000,
  command=f"ssh jdl_wsl \"tail -F ~/projects/coding-3/logs/phase2_{NAME}_{timestamp}.log 2>/dev/null\" | grep -E --line-buffered '\\[evolve\\]|Traceback|Error|BrokenProcessPool|Killed|OOM|CRASH|FAILED|forfeit'"
)
```

Monitor will emit 1 event per gen completion (~every 35-50 min) for the full 18-20h run. Also catches stagnation / restart triggers / traceback lines.

## 7. On completion: HTH validation

```bash
# On server, use hth_battery.py with the new order's final_weights.py
ssh jdl_wsl "cd ~/projects/coding-3 && .venv/bin/python experiments/hth_battery.py --weights experiments/artifacts/final_weights.py --opponents baseline monster_rule_expert zoo_reflex_h1test zoo_minimax_ab_d2 --games-per-opp 200 60 40 40 --layouts defaultCapture RANDOM --workers 16 --master-seed 42 --out experiments/artifacts/hth_<ORDER_TAG>.csv 2>&1 | tail -15"
```

Expect Wilson 95% CI per opponent. Compare to A1's baseline 79.0% [0.728, 0.841].

**CRITICAL GOTCHA**: `hth_battery.py` requires weights JSON at ABSOLUTE path. If you ever modify the script, ensure the `weights=<path>` arg is `.resolve()`-ed. Symptom of relative-path bug: 0% WR across all 340 games (zoo_reflex_tuned seed-weight deadlock signature).

## 8. Promotion decision

- If new Order's baseline WR (Wilson LB) **>** A1's 0.728: promote to current champion
- If <= A1 with similar CI: keep A1; still archive Order N data for Phase 4 tournament
- If much worse (LB < 0.51): investigate — pool drift? init_mean failure? dead PARAMS too noisy? (see wiki `decision/ccg-revised-phase-2-scope-pm19`)

## 9. Launch next Order in queue

Repeat from step 3 (archive current Order, update `<ORDER_TAG>`, swap `--init-mean-from`).

## Anti-patterns

- ❌ Launching next Order without archiving → previous artifacts silently overwritten
- ❌ Using relative path in `weights=<path>` override arg
- ❌ Not verifying pgrep count after launch (could silently crash in gen 0 setup)
- ❌ Letting a crash log accumulate without reading (pm19's Order 2 had fixed sigma bug; new bugs may differ)
- ❌ Forgetting to `git push` Mac commits before server pull (causes "Already up to date" false negative)

