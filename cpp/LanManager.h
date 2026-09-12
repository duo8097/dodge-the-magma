#ifndef LAN_MANAGER_H
#define LAN_MANAGER_H

#include "NetworkProvider.h"
#include <vector>
#include <string>
#include <cstdint> // Include for uint64_t etc.

#ifdef _WIN32
    // WIN32_LEAN_AND_MEAN trims out lesser-used API sets (RPC, Shell, DDE...).
    // NOGDI/NOUSER are what actually stop windows.h from declaring
    // Rectangle(), CloseWindow(), ShowCursor(), DrawText()... — names raylib
    // also uses, which otherwise causes redeclaration errors. NOMINMAX
    // stops windows.h from defining min/max macros that break std::min/std::max.
    #ifndef WIN32_LEAN_AND_MEAN
        #define WIN32_LEAN_AND_MEAN
    #endif
    #ifndef NOGDI
        #define NOGDI
    #endif
    #ifndef NOUSER
        #define NOUSER
    #endif
    #ifndef NOMINMAX
        #define NOMINMAX
    #endif
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #include <basetsd.h> // SSIZE_T
    typedef SSIZE_T ssize_t;
#else
    #include <sys/socket.h>
    #include <arpa/inet.h>
    #include <netinet/in.h>
#endif

class LanManager : public NetworkProvider {
public:
    // Singleton accessor (kept for backward compat with the game code).
    // Prefer constructing your own instance for tests / multi-instance use.
    static LanManager& Get();

    // Public constructor so tests and other consumers can own multiple instances.
    LanManager();
    ~LanManager() override;

    // Disable copy/move: this class owns sockets and global WSA state.
    LanManager(const LanManager&) = delete;
    LanManager& operator=(const LanManager&) = delete;

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
    uint32_t GetPlayerId() const override;
    int GetPlayerCount() const override;
    uint32_t GetPlayerIdAt(int slot) const override;

private:
    bool m_isHost = false;
    bool m_isConnected = false;
    std::string m_statusMessage = "Offline (LAN)";
    
    size_t m_serverSocket = ~static_cast<size_t>(0);
    size_t m_clientSocket = ~static_cast<size_t>(0);
    
    struct ConnectedPlayer {
        uint32_t playerId = 0;
        char name[32] = {0};
        bool ready = false;
        bool isHost = false;
        bool addressValid = false;
        sockaddr_in address;
        uint64_t lastSeen = 0;
    };
    std::vector<ConnectedPlayer> m_players;
    
    uint32_t m_myPlayerId = 0;
    std::string m_myPlayerName;
    bool m_isJoining = false;
    bool m_wsaInitialized = false;
    void GeneratePlayerId(uint32_t mixSalt);
    uint64_t m_lastJoinAttemptTime = 0;
    uint64_t m_lastKeepAliveSendTime = 0; // Bug #51: separate from host-packet timestamp
    uint64_t m_lastHostPacketTime = 0;    // Bug #51: clean "last time we heard from host"
    sockaddr_in m_hostAddress;
    
    void ReceiveData();
    void AcceptClients();
    void SendPlayerList();
    void AddPlayer(uint32_t id, const char* name, bool isHost, bool addressValid = false, const sockaddr_in* addr = nullptr);
    void RemovePlayer(int index);
    int FindPlayerByName(const char* name);
    int FindPlayerById(uint32_t id);
    int FindPlayerByAddress(const sockaddr_in& addr);
};

#endif // LAN_MANAGER_H
