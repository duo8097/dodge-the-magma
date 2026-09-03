#ifndef NETWORK_PROVIDER_H
#define NETWORK_PROVIDER_H

#include <string>
#include <functional>
#include <cstdint>

// ── Packet type IDs ──────────────────────────────────────────────────────────
//  1 = PlayerStatePacket   (position / shield / score)
//  2 = SpawnMagmaPacket    (magma spawned by host)
//  3 = CoinPickupPacket    (coin(s) collected — adds to shared team pool)
//  4 = TeamUpgradePacket   (team shop purchase — upgrade synced to peer)
//  5 = PlayerJoinPacket    (client sends to host on join)
//  6 = PlayerListPacket    (host sends to all with player list & ready status)
//  7 = ReadyStatusPacket   (client toggles ready state)
//  8 = StartGamePacket     (host signals all to start game)
// ─────────────────────────────────────────────────────────────────────────────

#pragma pack(push, 1)

struct PlayerStatePacket {
    uint8_t  type      = 1;
    float    x;
    float    y;
    float    vx;
    float    vy;
    bool     has_shield;
    int32_t  score;          // sender's current score (for team score display)
};

struct SpawnMagmaPacket {
    uint8_t type  = 2;
    float   x;
    float   y;
    float   w;
    float   h;
    float   speed;
};

struct CoinPickupPacket {
    uint8_t  type  = 3;
    int32_t  count;          // number of coins just collected by sender
};

struct TeamUpgradePacket {
    uint8_t  type       = 4;
    uint8_t  upgrade_id; // 0=speed  1=jump  2=shield  3=magnet
    int32_t  new_value;  // stat value after upgrade (applied on receiver side)
};

struct PlayerJoinPacket {
    uint8_t  type = 5;
    uint32_t playerId;
    char     name[32];
};

struct PlayerInfo {
    uint32_t playerId;
    char     name[32];
    bool     ready;
    bool     isHost;
};

struct PlayerListPacket {
    uint8_t type = 6;
    uint8_t count;
    PlayerInfo players[4];
};

struct ReadyStatusPacket {
    uint8_t  type = 7;
    bool     ready;
    uint32_t playerId;
};

struct StartGamePacket {
    uint8_t type = 8;
};

#pragma pack(pop)

// ─────────────────────────────────────────────────────────────────────────────

class NetworkProvider {
public:
    virtual ~NetworkProvider() = default;

    virtual bool Init()                                    = 0;
    virtual void Tick()                                    = 0;
    virtual void Shutdown()                                = 0;

    virtual void HostGame()                                = 0;
    virtual void JoinGame(const std::string& addressOrId)  = 0;
    virtual void SendPacket(const void* data, uint32_t len)= 0;

    virtual bool        IsHost()      const = 0;
    virtual bool        IsConnected() const = 0;
    virtual std::string GetStatus()   const = 0;
    virtual std::string GetMyId()     const = 0;

    // ── Callbacks ──
    std::function<void(const PlayerStatePacket&)>    onPlayerStateReceived;
    std::function<void(const SpawnMagmaPacket&)>     onMagmaSpawnReceived;
    std::function<void(bool)>                        onConnectionEstablished;
    std::function<void(int /*count*/)>               onCoinPickupReceived;    // team coin sync
    std::function<void(uint8_t /*id*/, int32_t)>     onTeamUpgradeReceived;  // team shop sync
    std::function<void(const PlayerJoinPacket&)>     onPlayerJoinReceived;
    std::function<void(const PlayerListPacket&)>     onPlayerListReceived;
    std::function<void(const ReadyStatusPacket&)>    onReadyStatusReceived;
    std::function<void(const StartGamePacket&)>      onStartGameReceived;
};

#endif // NETWORK_PROVIDER_H
