# Autopilot Server Pipeline (pm21)

**Purpose**: Autonomous server orchestration from Order 2 completion through
Order 3 → Order 4 → Phase 4 tournament. No user permission prompts.

**Invocation**: `CronCreate` fires this instruction file every 30 min. Claude
reads current server state, identifies stage, executes appropriate action.

**Termination**: When Phase 4 tournament CSV exists, call `CronDelete` and
`PushNotification` to signal completion.

---

## Procedure (each wake)

### Step 1 — Read state

Run state detection (server-side):

```bash
ssh jdl_wsl "cd ~/projects/coding-3 && \
  echo '=== tmux ==='; tmux capture-pane -t work -p -S -10 | tail -6; \
  echo '=== pgrep ==='; pgrep -af evolve.py | wc -l; \
  echo '=== current artifacts ==='; \
  ls experiments/artifacts/final_weights.py 2>/dev/null && echo YES_FINAL; \
  ls experiments/artifacts/2a_gen*.json 2>/dev/null | wc -l; \
  ls experiments/artifacts/2b_gen*.json 2>/dev/null | wc -l; \
  echo '=== archived phases ==='; \
  ls -d experiments/artifacts/phase2_*/ 2>/dev/null"
```

Classify into ONE of these stages:

| # | Trigger | Meaning |
|---|---|---|
| **S0** | `pgrep>0` AND no `final_weights.py` | Order running. Report progress, no action. |
| **S1** | `pgrep==0` AND `final_weights.py` exists AND no new archive dir since last check | Order just finished. Run validate+archive+next-launch pipeline below. |
| **S2** | all planned Orders archived (A1, A1_B1_20dim, Order3, Order4 dirs exist) | All CEM done → launch Phase 4 tournament. |
| **S3** | `experiments/artifacts/phase4_tournament.csv` exists | All done → cleanup + terminate. |

### Step 2 — Action per stage

#### S0: Order still running

Do nothing except report progress in notepad. Format:

```
[autopilot S0] {timestamp} Order {N} gen {X}/{total} best={Y} wall={Z}min ETA {H}h{M}m
```

No other action. Return.

#### S1: Order just completed — run full pipeline

**S1.1 HTH Battery on server** (~30-60s):

```bash
ssh jdl_wsl "cd ~/projects/coding-3 && .venv/bin/python experiments/hth_battery.py \
    --weights experiments/artifacts/final_weights.py \
    --opponents baseline monster_rule_expert zoo_reflex_h1test zoo_minimax_ab_d2 \
    --games-per-opp 200 60 40 40 --layouts defaultCapture RANDOM \
    --workers 16 --master-seed 42 \
    --out experiments/artifacts/hth_\${ORDER_TAG}.csv 2>&1 | tail -15"
```

Parse Wilson CI lower bound vs `baseline`. Decide champion:
- Wilson LB ≥ 0.80 AND > current champion's LB → promote to champion
- Else → keep current champion

**S1.2 Archive artifacts** on server:

```bash
ssh jdl_wsl "cd ~/projects/coding-3 && mkdir -p experiments/artifacts/${ORDER_TAG} && \
    mv experiments/artifacts/2a_gen*.json experiments/artifacts/2b_gen*.json \
       experiments/artifacts/final_weights.py experiments/artifacts/hth_${ORDER_TAG}.csv \
       experiments/artifacts/${ORDER_TAG}/"
```

`${ORDER_TAG}` derivation:
- Order 2 done → `phase2_A1_B1_20dim`
- Order 3 done → `phase2_A3_diverse_s1001_h1test`
- Order 4 done → `phase2_A4_diverse_s2026_a1init`

**S1.3 Generate HOF wrapper** on server, scp to Mac:

```bash
ssh jdl_wsl "cd ~/projects/coding-3 && .venv/bin/python experiments/make_hof_wrapper.py \
    --weights experiments/artifacts/${ORDER_TAG}/final_weights.py \
    --name zoo_reflex_O${N}"
scp jdl_wsl:~/projects/coding-3/minicontest/zoo_reflex_O${N}.py minicontest/
```

Where `${N}` = 2, 3, 4 for Orders 2, 3, 4.

**S1.4 Commit + push**:

```bash
cd "/Users/jaehyeon/KAIST/26 Spring/인공지능개론/coding 3" && \
  git add minicontest/zoo_reflex_O${N}.py && \
  git commit -m "pm21 autopilot: Order ${N} champion HOF wrapper (zoo_reflex_O${N})" && \
  git push origin main
```

**S1.5 Push notification**:

```
PushNotification "Order ${N} done. HTH: baseline {WR}% [{LB}-{UB}]. Champion: {A1|O${N}}. Order ${N+1} launching."
```

**S1.6 Launch next Order** (if Order 2/3):

```bash
ssh jdl_wsl "cd ~/projects/coding-3 && git pull origin main 2>&1 | tail -3 && \
  tmux send-keys -t work 'bash experiments/launch_orders_34.sh ${NEXT}' Enter"
```

Where `${NEXT}` = 3 or 4 respectively.

For Order 3 and 4, we want the HOF pool to grow (include all prior champion wrappers). **Edit `experiments/launch_orders_34.sh`** to include them before launching:

```bash
# After generating zoo_reflex_O2.py, ensure Order 3's pool includes it
# After zoo_reflex_O3.py, Order 4's pool includes both O2 and O3
```

If launch_orders_34.sh has `zoo_reflex_A1` hardcoded in opponent list, edit to add:
- Order 3: `zoo_reflex_A1 zoo_reflex_O2`
- Order 4: `zoo_reflex_A1 zoo_reflex_O2 zoo_reflex_O3`

Commit the script change + push.

**S1.7 Verify launch**:

```bash
sleep 5 && ssh jdl_wsl "tmux capture-pane -t work -p | tail -5 && pgrep -af evolve.py | wc -l"
```

Expect 17-18 processes. If 0/1, launch failed — PushNotification error + diagnose.

#### S2: All Orders done → Phase 4 tournament

Launch round-robin across ALL candidates:
- A1, Order 2/3/4 champion wrappers + zoo_reflex_A1 + zoo_reflex_O{2,3,4}
- Mac-generated hybrids: zoo_reflex_A1_{D1,D2,D3,D13,T4,T5}

```bash
ssh jdl_wsl "cd ~/projects/coding-3 && git pull origin main 2>&1 | tail -3 && \
  .venv/bin/python experiments/tournament.py \
    --agents zoo_reflex_A1 zoo_reflex_O2 zoo_reflex_O3 zoo_reflex_O4 \
             zoo_reflex_A1_D1 zoo_reflex_A1_D2 zoo_reflex_A1_D3 \
             zoo_reflex_A1_D13 zoo_reflex_A1_T4 zoo_reflex_A1_T5 \
    --anchor baseline --layouts defaultCapture RANDOM \
    --seeds 101 202 303 404 505 --workers 16 \
    --out experiments/artifacts/phase4_tournament.csv 2>&1 | tee logs/phase4_tournament.log | tail -20"
```

(May need to adapt to actual tournament.py CLI — check arg compatibility first.)

**S2 commit**: copy phase4_tournament.csv back to Mac, commit.

```bash
scp jdl_wsl:~/projects/coding-3/experiments/artifacts/phase4_tournament.csv experiments/artifacts/
```

PushNotification: "Phase 4 complete. Top-3: [list]"

#### S3: Tournament done → terminate

```
CronDelete {cron_id}
PushNotification "🎉 Autopilot pipeline complete. Phase 4 results in experiments/artifacts/phase4_tournament.csv. Next: Phase 5 multi-seed top-3 validation (manual)."
```

---

## Safety rails

- If ANY command fails with non-zero exit code, do NOT retry more than 1× per wake.
  On repeated failure (same error 3 wakes), PushNotification error + skip until
  user intervention.
- Verify git status is clean before committing HOF wrappers (no accidental
  staging of other files).
- Never modify `baseline.py`, `capture.py`, or other frozen framework files.
- If WSL dies mid-Order, detect via `pgrep==0 AND no final_weights.py`:
  - Wake WSL: `ssh jdl "wsl -d Ubuntu-22.04 -- uptime"`
  - Re-launch with `--resume-from experiments/artifacts/`
  - If resume fails, PushNotification + stop.

## Recovery from stale state

If the autopilot's notion of "current Order" doesn't match reality (e.g.,
user manually launched something), re-derive from `ls experiments/artifacts/phase2_*/`
directories. Order N done iff `phase2_*N_tag*/final_weights.py` exists.

## State file

Autopilot writes progress + last-action to `.omc/state/autopilot-server-pipeline.json`:

```json
{
  "last_wake": "2026-04-18T09:07:00+09:00",
  "current_order": 3,
  "last_action": "launched_order_3",
  "champion": "A1",
  "hof_wrappers": ["zoo_reflex_A1", "zoo_reflex_O2"],
  "cron_id": "{from_CronCreate}"
}
```

Read this first each wake; update on any meaningful action.
