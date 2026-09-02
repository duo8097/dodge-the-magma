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

## Project Structure

```text
Dodge-the-Magma/
├── cpp/                                  # C++ port (active development)
│   ├── dodge_the_magma_desktop_cpp.cpp  # Main game
│   ├── NetworkProvider.h                 # Network interface and packet definitions
│   ├── LanManager.h / .cpp               # LAN UDP implementation
│   ├── EOSManager.h / .cpp               # Online EOS implementation
│   └── build/                            # Build output
│       └── bin/dodge_magma(.exe)
├── python (deprecated)/                   # Original Python + pygame-ce version
└── third-party-api/                      # EOS SDK headers
```

## Legacy Python Version

The original Python + `pygame-ce` version is kept in `python (deprecated)/` for reference.

It is **no longer maintained**. The C++ version has feature parity with the Python version and additionally provides multiplayer support.
