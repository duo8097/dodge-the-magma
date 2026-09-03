# Dodge the Magma

A small arcade game where you dodge falling magma, collect coins, and use dashes and shields to survive as long as possible.

Supports **LAN and online multiplayer**, including shared team coins, a team shop, and team score tracking.

## Building (C++ / raylib)

### Requirements

* C++17-compatible compiler (GCC, Clang, or MSVC)
* CMake 3.15 or newer
* **Windows:** No additional dependencies are required. Winsock2 is included with MSVC/MinGW.
* **Linux:** The following packages are required:

  * `build-essential`
  * `libgl1-mesa-dev`
  * `libx11-dev`
  * `libxrandr-dev`
  * `libxi-dev`
  * `libxcursor-dev`
  * `libxinerama-dev`

### Build & Run

```bash
cd cpp
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . -j
```

Run the game:

**Linux**

```bash
./bin/dodge_magma
```

**Windows**

```powershell
.\bin\dodge_magma.exe
```

> Want to test multiplayer before playing? Run the [automated test suite](#automated-multiplayer-test-suite) (~1 min, no partner needed) or the [2-machine helper script](#manual-2-machine-lan-test).

## Multiplayer

Press **`M`** from the main menu to open the dedicated **Multiplayer** screen.

### Connecting

| Key   | Action                                        |
| ----- | --------------------------------------------- |
| `C`   | Toggle between **LAN (UDP)** and **Online (EOS)** |
| `H`   | Host a game                                   |
| `J`   | Start entering the host **IP** (to join)      |
| `T`   | Open the **Team Shop** (when connected)       |
| `ESC` | Return to the main menu                       |

**To join:** press **`J`** to start typing the host's IP address, then press **`Enter`** to connect. Press **`ESC`** while typing to cancel.

### Lobby (Ready-up flow)

Once a client connects, both players are taken to the **Lobby** screen where a list of joined players and their ready status is shown. The game will not start until every player is ready.

| Key     | Action                                            |
| ------- | ------------------------------------------------- |
| `R`     | Toggle ready / unready (client only)              |
| `SPACE` | Start the game (host only, when **all** ready)    |
| `ESC`   | Leave the lobby and return to the Multiplayer screen |

After everyone has readied up, the **host** presses **`SPACE`** to launch the game together.

### Team Features

| Feature        | Details                                                                                                                                                                                                                                 |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Team Coins** | Players share a single coin pool. When either player collects a coin, a `CoinPickupPacket` is sent to the peer. Both sides add the coins to `team_coins`. Coins are **not** added to the players' personal balances during multiplayer. |
| **Team Shop**  | Open the shop with **`T`** from the Multiplayer screen while connected. Purchases are deducted from `team_coins` and applied to **both** players. The buyer sends a `TeamUpgradePacket` so the peer receives the same stat change.      |
| **Team Score** | The HUD displays both your score and the remote player's score, making the team's combined performance easy to track.                                                                                                                   |
| **Team HUD**   | During multiplayer, the HUD displays `SCORE`, `P2 SCORE`, and `TEAM COINS`.                                                                                                           
## Controls

### Main Menu

| Key     | Action                      |
| ------- | --------------------------- |
| `SPACE` | Start a solo game           |
| `S`     | Open the shop               |
| `M`     | Open the Multiplayer screen |
| `O`     | Open settings               |
| `Q`     | Exit                        |

### Multiplayer Screen

| Key   | Action                              |
| ----- | ----------------------------------- |
| `C`   | Toggle between LAN and Online       |
| `H`   | Host a game                         |
| `J`   | Start entering the host IP to join  |
| `Enter` | Confirm IP and join                 |
| `T`   | Open the Team Shop (when connected) |
| `ESC` | Return to the main menu             |

### Lobby

| Key     | Action                                          |
| ------- | ----------------------------------------------- |
| `R`     | Toggle ready / unready (client only)            |
| `SPACE` | Start the game (host only, when all ready)      |
| `ESC`   | Leave the lobby back to the Multiplayer screen  |

### Team Shop

| Key   | Action                           |
| ----- | -------------------------------- |
| `1`   | Speed +1 (20 team coins)         |
| `2`   | Jump -2 (30 team coins)          |
| `3`   | Shield upgrade (100 team coins)  |
| `4`   | Magnet upgrade (150 team coins)  |
| `ESC` | Return to the Multiplayer screen |

### In Game

| Key                     | Action                                      |
| ----------------------- | ------------------------------------------- |
| `A` / `D` or Arrow Keys | Move                                        |
| `SPACE`                 | Jump / double jump / hold for a higher jump |
| `Q`                     | Dash                                        |
| `E`                     | Activate shield                             |
| `ESC`                   | Pause                                       |
| `` ` ``                 | Open the cheat console                      |

### Solo Shop

| Key   | Action                  |
| ----- | ----------------------- |
| `1`   | Speed upgrade           |
| `2`   | Jump upgrade            |
| `3`   | Shield upgrade          |
| `4`   | Magnet upgrade          |
| `ESC` | Return to the main menu |

## Save System

Game data is saved to `save.txt` using a simple `key=value` format, with no external JSON library required.

The save system stores:

* Coins
* Player speed
* Jump strength
* Shield cooldown
* Shield active time
* Magnet level
* Target FPS

A queue-based autosave mechanism is used to avoid writing to disk too frequently.

## Cheat Console

Press `` ` `` to open the cheat console.

Available commands:

| Command                                 | Description              |
| --------------------------------------- | ------------------------ |
| `help`                                  | List available commands  |
| `coin [n]`                              | Add coins (default: 100) |
| `speed [n]`                             | Add speed (default: 2)   |
| `jump [n]`                              | Add jump (default: 2)    |
| `god`                                   | Enable invincibility     |
| `reset [coins/speed/shield/magnet/all]` | Reset selected stats     |
| `save`                                  | Force a save             |
| `stats`                                 | Show current stats       |
| `exit`                                  | Quit the game            |

## Testing

### Automated multiplayer test suite

The C++ port ships with an automated regression test suite that covers the
multiplayer protocol and `LanManager` end-to-end through real UDP sockets
(127.0.0.1). It catches regressions in packet layout, team-coin sync, team
shop transactions, lobby flow, join/leave/reconnect, packet spam, and
mid-transaction disconnect.

To build & run:

```bash
cd cpp/build
cmake .. -DBUILD_TESTS=ON
cmake --build . --target test_multiplayer
./bin/test_multiplayer
```

Expected output:

```
=== Dodge the Magma — multiplayer test suite ===

[1] Packet struct tests           (5 tests)
[2] Mocked integration            (3 tests)
[3] LAN UDP loopback              (3 tests)
[4] Dual-instance LAN             (6 tests)

=== Results: 86/86 passed, 0 failed ===
```

Run this before opening a PR that touches `NetworkProvider.h` or
`LanManager.{h,cpp}` — it runs in under a minute and exercises every
protocol path.

### Manual 2-machine LAN test

Automated tests cover the protocol layer but cannot replace running the
real game across two physical machines. Use the helper script and
checklist:

- [`scripts/lan_2machine_check.sh`](scripts/lan_2machine_check.sh) —
  firewall setup, ping, UDP probe, and optional `tc netem` for local
  latency/loss simulation.
- [`docs/lan_2machine_checklist.md`](docs/lan_2machine_checklist.md) —
  8 manual scenarios (basic 2-player, lobby reset loop ×20, join/leave
  mid-session, host crash, 3-4 player, packet loss sim, real-Wi-Fi loss,
  team shop under spam).

Quick start on two laptops:

```bash
# On the HOST:
./scripts/lan_2machine_check.sh host

# On the CLIENT (replace with the host's IP):
./scripts/lan_2machine_check.sh client 192.168.1.42
```

If the ping/UDP probe works but the game can't connect, the most common
culprits are:

- host firewall blocking UDP 45678 (`sudo ufw allow 45678/udp`)
- client typed the wrong IP
- both machines on different VLANs / guest networks

If you find a bug while testing, file an issue with the `multiplayer`
tag and attach the console output from both machines.

## Project Structure

```text
Dodge-the-Magma/
├── cpp/                                  # C++ port (active development)
│   ├── dodge_the_magma_desktop_cpp.cpp  # Main game
│   ├── NetworkProvider.h                 # Network interface and packet definitions
│   ├── LanManager.h / .cpp               # LAN UDP implementation
│   ├── EOSManager.h / .cpp               # Online EOS implementation
│   ├── tests/test_multiplayer.cpp        # Automated multiplayer tests
│   └── build/                            # Build output
│       └── bin/dodge_magma(.exe)
├── python (deprecated)/                   # Original Python + pygame-ce version
├── scripts/
│   └── lan_2machine_check.sh              # 2-machine test helper
├── docs/
│   └── lan_2machine_checklist.md          # Manual 2-machine checklist
└── third-party-api/                      # EOS SDK headers
```

## Legacy Python Version

The original Python + `pygame-ce` version is kept in `python (deprecated)/` for reference.

It is **no longer maintained**. The C++ version has feature parity with the Python version and additionally provides multiplayer support.
