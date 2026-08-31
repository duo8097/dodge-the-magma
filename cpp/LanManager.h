#ifndef LAN_MANAGER_H
#define LAN_MANAGER_H

#include "NetworkProvider.h"

class LanManager : public NetworkProvider {
public:
    static LanManager& Get();

    bool Init() override;
    void Tick() override;
    void Shutdown() override;

    void HostGame() override;
    void JoinGame(const std::string& addressOrId) override;
    void SendPacket(const void* data, uint32_t length) override;

    bool IsHost() const override { return m_isHost; }
    bool IsConnected() const override { return m_isConnected; }
    
    std::string GetStatus() const override { return m_statusMessage; }
    std::string GetMyId() const override;

private:
    LanManager() = default;
    ~LanManager() = default;

    bool m_isHost = false;
    bool m_isConnected = false;
    std::string m_statusMessage = "Offline (LAN)";
    
    // Using int as socket handle (socket_t), casted to size_t to avoid OS headers in .h
    size_t m_serverSocket = 0;
    size_t m_clientSocket = 0;
    
    void ReceiveData();
    void AcceptClients();
};

#endif // LAN_MANAGER_H
