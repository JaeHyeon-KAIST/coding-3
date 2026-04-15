---
title: "Remote compute infra — WSL2 Ryzen 7950X server (jdl_wsl)"
tags: ["environment", "remote-server", "ssh", "wsl2", "tmux", "ryzen-7950x", "dispatch-policy"]
created: 2026-04-15T21:04:52.125Z
updated: 2026-04-15T21:04:52.125Z
sources: ["pm17 user-provided infra spec", "ssh jdl_wsl status check 2026-04-16"]
links: []
category: environment
confidence: high
schemaVersion: 1
---

# Remote compute infra — WSL2 Ryzen 7950X server (jdl_wsl)

# Remote compute infra — WSL2 Ryzen 7950X server (jdl_wsl)

**Available since 2026-04-16 pm17.** Use for heavy evolve / tournament batches; Mac for interactive dev / analysis / report.

## Specs (verified live 2026-04-16)
- **Host**: `DESKTOP-E1VA18K`, WSL2 Ubuntu 22.04, kernel `6.6.87.2-microsoft-standard-WSL2`
- **CPU**: AMD Ryzen 9 7950X — **16 physical / 32 SMT threads** (Zen 4, max 4.5 GHz)
- **RAM**: 128 GB DDR5-5600 (WSL gets 48 GB dynamic)
- **GPU**: RTX 4090 — **NOT used** (project rule: numpy/pandas only)
- **IP**: `143.248.59.120` (KAIST public, fixed)
- **Project path**: `/root/projects/coding-3` = `~/projects/coding-3`
- **venv**: `.venv/` Python 3.9.25, numpy 2.0.2, pandas 2.3.3 (identical to Mac)

## SSH aliases (Mac side, configured in `~/.ssh/config`)
- **`ssh jdl_wsl`** — WSL Ubuntu, port 2222, user `root`. Use for ALL project work. Lands directly in Linux bash.
- **`ssh jdl`** — Windows host, port 22, user `user`. Only for `wsl --shutdown` / `netsh portproxy` / PowerShell meta.
- **Port 2222 only**. 9876 is unreachable for unknown reasons; never use it.

Keys: `id_ed25519` registered both sides + macOS Keychain stores passphrase. Mac reboot → no prompt.

## tmux session `work` — survives Mac disconnect
Persistent on server; Mac SSH dropouts don't kill running jobs.

```bash
ssh jdl_wsl "tmux list-sessions"                 # check exists
# Re-create if missing:
ssh jdl_wsl "tmux new-session -d -s work && tmux send-keys -t work 'cd ~/projects/coding-3 && source .venv/bin/activate' Enter"
```

Persistence guarantees:
- `.wslconfig`: `[general] instanceIdleTimeout=-1` + `[wsl2] vmIdleTimeout=-1` → no WSL auto-shutdown (defends against MS Issue #13291's 15s SIGTERM in WSL 2.5.7+).
- `/etc/wsl.conf`: `systemd=true` → sshd auto-starts on boot.
- Windows sleep OFF (display-off only after 1h, no compute impact).

## Performance benchmarks (measured 2026-04-16)
| metric | server | Mac M3 Pro | speedup |
|---|---|---|---|
| Single match (run_match.py) | **1.3 s** | 2.7 s | 2.1× |
| evolve pop=16, gen wall | **8.8 s** | 19.8 s (workers=8) | 2.25× |

⚠️ **Use `--workers 16` to saturate 16 physical cores.** With `pop < 8` the server advantage shrinks because workers idle.

⚠️ **Cross-platform fitness reproducibility is imperfect.** Same `--master-seed` can yield meaningfully different best/mean fitness across Mac vs server (occasionally Mac best=0.5, server best=0.0). Compare quantitatively only WITHIN a single platform.

## Dispatch policy (project convention)

| task | venue | reason |
|---|---|---|
| Quick smoke (pop≤4, 1 gen) | Mac | iteration speed, context inline |
| Mid-tuning (pop 8-16, 2-5 gen) | Either | Mac if convenient |
| **Heavy evolve (pop≥16, 20+ gens)** | **Server (tmux)** | 2.25× + survives ssh dropout |
| Large tournament (100s of matches) | Server | 32-thread pool |
| Result analysis / report | Mac | inline Claude context |

## Two execution patterns

### (A) One-shot (short queries / runs)
```bash
ssh jdl_wsl "cd ~/projects/coding-3 && git log --oneline -5"
ssh jdl_wsl "cd ~/projects/coding-3 && .venv/bin/python experiments/run_match.py --red baseline --blue baseline --seed 1"
ssh jdl_wsl "cat ~/projects/coding-3/experiments/results/latest.json"
```
- stdout flows back to Mac Claude context for analysis.
- Dies if SSH drops. Don't use for >5 min jobs.

### (B) tmux send-keys (long batches)
```bash
# Inject command (async, returns immediately)
ssh jdl_wsl "tmux send-keys -t work 'cd ~/projects/coding-3 && mkdir -p logs && .venv/bin/python experiments/evolve.py --phase both --n-gens-2a 20 --pop 16 --workers 16 2>&1 | tee logs/evo-\$(date +%F-%H%M).log' Enter"

# Snapshot (capture-pane has 2000-line buffer limit)
ssh jdl_wsl "tmux capture-pane -t work -p | tail -30"

# Long log → file (ALWAYS pipe through tee for >5 min runs)
ssh jdl_wsl "ls -la ~/projects/coding-3/logs/"
ssh jdl_wsl "tail -100 ~/projects/coding-3/logs/evo-*.log | tail -50"

# Process check
ssh jdl_wsl "pgrep -af evolve"
```

**Rule**: Long runs MUST `2>&1 | tee ~/projects/coding-3/logs/<name>.log`. capture-pane buffer truncates beyond 2000 lines.

## Result sync workflow
Server work → commit → Mac pull:
```bash
# Server side
ssh jdl_wsl "cd ~/projects/coding-3 && git checkout -b exp/server-\$(date +%Y%m%d) && git add logs/ && git commit -m 'exp: server evolve run' && git push origin HEAD"

# Mac side
git fetch
git log exp/server-* --oneline
```
`.gitignore` already excludes `experiments/artifacts/` — for run logs use `logs/` (not gitignored) or `git add -f` artifacts you want shared.

## Status check command bundle
```bash
ssh jdl_wsl "echo ok && uptime && hostname && nproc && uname -r"
ssh jdl_wsl "tmux list-sessions"
ssh jdl_wsl "tmux capture-pane -t work -p | tail -30"
ssh jdl_wsl "ls -la ~/projects/coding-3/logs/ 2>/dev/null"
ssh jdl_wsl "cd ~/projects/coding-3 && git status && git log --oneline -5"
ssh jdl_wsl "free -h && ps -eo pcpu,pmem,cmd --sort=-pcpu | head -10"
```

## Gotchas
1. **Security**: 143.248.59.120 is a public KAIST IP. Currently `PasswordAuthentication yes` + `PermitRootLogin yes` — only safe because key auth works. Once confirmed, harden with `PasswordAuthentication no` + fail2ban. **Re-verify key auth BEFORE flipping** or you lock yourself out.
2. **Port 9876 banned**, only 2222 works for external connections.
3. **Windows reboot**: WSL auto-starts but tmux `work` is gone. Re-run the create-session command above.
4. **WSL IP changes break portproxy**. Symptom: external SSH fails. Fix from PowerShell admin:
   ```powershell
   netsh interface portproxy show all
   wsl hostname -I
   netsh interface portproxy reset
   $wslIP = (wsl hostname -I).Trim().Split()[0]
   netsh interface portproxy add v4tov4 listenport=2222 listenaddress=0.0.0.0 connectport=2222 connectaddress=$wslIP
   ```
5. **Mac sleep/quit** doesn't affect server tmux. Wake → `ssh jdl_wsl "tmux capture-pane -t work -p | tail -50"` to catch up.
6. **WSL idle timeout regression**: if `.wslconfig` gets reset (someone edits / Windows update), `instanceIdleTimeout=-1` may disappear → SSH starts dying after 15s. Verify with `ssh jdl "type C:\Users\user\.wslconfig"`.
7. **Long run log MUST be `tee`'d to file**. capture-pane 2000-line buffer truncates anything bigger.

## Implications for THIS project (CS470 A3)

- **M6 full campaign budget on server**: ~10h (vs Mac ~23h post-Option A) — fits an overnight run safely.
- **M4 tournament re-runs**: ~7 min/210-match (vs Mac ~32 min). Multiple layouts × seeds becomes cheap.
- **Phase 2b 20-gen evolution**: ~6h on server. Doable within a single workday.
- **Cross-platform fitness caveat**: when promoting weights from server-evolved final_weights.py to Mac-side submission `your_best.py`, do a Mac-local 100-game baseline match to re-confirm. Don't trust server fitness as absolute.

