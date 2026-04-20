# SESSION_RESUME — 5-minute onboarding for any new Claude or human session

**Last updated:** 2026-04-20 pm29 END — **rc-tempo V0.1 β 구현 + 2000g HTH 검증 완료**:
- 🏆 **rc-tempo β**: 2000g HTH overall **68.6% WR** [0.666, 0.706], **71% H2H vs rc82**, **100% vs h1test on distant**.
- ✅ **β = rc-tempo V0.1 submission candidate** (tournament 30pt, rc82 H2H 우위).
- ❌ **γ REJECTED**: 0/200 vs rc166 default (catastrophic). Entry-DP 아이디어는 V0.2 재설계.
- 📊 **β vs γ H2H**: 101/200 (50.5% coin flip).
- 📐 **Files**: `minicontest/{zoo_rctempo_core, zoo_reflex_rc_tempo_beta, zoo_reflex_rc_tempo_gamma}.py`, `experiments/rc_tempo/{hth_resumable, analyze_hth, capsule_safety, two_agent_split, viz_risk}.py`.
- 📄 **Session log**: `.omc/wiki/2026-04-20-pm29-rc-tempo-v01-beta-gamma-hth.md`.

## pm30 TL;DR (NEXT SESSION — READ FIRST)

### 🎯 pm30 immediate priorities

1. **Phase 4 round-robin tournament** — Pool expanded with rc-tempo β. Dispatch server 16-worker.
2. **M7 flatten** — rc166 → `20200492.py` (primary, 98.5% 200g baseline). Optionally rc-tempo β → alt submission.
3. **M8 output.csv** — populate `your_baseline{1,2,3}.py` + final.
4. **M9 ICML report** — rc-tempo paradigm as distinctive methodology.

### 📊 pm29 Leaderboard (vs rc-tempo β, 200g per cell)

| Opponent | default WR | distant WR |
|---|---|---|
| baseline | 95.0% | 78.0% |
| rc82 | **71.0%** 🏆 | 51.5% |
| rc166 | 50.0% | 53.5% |
| monster | 66.0% | 44.5% |
| h1test | 77.0% | **100.0%** 🏆 |

### ⚠️ Known issues / TODOs

- γ HTH partial (1577/2000 before WSL dropped) — 재시작 완료, 추후 분석만 하면 됨
- `RCTEMPO_METRICS_CSV` env propagation 작동 안 함 (ProcessPool subprocess chain 이슈) — WR 데이터로 충분
- **your_best/baseline{1,2,3}.py 여전히 DummyAgent** — M7 flatten 필요

### 📂 Critical reference docs

- `.omc/plans/rc-tempo-design.md` — V0.1 original design (일부 revision 필요 — strategic는 static unsafe, 실제로 제외됨)
- `.omc/wiki/2026-04-20-pm29-rc-tempo-v01-beta-gamma-hth.md` — pm29 full session log
- `experiments/artifacts/rc_tempo/hth_beta.csv` — 2000g β HTH raw data
- `experiments/artifacts/rc_tempo/hth_gamma.csv` — γ HTH raw data
- `experiments/rc_tempo/analyze_hth.py` — per-opp Wilson CI analyzer

---

**Last updated:** 2026-04-20 pm28 END — **rc-tempo V0.1 설계 완료 (미구현), Server Order 4 분석 완료**:
- 🏁 **rc-tempo V0.1 design locked** → `.omc/plans/rc-tempo-design.md` (상세). 다음 세션 구현 착수.
- 🧠 **Paradigm novel**: 우리 rc 139개 중 첫 **deterministic orienteering** agent. User-driven design (pm28 전체 세션).
- 📐 **Key insight (user)**: 40 scared 창은 "개수 max"가 아닌 **"위험 food 우선"** (dead-end/funnel) weighted DP. 쉬운 food는 Agent B 또는 후속 trip에서.
- ⏱️ **DP 실측**: defaultCapture 0.12s / distantCapture 0.22s / strategicCapture 2.32s — 모두 15초 init 예산 내.
- 🔢 **Ceiling (DP)**: default 7 / distant 9 / strategic 13 food per scared trip. +B swarm +entry = 1 trip ~12-21 food deposit (18 game-end).
- 🎯 **Server Order 4 (A4)**: fitness 0.968 peak, A1(1.065) 미달. 건강한 수렴 (gen 15 peak + 4 gen stagnation). `experiments/artifacts/final_weights.py` 서버 root에 unarchived.
- ⚠️ **your_best/baseline1/2/3.py 전부 아직 DummyAgent** (2021 원본). 제출 직전 flatten 필수.

## pm29 TL;DR (NEXT SESSION — READ FIRST)

### 🎯 pm29 immediate priorities (in order)

1. **rc-tempo V0.1 구현** (1일) — 13 tasks in TaskList. 순서:
   - Task #1 스켈레톤 → #10 fallback → #2 topology → #13 risk map → #3 food split → #4 entry → #5 weighted DP → #8/#9 runtime → #11 HTH test → #12 AI_USAGE
   - **Design doc**: `.omc/plans/rc-tempo-design.md` (READ FIRST)
   - 100g HTH 목표: vs baseline ≥ 97% (rc82 동급), H2H vs rc82 ≥ 50% (초월 후보)

2. **서버 A4 archive** (5분) — ssh jdl_wsl, `experiments/artifacts/` 루트 2a/2b gen JSON + final_weights.py를 `phase2_A4_s2026_a1init_20dim/` 로 이동. Mac pull.

3. **Phase 4 라운드 로빈 검토** — rc-tempo 구현 후 Pool에 추가. rc166 vs rc-tempo vs rc82 tier 확정.

4. **your_best.py 채우기** — Phase 4 챔피언 (rc166 or rc-tempo) flatten via `experiments/flatten_multi.py`. **your_baseline1/2/3** 도 동시 채움 (M8 output.csv 용).

### 📐 rc-tempo V0.1 설계 핵심 (user-driven)

**Paradigm**: Precomputed orienteering (not reactive). 맵 정보 static → init 15s에 전체 trip 계획 baked.

**Phase state machine:**
1. Entry: precomputed route, skip too-deep food (`depth > max_opp_depth × 0.85`)
2. Capsule approach: A within 5 → swarm_safe 체크 → B midline pre-position
3. **Scared (40 move)**: A executes **weighted DP** (risk sum max, not count max). B crosses midline → safe food cleanup.
4. Deposit: A role-flip to defense.
5. 2nd cycle: rc82 reactive

**Weighted orienteering objective:**
```
risk(f) = 3 × dead_end_depth
        + 2 × ap_count_on_path_to_home
        + 0.5 × dist_to_home / 10
        + 5 × (low_voronoi_margin)
        + 2 × isolated_food
```
DP bitmask. Same state space, only `best_state` 판정이 `risk_sum` 기준.

**왜 weighted?** Scared 창은 "평소 위험해서 못 먹는 food" 전용. 일반 food는 언제든 후속 trip.

**Agent A vs B:**
- A: DP로 고위험 food 우선 (dead-end, funnel, 외톨이)
- B: swarm join 후 저위험 food cleanup (개수 극대화)

### 🔒 V0.1 Scope (lock)

**타겟 (1 capsule)**: defaultCapture, distantCapture, strategicCapture
**Fallback (rc82 redirect)**: alleyCapture, blox, crowded, fast, medium, office, tiny (0 capsules), jumboCapture (2 capsules — V2), testCapture (tiny/asymmetric)

**V0.2+ 보류:**
- Capsule chaining (jumbo: 78 scared 연장)
- Voronoi safe route table (defender position별)
- Top-3 anti-deterministic variants
- Scared ghost hunt
- Dead-end entry whitelist full

### 🚨 Known issues / TODOs

- **your_baseline{1,2,3}.py + your_best.py 아직 DummyAgent** — 제출 전 필수 populate
- **Server A4 unarchived** — 다음 세션 cleanup
- rc-tempo가 rc82 < 이면 V0.2 설계 회귀, rc166 교체 시나리오 포기 가능
- DP 2.3s on strategicCapture — 다른 precompute 포함 시 15s 예산 여유 체크 필요

### 📂 Critical reference docs

- **`.omc/plans/rc-tempo-design.md`** — V0.1 전체 설계 (READ FIRST)
- `experiments/test_orienteering.py` — DP timing 실측 스크립트
- `minicontest/zoo_reflex_rc82.py` — fallback delegate용 (아직 수정 X, 참조만)
- `experiments/flatten_multi.py` — submission flatten 도구
- `.omc/wiki/2026-04-20-pm28-rc-tempo-design.md` — pm28 session log (예정)

### Next action order (pm29 opening)

1. Read `.omc/plans/rc-tempo-design.md` (전체 설계)
2. `ssh jdl_wsl` A4 archive (5분)
3. Task #1 (파일 스켈레톤) 착수
4. 순차 구현 + 10g smoke test between stages
5. 100g HTH 측정 → rc82/rc166 비교

---

## pm27 TL;DR (이전 세션 — NEW PEAK rc166/rc177 = 98.5% 200g + 11 Tier 2/3 paradigms + M7 flatten working)
- 🏆 **rc166** (`if score ≥ 3: rc82 else rc16`) & **rc177** (`≥ 2 threshold`) both **98.5% 200g** [0.957, 0.995].
- **rc166 > rc177 H2H 100-0-0** (strictly better despite identical baseline WR) → **rc166 = primary submission candidate**.
- **rc82 > rc166 H2H 29-0-31** (pm26 finding confirmed, **rc82 = tournament candidate**).
- **11 new Tier 2/3 paradigms** implemented: rc25/37/38/41/47/49 (Tier 2) + rc58/59/60/65/75 (Tier 3).
- **rc47 Engine αβ** strong non-composite: 95% 200g [0.910, 0.974].
- **M7 flatten_agent DONE**: `experiments/flatten_multi.py` recursive dep resolver, verified rc166 → 2205-line standalone `20200492.py`-style file, parity 98%/100g.

## pm28 TL;DR (historical — pm28에서 진행한 priorities였음, 대부분 rc-tempo 설계로 대체됨)

### 🎯 pm28 immediate priorities (old — mostly superseded)

1. **Phase 4 round-robin tournament** (server). Pool expanded to ~40+ agents with pm27 additions. 5 layouts × 3 seeds × 2 colors. Dispatch: `ssh jdl_wsl` + `tmux work`. Expected tiering: rc82 > rc166 > rc47 > rc25 > mid-tier (rc37/41/49/59/60/75) > lower-tier (rc38/58/65).
2. **Submission decision**:
   - **Safe/baseline 40pt**: rc166 (98.5% 200g [0.957, 0.995]) via `experiments/flatten_multi.py --agent zoo_reflex_rc166 --weights experiments/artifacts/phase2_A1_17dim_final_weights.py --out minicontest/20200492.py`
   - **Tournament 30pt**: rc82 (H2H dominant) OR let Phase 4 decide
3. **Check Server Order 4 status** (pm26 SSH timeout). Retry `ssh jdl_wsl "pgrep -af evolve.py | wc -l && ls experiments/artifacts/2?_gen*.json | tail -5"`. If finished → add to Phase 4 pool.
4. **M8/M9/M10**: `your_baseline1/2/3.py` population, ICML report (Intro/Methods/Results/Conclusion), ZIP packaging.

### 📊 200g authoritative leaderboard

| rc | 200g WR | Wilson 95% |
|---|---|---|
| **rc166** (≥3 thresh) | **98.5%** | [0.957, 0.995] |
| **rc177** (≥2 thresh) | **98.5%** | [0.957, 0.995] |
| rc159 (4-way) | 98.0% | [0.950, 0.992] |
| rc160 (≥1 thresh) | 97.5% | [0.944, 0.990] |
| rc82 (composite) | 97.0% | [0.935, 0.986] |
| rc47 (engine αβ) | 95.0% | [0.910, 0.974] |

### 🧪 pm27 Tier 2/3 catalog (11 new)

**Tier 2** (search + inference heuristics):
- `rc25` Quiescence Search (αβ d4 + q-ext +2) — 98% 100g
- `rc37` Novelty Search (position anti-loop) — 94% 100g
- `rc38` MAP-Elites inference (12-niche archive) — 87% 100g
- `rc41` SARSA 4-step self-only rollout — 93% 100g
- `rc47` Engine αβ (IDDFS + history + PVS-lite) — **95% 200g**
- `rc49` SIPP-lite (3-step teammate reservation) — 95% 100g

**Tier 3**:
- `rc58` Coord-Graph UCT (pairwise spreading) — 87% 100g
- `rc59` Reward Machines (5-stage FSM) — 90% 100g
- `rc60` Difference Rewards (aristocrat utility) — 90% 100g
- `rc65` ToM L2 (2-ply adversarial over rc82) — 74% 100g (weak)
- `rc75` MAML/Reptile (layout-family adjust) — 90% 100g

**Drops**: rc26 (too slow), rc35/rc36 (rollout opp-model bug), rc42/rc43 (Double-Q/TD variants failed), rc67 (stochastic RM+ broken), rc185 (switch continuity break).

### 🔧 M7 flatten_agent (working)

```bash
.venv/bin/python experiments/flatten_multi.py \
  --agent zoo_reflex_rc166 \
  --weights experiments/artifacts/phase2_A1_17dim_final_weights.py \
  --out minicontest/20200492.py
```
Recursively resolves dep chain (rc166 → rc82 → rc44 → {A1, rc02, rc16, rc32}), strips zoo_* imports (keeps nested stdlib like `import importlib.util`), injects evolved SEED_WEIGHTS. Output ~2200 lines. Verified parity via 100g HTH: flat 98/100 vs original 98.5%/200g.

### 🔑 Critical insights (pm26+pm27)

1. **Baseline WR ≠ tournament strength**. rc166 has higher baseline (98.5%) but loses H2H to rc82 (0-29-31). Switch composites exploit baseline's weaknesses; don't generalize.
2. **H2H deadlock among strong agents**. rc47 vs rc166 = all 60 Tie (search + reflex composite neutralize each other).
3. **Threshold sweep sweet spot**: rc177 (≥2) = rc166 (≥3) at 98.5% 200g. Below (rc160 ≥1) or above (rc178 ≥4) both lose ~1pp.
4. **Search paradigm works when fixed bugs**: rc47 needs `static_eval` (max over self's legal at any state), not stale `leaf_eval(state, last_action)`. Also MUST use A1 evolved weights not seed.
5. **Rollout opp-model bug**: if opponent uses MY `evaluate(self, …)` (biased to self's perspective) → catastrophic. rc35/rc36 failed here. rc41's self-only rollout fixed it (93% WR).

### 📂 Reference docs

- `.omc/wiki/2026-04-20-pm27-tier2-3-expansion-11-paradigms-m7-flatten.md` — full session log
- `.omc/plans/pm27-batch-ii-tier23.md` — Tier 2/3 plan (partially executed)
- `.omc/plans/rc-pool.md` — full catalog (needs pm27 update)
- `experiments/flatten_multi.py` — multi-file flatten
- Recent commits: should see pm27 commit as latest

### 🚨 Known issues / TODOs

- Server Order 4 status unknown since pm26 (SSH timeout 2026-04-19 evening).
- pm27 drops kept in `minicontest/` for audit trail (rc26/35/36/42/43/67); can delete later if clutter.
- `your_baseline{1,2,3}.py` still DummyAgent — populate before M8 output.csv.

### Next action order

1. Read `STATUS.md` (detailed table).
2. `ssh jdl_wsl "pgrep -af evolve.py | wc -l"` — Order 4 alive?
3. If Order 4 done: add O4 to Phase 4 pool and launch tournament.
4. If not reachable: launch Phase 4 with current pool (~40 agents including pm27 additions).
5. Post-tournament: M7 flatten final champion to `20200492.py`, run 100g HTH sanity, update AI_USAGE.md.

## pm27 TL;DR (historical — this session just completed)

### 🎯 pm27 immediate priorities

1. **Phase 4 round-robin tournament** (server). Pool: rc160 + rc82 + rc105 + rc131 + rc16 + rc152 + A1 + top pm24 champions (~15-25 agents). 5 layouts × 3 seeds × 2 colors. Expected: rc82 > rc160 > rc16 > rc52b tier ordering based on pm26 H2H evidence. Dispatch: `ssh jdl_wsl` + `tmux work`.
2. **Submission selection decision**:
   - **rc160** if code 40pt (baseline) is priority — 97.5% is safest.
   - **rc82** if extra 30pt (tournament) is priority — dominates in H2H.
   - Recommend: run phase 4 first, then decide based on data.
3. **M7 flatten_agent** (Mac coding, ~2h). `experiments/select_top4.py:140` has NotImplementedError stub. Must implement AST-based flattening to produce `20200492.py` from chosen rc (rc160 or rc82). Both are composition-based so flattening needs `zoo_reflex_rc82.py` + `zoo_reflex_rc16.py` + `zoo_core.py` + `zoo_features.py` inlined.
4. **Server Order 4 check** (SSH was timing out pm26). Retry `ssh jdl_wsl "pgrep -af evolve.py | wc -l && ls experiments/artifacts/2?_gen*.json | tail -5"`. If finished, HTH battery vs baseline + add to Phase 4 pool.

### 🧪 pm26 key findings (pattern laws)

1. **Asymmetric direction matters**: "rc82-leading + rc16-else" (rc160) = 99%. Reverse (rc164) = 97%.
2. **Tied score MUST use rc16**: rc163 (rc82 at 0) = 96%, rc162 (rc82 always ex tied) = 93%.
3. **Threshold 1-3 is flat**: rc160 (≥1) = rc166 (≥3) = 99%.
4. **More switch slots don't help**: 2-way rc160 = 99% > 4-way rc152 = 98% > 5-way rc154 = 92%.
5. **Baseline WR is NOT tournament proxy** — rc160 beats baseline by switching but loses to rc82 H2H.

### 📝 pm26 full rc catalog (24 agents committed)

Switch variants (12):
- rc148-152: score-conditioned (rc82/rc52b/A1/...)
- rc153-156: variants with rc32 / hysteresis / finer bands
- rc157-160: no-A1 / 2-way
- rc161-167: champion-only combinations + threshold sweep
- rc170-174: consensus / carry-count / endgame-guard

Asymmetric (5): rc141/142/143/147 (learning OFF + composite DEF) — all 90-91%.

REINFORCE (3): rc52b (92% lucky), rc52c (86% overshot), rc52d (86% conservative-regressed).

Verification-only: rc82/rc16/rc105 100g re-tests.

### 🔧 Files ready to use

- `minicontest/zoo_reflex_rc160.py` ← **primary submission candidate** (2-way score switch)
- `minicontest/zoo_reflex_rc82.py` ← **tournament submission candidate** (rc29+rc44 composite)
- `experiments/hth_battery.py` ← for 100g authoritative HTH
- `experiments/tournament.py` ← Phase 4 round-robin (dispatch to server)

### 🚨 Known issues / TODOs

- M7 flatten_agent raises `NotImplementedError` — must fix before M8/M10.
- Server Order 4 status unknown (SSH timeout 2026-04-19 evening).
- pm23/24 "100% champion" labels need global update — they're 90-97% at 100g, not 100%.

### 📂 Reference docs

- `.omc/wiki/2026-04-19-pm26-end-switch-based-rc160-breakthrough-97-5-200g.md` — full pm26 session log
- `.omc/plans/rc-pool.md` — 160+ rc catalog with pm26 entries
- `experiments/hth_battery.py --help` — HTH protocol
- Recent commits: `git log --oneline -10` → 6 pm26 commits (rc sprint → rc152 → rc160 → final)

---

## pm25 TL;DR (historical — pm26 superseded this)

### pm25 주요 성과

- rc22 distillation (numpy MLP, rc82 teacher) → 88% vs baseline Wilson [0.80, 0.93]
- rc22-v2 39-dim extended features → 85% (val_acc 91→94% but game-WR plateau)
- rc52 REINFORCE (linear Q gradient, A1 init, T=5) → 90% [0.83, 0.95] (honest post-debug)
- rc140 (rc52 OFF + rc82 DEF asym) → 91%
- A1 authoritative Mac 100g = 86% [0.78, 0.92] (corrected from server 79%)
- Server Order 4 Phase 2a gen 3/10 best=0.712 ETA ~20-24h.

## pm26 TL;DR (historical — superseded by pm26 END section at top)

### pm25 주요 성과

- **rc22 shipped**: numpy MLP policy distillation pipeline working end-to-end.
  - `experiments/distill_rc22.py` (orchestrator, collect/train/both subcommands)
  - `minicontest/zoo_distill_collector.py` (teacher logger wrapper on rc82)
  - `minicontest/zoo_distill_rc22.py` (student inference, 2K params, numpy-only)
  - 100-game HTH: **88%** — beats A1 (82.5%), first ARCHITECTURALLY DIFFERENT pool member.

### 중요 lessons (pm25)

1. **40-game HTH too noisy for learning agents** — use ≥100 games for Tier 3 authoritative numbers. pm25 saw 65% / 82.5% variance on same weights at 40 games, stabilized to 88% at 100 games.
2. **Info-bottleneck**: val_acc plateau at ~91% regardless of data size. Adding more games (20 → 100) didn't help val_acc. Feature extension needed for further lift.
3. **Default path absolute, env var paths can bite** — `RC22_WEIGHTS` with relative path failed silently because `single_game.py` cwd=minicontest/. Always absolute.
4. **CPU-only sufficient** for 2K-param MLP; GPU not needed. Data collection (Pacman simulation) dominates wall time (~95%).

### pm26 우선순위

**A. 서버 Order 4 완료 모니터링** (ETA ~2026-04-20 evening if gen wall ~60min ×  ~25 gens remaining)
  - Gen 0-3 trajectory: 0.555 → 0.539 → 0.597 → **0.712** (CEM learning confirmed, +29% over gen 0)
  - Expected final: fitness close to A1's 1.065 or exceed
  - Next: HTH battery vs baseline, update champion if beats A1's 79%

**B. 다음 Tier 3 rc 후보 (우선순위 선택 필요):**
  - **rc46 Opponent-type classifier** (1-2d, novel) — K-means on opponent's first 50 moves → counter-policy switch. Strategic value: adapts to tournament opponents.
  - **rc52 Q-learning v3** (2d, real RL) — replay buffer + SGD on linear Q. zoo_approxq revival. Expected WR ~60-70%.
  - **rc61 AlphaZero-lite** (5d, highest ceiling) — MCTS + policy/value net + self-play. Research-grade.
  - **rc22-v2 feature extension** (stretch) — add 15-dim history + AP flag + phase bucket → 34-dim student. Expected WR 88% → 92%+.

**C. Phase 4 + M7 prep (parallel track):**
  - Lock 8 pm24 100% champions (rc02/16/82/105/109/116/123/131) + rc22 + O4 (pending) + A1 = ~11 candidates for top tier.
  - Pool size ~75 total (pm24 + pm23 + HOF + D/T + rc22).
  - Tournament infra: `experiments/tournament.py` already ready. Dispatch to server when Order 4 done.

**추천 순서**: pm26 동안 **Mac**에서 (1) rc46 Opponent classifier 시작 (2d) + (2) Phase 4 prep + M7 flatten 스켈레톤. **서버**는 Order 4 계속. Order 4 완료 시 pm27에서 Phase 4 런칭.

**참고 문서**:
- `.omc/wiki/2026-04-19-pm25-rc22-policy-distillation-first-tier-3-pass.md` — 상세 기록
- `.omc/plans/rc-pool.md` 끝부분 — pm25 log + rc22 status row
- `experiments/artifacts/rc22/` — weights + data + hth CSV

## pm25 TL;DR (historical — deeper pm25 context)

### ⚠️ pm24가 놓친 것 (IMPORTANT)

**pm24는 Tier 1-2 hand-rule/composite만 68개 구현했고, Tier 3 학습 기반 rc는 전혀 안 함.**

안 한 큰 항목 (각 1~5일 소요):
- **rc22** Policy Distillation (teacher → student MLP, numpy inference)
- **rc23** Coevolutionary CEM
- **rc51** C4 ExIt (MCTS+NN)
- **rc52** Q-learning v3 real training (replay buffer + SGD)
- **rc53** CMA-ES with restarts
- **rc54** NEAT
- **rc55-60** IS-MCTS / POMCP / Factored MCTS 등
- **rc61** **AlphaZero-lite (5일, 가장 복잡)**
- **rc62-64** Distributional RL / SAC / MAPPO
- **rc70** MuZero-lite (5일, 연구급)
- **rc71-75** 최신 논문 (TAR², DrS, ARES, DIRECT, MAML)
- **rc76-80** Pruning / Ensemble Distillation / Gating

제출은 numpy+pandas only이므로 학습은 server GPU (RTX 4090)에서, 추론 weights는 numpy로 export 필요.

### pm24 주요 성과 (사실)

- **68 new rc** (17 batches A-Q), **66 pass**, 2 drop
- **8 champions at 100%**: rc02, rc16, rc82, rc105, rc109, rc116, rc123, rc131
- Pattern 발견: rc16/rc32 OFF + rc82 DEF = sweet spot
- 모두 **hand-rule + composite/overlay** — 학습 없음

### pm25 우선순위

**병렬 전략 (추천)**:
1. **서버 Order 4 완료 대기** (ETA 2026-04-20 ~17:00 KST if gen 2/30 wall ~60min/gen)
2. **Mac: Tier 3 rc 시작** — 아래 순서
   a. **rc22 Policy Distillation** (제일 쉬운 진입): rc82 data collection → numpy MLP 학습 → rc22 inference agent
   b. **rc52 Q-learning v3** (1~2일): replay buffer + SGD, zoo_approxq 살리기
   c. **rc61 AlphaZero-lite** (5일, stretch): MCTS + policy/value net + self-play
3. **서버 Order 4 끝나면**: HTH battery → O4 champion 결정 → Phase 4 tournament 런칭 (~75 agents, 서버 6분)
4. **Phase 4 결과로 M7 flatten** 챔피언 확정 (후보: rc82/105/109/116/123/131 + Tier 3 결과)
5. **M8-M10** output.csv + ICML report + zip

**서버 상태 (pm24 종료 시점)**: Order 4 running, 18 evolve processes, gen 2/30 wall ~60min, ETA ~30h

**pm25 첫 액션**:
```bash
# Step 1: Server Order 4 상태
ssh -o ConnectTimeout=10 jdl_wsl "cd ~/projects/coding-3 && pgrep -af evolve.py | wc -l && tail -15 logs/phase2_A4*.log"
# Step 2: pm24 모든 rc 학습 요약 확인
cat .omc/STATUS.md | head -60
# Step 3: rc-pool.md 변경 로그에서 pm24 section
# Step 4: Tier 3 중 rc22부터 시작 (data collection 단계)
```

**참고 문서**:
- `.omc/wiki/2026-04-19-pm24-mega-sprint-68-rc-8-champions.md` — 68 rc 상세 기록
- `.omc/plans/rc-pool.md` — 전체 80 rc 카탈로그 + 17 batch 변경 로그
- `.omc/STATUS.md` — pm24 FINAL headline + champion tier
- `experiments/phase4_agents.txt` (미커밋) — top-14 agent list
- `experiments/phase4_launch.sh` (미커밋) — tournament 런칭 스크립트

## pm23-24 TL;DR (historical)

- **pm22**: Round-robin 후보 80개 수집 (Codex 18 + Gemini 17 + 기존 50 + user 아이디어). `rc-pool.md` 생성.
- **pm23**: 17 rc implemented in one session (rc02-rc08, rc09/11/15/16/17/19, rc27/32/33/45/46). rc02 + rc16 공동 1위 (100%), rc32 97.5%. rc18 dropped (FAIL).
- **pm24**: 8 more rc (rc28/29/30/31/34/44/48/50). 6 pass, 2 drop. Batch B learned: random top-K injection catastrophic; deterministic top-K safe.

## pm22 TL;DR (historical)

- Autopilot cron으로 Order 3 자동 실행 (Phase 2a 완료, Phase 2b gen 6/20 진행 중)
- 후보군 총 정리 세션 (코드 구현 X)
- CCG advisor (Codex + Gemini) 사용해 추가 후보 35개 수집
- `rc##` naming 도입 (pm은 세션 타임라인, rc는 작업 항목)
- 문서 신규 2개: `rc-pool.md`, `pm23-handoff.md`

## pm20 TL;DR (historical)

3-axis parallel development (CEM evolution + rule-based hybrids + paradigm hybrids) with 17 tasks tracked; CCG added particle filter + opponent classifier + endgame lockout + capsule proxy camping + stochasticity; robustness-first over peak (180-agent tournament); **never discard ≥50% baseline candidates** (all go to Phase 4 round-robin).

This is the **first thing to read** when resuming work on this project. STATUS.md and STRATEGY.md have more detail; this file makes you productive in 5 minutes.

## Step 1 — Read this 30-second TL;DR

**CS470 Coding Assignment #3**: Pacman Capture-the-Flag tournament agent (KAIST, UC Berkeley CS188 framework). Student ID `20200492`. 21 agents implemented (18 zoo incl. 3 H1-family + 3 monsters). 40-game apples-to-apples reverification (pm4) produced the canonical comparison vs `baseline.py` on `defaultCapture`:

| Agent | W / L / T | Win% | Net (W−L) |
|---|---|---|---|
| zoo_reflex_tuned (control) | 0 / 0 / 40 | 0% (100% tie) | 0 |
| zoo_reflex_h1test (both-OFFENSE) | 14 / 14 / 12 | **35%** | 0 |
| zoo_reflex_h1b (role-split, RESURRECTED) | 12 / 4 / 24 | 30% | **+8** |
| zoo_reflex_h1c (capsule-exploit, new) | 8 / 2 / 30 | 20% | +6 |

Key reversals: **pm2's H1b rejection was wrong** — H1b has the best net score (+8) and lowest loss rate (10%). **H1 leads on raw win% (grading metric) at 35%**, but 14/40 vs p=0.51 rejects the 51% threshold at 95% (z=-2.07). **Single-dict tuning is statistically saturated**; M6 CEM evolution is now the only viable path to the 40pt code score. ReflexTuned 100% tie confirms the original deadlock is structural.

## Step 2 — Run these commands (~30 sec)

```bash
cd "/Users/jaehyeon/KAIST/26 Spring/인공지능개론/coding 3"
git log --oneline -5         # what was committed recently
ls minicontest/zoo_*.py minicontest/monster_*.py | wc -l   # 21 expected (18 zoo + 3 monsters)
```

## Step 3 — Read these in order (~3 min)

1. **`.omc/STATUS.md`** — canonical 40-game table + all open blockers (1 min)
2. Wiki `session-log/2026-04-15-pm4-40-game-apples-to-apples-reverification-h1b-redem` — what pm4 concluded (1 min) — read with `wiki_read`
3. Wiki `debugging/experiments-infrastructure-audit-pre-m4-m6` — the two 🔴 blockers that M4 must fix (1 min) — read with `wiki_read`

## Step 4 — Know what to do next

**Current state (2026-04-16 pm18 end)**: Phase 1 complete and committed. A1 17-dim (Order 1) launched and running on server with real learning signal.

**What's done since pm17**:
- ✅ Phase 1 B1 (20-dim features, commit `379dc74`) — f_scaredGhostChase, f_returnUrgency, f_teammateSpread. seed_weights = 0.0 (evolution discovers magnitudes).
- ✅ Phase 1 C4 (commit `a1b5569`) — MCTS time-budget polling 0.8s/move in zoo_mcts_{heuristic,random,q_guided}.py. Submission-safe under capture.py's 1s warning.
- ✅ A1 17-dim Order 1 launched on server 06:37 with 11-opp no-MCTS pool + `--master-seed 42 --workers 16 --init-mean-from h1test --phase both`.

**A1 in flight, first 3 gens**:
| gen | best | mean | snr | wall |
|---|---|---|---|---|
| 0 | 0.112 | 0.007 | 0.61 | 2796.8s |
| 1 | 0.181 | 0.026 | 0.91 | 2895.4s |
| 2 | 0.483 | 0.099 | 1.10 | 2926.9s |

CEM learning confirmed (best 4.3× over 3 gens, snr cleared 1.0 at gen 2). Wall stable ~47-48 min/gen → ETA finish ~00:40 next day. Per-gen wall is ~2× the wiki estimate, so total ~18-19h vs planned 10h — still within overnight budget.

**Server commits needed**: `git pull origin main` to get `379dc74` + `a1b5569` (pm18 B1+C4). Mac already has them. A1 does NOT need these (it's running 17-dim reflex, not 20-dim or MCTS).

## ⚠️ Next-session immediate actions

Read in order:
1. THIS file
2. `.omc/STATUS.md` (milestone table — look for "A1 HTH validation (pm19)" and "CCG plan review (pm19)")
3. wiki `session-log/2026-04-17-pm19-a1-validated-order-2-launched-performance-max-pivot` (pm19 record — CCG advisor outputs archived there)
4. (optional) wiki `decision/next-session-execution-plan-performance-max-6-phase-pipeline` — superseded by pm19 scope tweaks; keep only Orders 2-4 queue, drop Orders 5-7 per CCG consensus unless buffer remains

**FIRST: verify Order 2 state** (launched 2026-04-17 11:55, ~18h expected):
```bash
ssh jdl_wsl "tmux capture-pane -t work -p -S -40 | tail -25 && echo --- && pgrep -af evolve.py | wc -l && echo --- && ls experiments/artifacts/2[ab]_gen*.json 2>/dev/null | head -30 && echo --- && tail -25 logs/phase2_A1_B1_20dim_*.log"
```

Three outcomes and actions:
- **RUNNING**: `pgrep` shows ≥17 processes. Wait or work on Phase 3 D-series coding on Mac in parallel.
- **FINISHED**: `pgrep` shows 0, artifacts has 2a_gen000-009 + 2b_gen000-019 + `final_weights.py`. → Archive to `experiments/artifacts/phase2_A1_B1_20dim/`, run HTH battery vs baseline+monster via `experiments/hth_battery.py`, compare to A1's 79% baseline WR. If Order 2 > A1: update champion. Then launch Order 3 (A2+B1 h1b init).
- **CRASHED**: check log for Traceback. Fix, re-archive any partial artifacts, decide restart vs skip.

**Phase 2 queue status (pm19 revised — Orders 5/7 dropped per CCG low-ROI)**:
- A1 (17-dim h1test) ✅ fitness 1.065, baseline 79% PASS
- Order 2 (A1+B1 20-dim h1test init) ▶️ running
- Order 3 (A2+B1 h1b init) — queued after Order 2
- Order 4 (A5+B1 (h1test⊕h1b)/2 hybrid init) — queued after Order 3
- Orders 5/7 (minimax / expectimax containers) — DROPPED (low ROI per Codex + Gemini consensus)
- Order 6 (MCTS container) — DROPPED (MCTS wall >> 120s timeout + machine-dependent time polling)
- Order 8 (h1c init) — stretch IF Orders 2-4 all underwhelm

**Phase 3 D-series coding plan** (Mac, ~10-12h, parallel to server Orders 2-4):
- D1 role-swap: dynamic OFFENSE↔DEFENSE swap on (carrying ≥ threshold → return) + (invaders ≥ 2 → both defensive)
- D2 capsule timing: eat capsule only when (a) ghost_dist ≤ 3 AND carrying ≥ 5, OR (b) opponents ate our capsule
- D3 endgame mode: last 100 moves, leading → defend; behind → all-in rush ignoring ghost penalty
- Dead-end-guard: hardcoded override when in dead-end with ghost ≤ 3 (overrides reflex evaluator)
- Deliverable: 4 variants per champion (bare / +D1 / +D2 / +D1+D2+D3)

## ⚡ pm20 KEY DECISIONS (must resolve before heavy compute)

### Decision 1 — Orders 2-4 are BIT-IDENTICAL as currently configured (pm19 late discovery)

pm17 plan's Orders 3 (h1b init), 4 (hybrid init) would produce IDENTICAL results to Order 2 because:
- `_H1B_FEAT_SEED = list(_H1TEST_FEAT_SEED)` in evolve.py — same vector
- `--master-seed 42` fixed across all → identical Gaussian sampling
- Same 11-opp pool
- Order 4 "hybrid" option NOT implemented in `--init-mean-from` CLI

**Fix options** for real diversification in Orders 3/4:
- (a) Different `--master-seed` per Order (e.g., 1001, 2026) — trivial
- (b) Expand `KNOWN_SEEDS_PHASE_2A` + `--init-mean-from` with `"a1"` option (seed from A1 final_weights)
- (c) HOF pool rotation — create `zoo_reflex_A1.py` wrapper, add to Order 3+ pool so evolution must beat A1 (AlphaZero-lite)

Combo (a+c) recommended: different seeds + HOF pool → genuine champion diversity for Phase 4 ELO meaningfulness.

### Decision 2 — Hybrid paradigm (Path 3) trial?

CCG analysis (wiki `decision/pm19-ccg-hybrid-paradigm-analysis-path-1-vs-2-vs-3-mcts-offen`):
- **Codex**: Path 3 tightly-scoped with hard kill. 1-2 days engineering + 18h CEM.
- **Gemini**: Stick with Path 1, polish report. Overengineering risk.
- **Claude synthesis**: given user's performance-max + 10-day budget, lean Codex. Prep: M7 flatten A1 first to LOCK submission candidate, then attempt Path 3 with clear abort criteria.

**pm20 action**: after Order 2 HTH, decide: (A) Path 3 trial, (B) A1-only polish, (C) other.

**Phase 4 tournament** (post Orders 2-4): round-robin ELO, ~1-2h server wall.

**Phase 5 multi-seed** (server + Mac): top-3 × 200 games × 10 seeds × 4 layouts. ~1h server + 1-2h Mac cross-platform check.

**Phase 6 submission** (Mac, ~15-20h report + misc):
- M7 flatten_agent AST implementation (skeleton at `experiments/select_top4.py`)
- M8 output.csv (auto via capture.py 4-loop)
- M9 ICML 2+ page report with 4+ ablation figures
- M10 package zip with sha256

## What we're doing (pm17 user decision)

**User has time slack, wants performance-max (code 40pt + tournament extra 30pt). Full 6-phase pipeline.** Fixed `--master-seed=42` for all Phase 2 candidates (apples-to-apples ranking) → Phase 5 multi-seed on top-5 (cross-platform robustness).

Critical path with parallelism:
- **First slot (~10h calendar)**: launch A1 17-dim baseline candidate on server (overnight, control champion) WHILE coding Phase 1 B1+C4 on Mac in parallel.
- **Subsequent slots**: queue server with B1-extended candidates (Order 2-7), Mac handles Phase 3 hybrid coding + Phase 5 validation + Phase 6 flatten/report.

Total budget ~5-7 days, mostly server overnight.

**Dispatch is case-by-case** — NOT "always server". See wiki page for the venue decision matrix.

**FIRST decision in next session**: confirm pm17 6-phase plan still wanted. If yes, launch the parallel first slot (server A1 17-dim + Mac Phase 1 coding). `evolve.py --phase 2a --n-gens-2a 2 --pop 8 --games-per-opponent-2a 24` with the canonical 3-opponent dry-run pool. Check fitness trend, elite selection, gen JSON emit, resume after one mid-gen kill.

**Then M6 — split into 4 resumable tiers** (do NOT treat as a single 23h block). Each tier is independent via `evolve.py --resume-from`; user judges at each gate whether to continue or pivot:

- **M6-a** (~1.5h parallel): Phase 2a smoke, 2 gens × 40 pop. Go/No-go signal = best_ever fitness exceeds h1test seed baseline. If no: diagnose (seed weights wrong? opponent pool too easy? restart with broader σ).
- **M6-b** (~4h parallel): Phase 2a full (gens 3-10), resuming from M6-a's gen 1. Emits `2a_gen009.json` containing the Phase 2b initial mean.
- **M6-c** (~2.75h parallel): Phase 2b early (gens 11-15). Split W + monster_rule_expert in pool. First look at whether split-W gains over shared-W.
- **M6-d** (~8.25h parallel): Phase 2b late (gens 16-30) + final_weights.py emission. Overnight / weekend block.

Launch each tier via `tmux new -d -s m6 'caffeinate -i .venv/bin/python experiments/evolve.py --phase 2a --n-gens-2a N --resume-from ...'`. Watchdog via Monitor tool on `artifacts/{phase}_gen*.json` stall.

**Then M7** (`flatten_agent` AST + select_top4 + family-floor). **M8** (output.csv: populate `your_baseline{1,2,3}.py` first). **M9 — split**:
- **M9-a** (~1.5h): Intro (8pt) + Methods (20pt)
- **M9-b** (~1.5h): Results (20pt) + ablation figures
- **M9-c** (~1h): Conclusion (12pt) + revise

**M10** (~15min): submission packaging.

## Tier policy (project convention)

Every milestone that needs more than ~1h of uninterrupted compute/work is split into resumable sub-tiers with Go/No-go gates. User decides after each gate. No single step commits more than ~4h.

Context for every follow-up session: start by reading this file (top-to-bottom), then `.omc/STATUS.md`, then the wiki pages referenced in the Option α step above.

## Project rules — must respect

(Already in `CLAUDE.md` which is auto-loaded; restated here for new humans):

1. **Never use global Python.** Always `.venv/bin/python` or `uv run --python .venv/bin/python`.
2. **Only numpy + pandas** — no torch, sklearn, tensorflow, pickle, requests.
3. **No multithreading in submission agent.** Training pipeline can use `multiprocessing.Pool`.
4. **Never modify framework files**: `baseline.py`, `capture.py`, `captureAgents.py`, `game.py`, `layout.py`, `util.py`, `distanceCalculator.py`, `keyboardAgents.py`, `mazeGenerator.py`, `textDisplay.py`, `graphicsDisplay.py`, `captureGraphicsDisplay.py`, `graphicsUtils.py`.
5. **Editable**: only `your_best.py`, `your_baseline1.py`, `your_baseline2.py`, `your_baseline3.py`, `myTeam.py`, plus our `zoo_*.py` and `monster_*.py` development files.
6. **Submission ZIP contains exactly one `.py`**: `20200492.py` (renamed from `your_best.py`). The `your_baseline*.py` files are NOT in the ZIP — they're for `output.csv` generation only.
7. **AI usage logging**: every edit to a submission-target file must append an entry to `docs/AI_USAGE.md` (assignment regulation).
8. **Session-log discipline**: at the end of any > 30-min work session or after a milestone, append a `session-log` wiki entry per `wiki/convention/session-log-protocol-...`.

## Where to find more (no need to read upfront)

| For information about... | Location |
|---|---|
| Full plan (all 11 sections) | `.omc/plans/STRATEGY.md` |
| Open / stretch questions | `.omc/plans/open-questions.md` |
| Detailed milestone status | `.omc/STATUS.md` |
| All decisions / observations / patterns / debugging notes | `.omc/wiki/` (use `wiki_query`) |
| Per-milestone code change log | `docs/AI_USAGE.md` |
| Project-specific terms | wiki `reference/glossary-cs470-a3-project-terms` |
| Working memory (7-day prune) | `.omc/notepad.md` |
| Persistent user context | `~/.claude/projects/.../memory/MEMORY.md` |

## When stuck

- Search prior sessions: `session_search --query "<topic>"` (also includes prior sessions on this project)
- Search wiki: `wiki_query --query "<topic>"`
- Read STRATEGY.md ADR section: `.omc/plans/STRATEGY.md` §0
- Ask user (don't barrel forward on ambiguous decisions)

## When done with this session

1. Summarize what you did + observations + decisions + next actions to `wiki_ingest` with `category=session-log`, `title="YYYY-MM-DD - <topic>"`
2. Update `.omc/STATUS.md` if any milestone state changed
3. Commit any code changes (per user request — don't auto-commit unless instructed)
4. Append to `docs/AI_USAGE.md` if submission-target code was modified
