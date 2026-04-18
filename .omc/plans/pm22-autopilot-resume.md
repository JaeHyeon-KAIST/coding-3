# pm22 Autopilot Resume — Session Handoff

**Origin**: pm21 session ended 2026-04-18 13:50 KST.
**Reason**: context reset for cost management; pm22 fresh session continues autopilot.
**Goal**: autopilot auto-handle Order 3 → Order 4 → STOP at S2 (Phase 4 manual).

## 🎯 pm22 First Actions (5 min)

### Step 1 — Read handoff (30s)
```bash
cat .omc/plans/pm22-autopilot-resume.md     # this file
cat .omc/state/autopilot-server-pipeline.json
```

### Step 2 — Check server (30s)
```bash
ssh jdl_wsl "cd ~/projects/coding-3 && \
  echo '=== tmux ==='; tmux capture-pane -t work -p -S -10 | tail -6; \
  echo '=== pgrep ==='; pgrep -af evolve.py | wc -l; \
  echo '=== final ==='; ls experiments/artifacts/final_weights.py 2>/dev/null && echo YES_FINAL || echo NO_FINAL; \
  echo '=== archives ==='; ls -d experiments/artifacts/phase2_*/ 2>/dev/null"
```

### Step 3 — Identify stage (immediate)

Compare result to stage table in `.omc/plans/autopilot-server-pipeline.md`:

| Observation | Stage | pm22 action |
|---|---|---|
| pgrep>0, NO_FINAL, 2-3 archives (A1_17dim, A1_B1_20dim only) | **S0-Order3** | Re-arm cron, wait |
| pgrep=0/1, YES_FINAL, 2 archives | **S1-Order3 ready** | Run S1 pipeline manually OR arm cron (fires immediately) |
| pgrep>0, NO_FINAL, 3 archives (+ phase2_A3_diverse_s1001_h1test) | **S0-Order4** | Re-arm cron, wait |
| pgrep=0/1, YES_FINAL, 3 archives | **S1-Order4 ready** | Run S1 pipeline manually OR arm cron |
| pgrep=0/1, NO_FINAL, 4 archives (+ phase2_A4_diverse_s2026_a1init) | **S2** | No more auto actions. Notify user. Cron stays off. |

### Step 4 — Re-arm cron (10s, if stage ∈ {S0-Order3, S0-Order4})

```
CronCreate(
  cron="7,37 * * * *",
  recurring=true,
  durable=true,
  prompt="Autopilot server pipeline check. Read .omc/plans/autopilot-server-pipeline.md and .omc/state/autopilot-server-pipeline.json. SSH jdl_wsl, identify stage, execute action AUTONOMOUSLY. Update state + PushNotification on transitions. STOP at S2 (Phase 4 manual per user directive)."
)
```

Record cron id in state file under `cron_id`.

### Step 5 — If S1 detected, run pipeline immediately

Don't wait for cron. Execute `.omc/plans/autopilot-server-pipeline.md` Stage S1 sub-steps:

S1.1 HTH Battery on server:
```bash
ssh jdl_wsl "cd ~/projects/coding-3 && .venv/bin/python experiments/hth_battery.py \
    --weights experiments/artifacts/final_weights.py \
    --opponents baseline monster_rule_expert zoo_reflex_h1test zoo_minimax_ab_d2 \
    --games-per-opp 200 60 40 40 --layouts defaultCapture RANDOM \
    --workers 16 --master-seed 42 \
    --out experiments/artifacts/hth_${ORDER_TAG}.csv 2>&1 | tail -15"
```

`ORDER_TAG` = `phase2_A3_diverse_s1001_h1test` (Order 3) or `phase2_A4_diverse_s2026_a1init` (Order 4).
`N` (wrapper number) = 3 or 4.

S1.2 Archive:
```bash
ssh jdl_wsl "cd ~/projects/coding-3 && mkdir -p experiments/artifacts/${ORDER_TAG} && \
    mv experiments/artifacts/2a_gen*.json experiments/artifacts/2b_gen*.json \
       experiments/artifacts/final_weights.py experiments/artifacts/hth_${ORDER_TAG}.csv \
       experiments/artifacts/${ORDER_TAG}/"
```

S1.3 Generate wrapper:
```bash
ssh jdl_wsl "cd ~/projects/coding-3 && .venv/bin/python experiments/make_hof_wrapper.py \
    --weights experiments/artifacts/${ORDER_TAG}/final_weights.py \
    --name zoo_reflex_O${N}"
```

S1.4 Sync + commit:
```bash
scp jdl_wsl:~/projects/coding-3/minicontest/zoo_reflex_O${N}.py minicontest/
cd "/Users/jaehyeon/KAIST/26 Spring/인공지능개론/coding 3" && \
  git add minicontest/zoo_reflex_O${N}.py && \
  git commit -m "pm22 autopilot: Order ${N} HTH + HOF wrapper" && \
  git push origin main
```

S1.5 Champion decision (rule):
- Parse hth CSV "baseline" row: Wilson LB
- If LB ≥ 0.80 AND > current champion's LB: re-flatten 20200492.py
  - Command: `.venv/bin/python experiments/flatten.py --agent zoo_reflex_tuned --weights experiments/artifacts/${ORDER_TAG}/final_weights.py --out minicontest/20200492.py`
  - Verify: `.venv/bin/python experiments/verify_flatten.py minicontest/20200492.py`
  - Commit + push
- Else: keep A1

S1.6 Server pull + next Order launch (only if N<4):
```bash
ssh jdl_wsl "cd ~/projects/coding-3 && rm -f minicontest/zoo_reflex_O${N}.py && \
    git pull origin main 2>&1 | tail -3 && \
    tmux send-keys -t work 'bash experiments/launch_orders_34.sh ${N+1}' Enter"
sleep 6 && ssh jdl_wsl "pgrep -af evolve.py | wc -l"   # expect 18
```

S1.7 Update state, notify, move on.

If N=4 (Order 4 done): skip S1.6 (no Order 5). Set stage=S2, CronDelete, notify user "Ready for Phase 4 tournament (manual)".

## 🗂️ State at handoff

- **current_order**: 3 (running)
- **next_order_num**: 4
- **champion**: A1 (from Order 2 decision: kept)
- **champion_wrapper**: zoo_reflex_A1
- **hof_wrappers**: [zoo_reflex_A1, zoo_reflex_O2]
- **hof_wrappers_needed**: [zoo_reflex_O3, zoo_reflex_O4]
- **order_tag** (Order 3): phase2_A3_diverse_s1001_h1test
- **order_tag** (Order 4): phase2_A4_diverse_s2026_a1init
- **phase4_launch_policy**: MANUAL (user will trigger separately)
- **terminal_stage**: S2

## 📁 Key files

| File | Purpose |
|---|---|
| `.omc/plans/autopilot-server-pipeline.md` | Authoritative pipeline + decision tree |
| `.omc/state/autopilot-server-pipeline.json` | Current stage, timestamps, champion |
| `experiments/launch_orders_34.sh` | Order 3/4 launch (HOF auto-detect) |
| `experiments/make_hof_wrapper.py` | Auto-generate zoo_reflex_O{N}.py from weights |
| `experiments/hth_battery.py` | HTH validation (200+200+60+40+40 games) |
| `experiments/flatten.py` | Flatten agent → 20200492.py for submission |
| `minicontest/zoo_reflex_O2.py` | Order 2 HOF wrapper (already in git) |
| `logs/phase2_A3_diverse_s1001_h1test_20260418-1314.log` | Order 3 log on server |

## 🕒 Expected Order 3/4 timing

Based on Order 2 observed walls (52 min/2a-gen, 34 min/2b-gen):
- Order 3 launch: 2026-04-18 13:14 KST
- Order 3 Phase 2a (10 gens × 52 min): ~8.7h → ~21:55 KST Apr 18
- Order 3 Phase 2b (20 gens × 34 min): ~11.3h → ~09:15 KST Apr 19
- Order 3 total: ~20h
- Order 4 launch: immediately after (~1 min S1 pipeline) → ~09:16 Apr 19
- Order 4 done: ~05:16 KST Apr 20

## 🛑 Hard stops (don't auto-proceed)

1. **Phase 4 tournament**: NEVER auto-launch. Wait for user.
2. **Submission 20200492.py**: Auto-reflatten ONLY when Wilson LB rule passes. Never silently overwrite on marginal differences (CI overlap).
3. **WSL crashed**: attempt recovery (wake via `ssh jdl "wsl -d Ubuntu-22.04 -- uptime"`, resume with `--resume-from`). If 3 wakes still stuck, PushNotification + stop auto-action.
4. **HTH shows crashes** or zero wins: investigate (might indicate weight-override bug). Don't proceed blindly.

## 🔔 Notification points (PushNotification)

- Order 3 complete + HTH + decision + Order 4 launched → "Order 3 done. Baseline WR {X}%. Order 4 launching."
- Order 4 complete + HTH + decision → "Order 4 done. Baseline WR {X}%. **Phase 4 manual — start when ready**."
- Any crash or failure → "🚨 Error: {details}. User intervention needed."

## 🔓 Canceling cron

Cron `7,37 * * * *` arms ~30-min checks. Auto-expires after 7 days. Manually cancel via `CronDelete({cron_id})` when S2 reached or user says stop.

## ⚠️ Anti-Patterns (pm21 learned)

- **Autopilot skill re-triggering**: the cron prompt includes keyword "autopilot" which reactivates OMC autopilot skill state. Stop hook blocks after each cron wake. Solution: after each cron wake that shows Order still running, if stop hook blocks → `state_write(mode=autopilot, active=false)` + `state_clear(mode=skill-active)`. Annoying but harmless.
- **Timezone confusion**: Mac and server both in KST. `date +%Y%m%d-%H%M` on server and Python `datetime.now(KST)` on Mac give same time. No conversion needed.
- **Gitignore traps**: `.omc/state/` is gitignored — state file is local runtime only. Don't try to commit it. Must be regenerated per session if manual resume.
