# LAN multiplayer manual test checklist

This document walks a human through exercising every flow that the
automated test suite cannot verify on a single machine. Run the
[`scripts/lan_2machine_check.sh`](../scripts/lan_2machine_check.sh) helper
first to confirm basic connectivity before starting the game.

## Setup

- [ ] Build the game on **both** machines (same commit, same architecture).
- [ ] Both machines on the **same LAN** (router, switch, or Wi-Fi).
- [ ] UDP port **45678** open on the host's firewall
      (`sudo ufw allow 45678/udp` on Linux; Windows Defender Firewall
      prompt should appear on first run).
- [ ] Run the helper:
  ```bash
  # On the host:
  ./scripts/lan_2machine_check.sh host
  ./scripts/lan_2machine_check.sh ping <client-ip>
  ./scripts/lan_2machine_check.sh client <host-ip>     # on the client
  ```

## Scenarios

For each scenario, mark **PASS / FAIL / N/A** and any notes.

### S1. Two-player basic

| Step | Expected | Result |
|---|---|---|
| Host: launch, press M, press H | "Hosting LAN (UDP)..." | |
| Client: launch, press M, press C (LAN), press J, type host IP, press Enter | "Connected to LAN (UDP)!" | |
| Both: see each other in the lobby list | 2 players visible | |
| Client: press R | ready toggle works | |
| Host: lobby shows client as Ready | isHost false, ready true | |
| Host: press SPACE | game starts on both screens | |
| Both: collect 3 coins | TEAM COINS goes 0 → 3 → 6 → ... on both | |
| Both: open Team Shop (T from Multiplayer or main menu) | both see the same coin balance | |
| Client: buy upgrade `1` (speed) | both players' speed stat increments | |
| Host: buy upgrade `4` (magnet) | both players' magnet level increments | |
| Host: dash (Q) | visible on both screens | |
| Client: shield (E) | visible on both screens | |

### S2. Lobby reset / re-ready loop (×20)

- [ ] From in-game, both players die (or pause/leave).
- [ ] Return to lobby.
- [ ] Un-ready, re-ready, host starts again.
- [ ] **Repeat 20 times.**
- [ ] Watch for: stuck ready state, player count desync, missing PlayerList updates, duplicate players in the list.

### S3. Join / leave mid-session

- [ ] Host a game, client joins.
- [ ] Client force-quits the game (close window or kill process).
- [ ] Within 5 s the host's player list should drop back to 1.
- [ ] Client relaunches and rejoins with the same IP.
- [ ] Lobby shows the client back in the list.

### S4. Host crash

- [ ] Host a game, client joins.
- [ ] Kill the host process.
- [ ] Client should show "Disconnected (Timeout)" within 5 s.
- [ ] Restart the host; client can rejoin.

### S5. Stress: 3–4 players (if hardware available)

- [ ] On a third machine, repeat the join flow.
- [ ] LAN manager caps at 4 players. Verify the 5th player gets rejected cleanly (no crash, no half-added entry).

### S6. Packet loss simulation (root only)

- [ ] On the host, while the game is running:
  ```bash
  sudo ./scripts/lan_2machine_check.sh netem
  ```
- [ ] This adds `delay 50ms ± 20ms, loss 2%` on **loopback only** (won't affect real LAN traffic — that's the point of step S7).
- [ ] Confirm the local game still feels playable (no rubber-banding past 200 ms).
- [ ] Remove:
  ```bash
  sudo ./scripts/lan_2machine_check.sh unnetem
  ```

### S7. Real-Wi-Fi packet loss (advanced)

Requires root on a Linux router or `tc` access on one of the machines'
network interface (e.g. `tc qdisc add dev wlan0 root netem ...`). This is
beyond the scope of the helper script — see `man tc-netem`.

### S8. Team shop consistency under spam

- [ ] Both players rapidly tap `1`/`2`/`3`/`4` for ~5 seconds.
- [ ] Both players' stats should converge to the same values.
- [ ] No player should end up with more coins than the team pool allows.
- [ ] `transaction_id` in network logs should be strictly monotonic per host.

## Reporting

If anything fails, capture:

1. `dodge_magma` console output from **both** machines.
2. Output of `./scripts/lan_2machine_check.sh ping <other-ip>` from both.
3. The exact button sequence that triggered the bug.

File an issue with the above + the tag `multiplayer`.

## What this checklist does NOT cover

- **EOS/Online mode** — needs Epic SDK credentials and a real product
  setup. See Epic's docs.
- **NAT traversal** — the game assumes direct LAN; if either side is
  behind a NAT without UPnP, the connection will silently fail.
- **IPv6** — UDP bind is `INADDR_ANY`; only IPv4 has been tested.