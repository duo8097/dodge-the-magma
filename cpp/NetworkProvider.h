#ifndef NETWORK_PROVIDER_H
#define NETWORK_PROVIDER_H

#include <string>
#include <functional>
#include <cstdint>

struct PlayerStatePacket {
    uint8_t type = 1; // 1 = state
    float x;
    float y;
    float vx;
    float vy;
    bool has_shield;
};

struct SpawnMagmaPacket {
    uint8_t type = 2; // 2 = spawn magma
    float x;
    float w;
    float h;
    float speed;
};

class NetworkProvider {
public:
    virtual ~NetworkProvider() = default;

    virtual bool Init() = 0;
    virtual void Tick() = 0;
    virtual void Shutdown() = 0;

    virtual void HostGame() = 0;
    virtual void JoinGame(const std::string& addressOrId) = 0;
    virtual void SendPacket(const void* data, uint32_t length) = 0;

    virtual bool IsHost() const = 0;
    virtual bool IsConnected() const = 0;
    
    // Status message for UI
    virtual std::string GetStatus() const = 0;
    virtual std::string GetMyId() const = 0; // For LAN, returns local IP (or blank), for EOS returns PUID

    // Callbacks
    std::function<void(const PlayerStatePacket&)> onPlayerStateReceived;
    std::function<void(const SpawnMagmaPacket&)> onMagmaSpawnReceived;
    std::function<void(bool)> onConnectionEstablished;
};

#endif // NETWORK_PROVIDER_H
