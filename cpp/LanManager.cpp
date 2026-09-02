#include "LanManager.h"
#include <iostream>
#include <vector>
#include <cstring>

#ifdef _WIN32
    #include <winsock2.h>
    #include <ws2tcpip.h>
    #pragma comment(lib, "ws2_32.lib")
    typedef SOCKET socket_t;
    #define INVALID_SOCKET_VAL INVALID_SOCKET
    #define SOCKET_ERROR_VAL SOCKET_ERROR
    #define CLOSE_SOCKET closesocket
#else
    #include <sys/socket.h>
    #include <arpa/inet.h>
    #include <netinet/in.h>
    #include <netdb.h>      // <-- dời vào đây
    #include <unistd.h>
    #include <fcntl.h>
    typedef int socket_t;
    #define INVALID_SOCKET_VAL -1
    #define SOCKET_ERROR_VAL -1
    #define CLOSE_SOCKET close
#endif

#define LAN_PORT 45678

static void SetNonBlocking(socket_t sock) {
#ifdef _WIN32
    u_long mode = 1;
    ioctlsocket(sock, FIONBIO, &mode);
#else
    int flags = fcntl(sock, F_GETFL, 0);
    fcntl(sock, F_SETFL, flags | O_NONBLOCK);
#endif
}

LanManager& LanManager::Get() {
    static LanManager instance;
    return instance;
}

bool LanManager::Init() {
    Shutdown(); // Ensure old sockets are cleaned up if re-initializing
#ifdef _WIN32
    WSADATA wsaData;
    WSAStartup(MAKEWORD(2, 2), &wsaData);
#endif
    m_serverSocket = INVALID_SOCKET_VAL;
    m_clientSocket = INVALID_SOCKET_VAL;
    m_isConnected = false;
    m_statusMessage = "LAN Initialized";
    return true;
}

void LanManager::Tick() {
    if (m_isHost && !m_isConnected) {
        AcceptClients();
    }
    if (m_isConnected) {
        ReceiveData();
    }
}

void LanManager::Shutdown() {
    if (m_clientSocket != INVALID_SOCKET_VAL) CLOSE_SOCKET((socket_t)m_clientSocket);
    if (m_serverSocket != INVALID_SOCKET_VAL) CLOSE_SOCKET((socket_t)m_serverSocket);
    m_clientSocket = INVALID_SOCKET_VAL;
    m_serverSocket = INVALID_SOCKET_VAL;
#ifdef _WIN32
    WSACleanup();
#endif
}

void LanManager::HostGame() {
    m_isHost = true;
    m_statusMessage = "Hosting LAN (UDP)...";
    m_players.clear();
    
    // Add host as first player
    std::string myName = "Player1";
    AddPlayer(myName.c_str(), true);
    
    if (m_serverSocket != INVALID_SOCKET_VAL) {
        CLOSE_SOCKET((socket_t)m_serverSocket);
        m_serverSocket = INVALID_SOCKET_VAL;
    }
    
    socket_t sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == INVALID_SOCKET_VAL) return;
    
    int opt = 1;
    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));
    
    sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(LAN_PORT);
    
    if (bind(sock, (struct sockaddr*)&addr, sizeof(addr)) == SOCKET_ERROR_VAL) {
        CLOSE_SOCKET(sock);
        m_statusMessage = "Failed to bind port";
        return;
    }
    
    SetNonBlocking(sock);
    m_serverSocket = (size_t)sock;
    m_isConnected = false; // Will set to true when we receive a packet from a client
}

void LanManager::JoinGame(const std::string& addressOrId) {
    m_isHost = false;
    m_statusMessage = "Joining LAN (UDP)...";
    
    if (m_clientSocket != INVALID_SOCKET_VAL) {
        CLOSE_SOCKET((socket_t)m_clientSocket);
        m_clientSocket = INVALID_SOCKET_VAL;
    }
    
    socket_t sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == INVALID_SOCKET_VAL) return;
    
    sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_port = htons(LAN_PORT);
    inet_pton(AF_INET, addressOrId.empty() ? "127.0.0.1" : addressOrId.c_str(), &addr.sin_addr);
    
    // For UDP, connect() just sets the default destination for send() and recv()
    if (connect(sock, (struct sockaddr*)&addr, sizeof(addr)) == SOCKET_ERROR_VAL) {
        m_statusMessage = "Failed to set UDP destination";
        CLOSE_SOCKET(sock);
        return;
    }
    
    SetNonBlocking(sock);
    m_clientSocket = (size_t)sock;
    m_isConnected = true;
    m_statusMessage = "Connected to LAN (UDP)!";
    
    // Send a PlayerJoinPacket so the host knows our name
    PlayerJoinPacket joinPkt;
    std::string myName = "Player" + std::to_string(rand() % 100 + 2);
    strncpy(joinPkt.name, myName.c_str(), 31);
    joinPkt.name[31] = '\0';
    send(sock, (const char*)&joinPkt, sizeof(joinPkt), 0);
    
    if (onConnectionEstablished) onConnectionEstablished(true);
}

void LanManager::AcceptClients() {
    socket_t server = (socket_t)m_serverSocket;
    if (server == INVALID_SOCKET_VAL) return;
    
    // In UDP, we don't accept(). We just wait for a packet to get the client's address.
    char buffer[256];
    sockaddr_in clientAddr;
    socklen_t clientLen = sizeof(clientAddr);
    
    int r = recvfrom(server, buffer, sizeof(buffer), 0, (struct sockaddr*)&clientAddr, &clientLen);
    if (r > 0) {
        uint8_t type = buffer[0];
        if (type == 5 && r == sizeof(PlayerJoinPacket)) {
            // We received a PlayerJoinPacket! 
            PlayerJoinPacket* joinPkt = reinterpret_cast<PlayerJoinPacket*>(buffer);
            
            // Connect the server socket to this client
            connect(server, (struct sockaddr*)&clientAddr, clientLen);
            
            // Add player to list
            AddPlayer(joinPkt->name, false);
            
            m_isConnected = true;
            m_statusMessage = "Client Connected (UDP)!";
            if (onConnectionEstablished) onConnectionEstablished(true);
            
            // Send updated player list to all (just this client for now)
            SendPlayerList();
            return;
        }
        
        // If we get here without a join packet, it might be a reconnect or something else
        // We can still connect if we already have a client
        if (m_players.size() > 1) {
            connect(server, (struct sockaddr*)&clientAddr, clientLen);
            m_isConnected = true;
            m_statusMessage = "Client Connected (UDP)!";
            if (onConnectionEstablished) onConnectionEstablished(true);
        }
    }
}

void LanManager::SendPacket(const void* data, uint32_t length) {
    if (!m_isConnected) return;
    socket_t sock = m_isHost ? (socket_t)m_serverSocket : (socket_t)m_clientSocket;
    if (sock == INVALID_SOCKET_VAL) return;
    
    // UDP preserves message boundaries, no need for length headers!
    send(sock, (const char*)data, length, 0);
}

void LanManager::ReceiveData() {
    socket_t sock = m_isHost ? (socket_t)m_serverSocket : (socket_t)m_clientSocket;
    if (sock == INVALID_SOCKET_VAL) return;
    
    char buffer[1024];
    while (true) {
        int r = recv(sock, buffer, sizeof(buffer), 0);
        if (r <= 0) break; // No more packets to read this frame
        
        uint8_t type = buffer[0];
        if (type == 1 && onPlayerStateReceived && r == sizeof(PlayerStatePacket)) {
            onPlayerStateReceived(*reinterpret_cast<PlayerStatePacket*>(buffer));
        } else if (type == 2 && onMagmaSpawnReceived && r == sizeof(SpawnMagmaPacket)) {
            onMagmaSpawnReceived(*reinterpret_cast<SpawnMagmaPacket*>(buffer));
        } else if (type == 3 && onCoinPickupReceived && r == sizeof(CoinPickupPacket)) {
            auto& pkt = *reinterpret_cast<CoinPickupPacket*>(buffer);
            onCoinPickupReceived(pkt.count);
        } else if (type == 4 && onTeamUpgradeReceived && r == sizeof(TeamUpgradePacket)) {
            auto& pkt = *reinterpret_cast<TeamUpgradePacket*>(buffer);
            onTeamUpgradeReceived(pkt.upgrade_id, pkt.new_value);
        } else if (type == 5 && onPlayerJoinReceived && r == sizeof(PlayerJoinPacket)) {
            onPlayerJoinReceived(*reinterpret_cast<PlayerJoinPacket*>(buffer));
        } else if (type == 6 && onPlayerListReceived && r == sizeof(PlayerListPacket)) {
            onPlayerListReceived(*reinterpret_cast<PlayerListPacket*>(buffer));
        } else if (type == 7 && onReadyStatusReceived && r == sizeof(ReadyStatusPacket)) {
            onReadyStatusReceived(*reinterpret_cast<ReadyStatusPacket*>(buffer));
        } else if (type == 8 && onStartGameReceived && r == sizeof(StartGamePacket)) {
            onStartGameReceived(*reinterpret_cast<StartGamePacket*>(buffer));
        }
    }
}

void LanManager::AddPlayer(const char* name, bool isHost) {
    if (m_players.size() >= 4) return;
    ConnectedPlayer p;
    strncpy(p.name, name, 31);
    p.name[31] = '\0';
    p.ready = false;
    p.isHost = isHost;
    m_players.push_back(p);
}

void LanManager::RemovePlayer(int index) {
    if (index >= 0 && index < (int)m_players.size()) {
        m_players.erase(m_players.begin() + index);
    }
}

int LanManager::FindPlayerByName(const char* name) {
    for (size_t i = 0; i < m_players.size(); ++i) {
        if (strcmp(m_players[i].name, name) == 0) return (int)i;
    }
    return -1;
}

void LanManager::SendPlayerList() {
    if (!m_isHost) return;
    PlayerListPacket pkt;
    pkt.count = (uint8_t)m_players.size();
    for (size_t i = 0; i < m_players.size(); ++i) {
        strncpy(pkt.players[i].name, m_players[i].name, 31);
        pkt.players[i].name[31] = '\0';
        pkt.players[i].ready = m_players[i].ready;
        pkt.players[i].isHost = m_players[i].isHost;
    }
    SendPacket(&pkt, sizeof(pkt));
}

std::string LanManager::GetMyId() const {
    char hostname[256];
    if (gethostname(hostname, sizeof(hostname)) != 0) return "127.0.0.1";
    struct addrinfo hints = {}, *res = nullptr;
    hints.ai_family   = AF_INET;
    hints.ai_socktype = SOCK_STREAM;
    if (getaddrinfo(hostname, nullptr, &hints, &res) == 0 && res) {
        char ip[INET_ADDRSTRLEN] = {};
        sockaddr_in* sa = reinterpret_cast<sockaddr_in*>(res->ai_addr);
        inet_ntop(AF_INET, &sa->sin_addr, ip, sizeof(ip));
        freeaddrinfo(res);
        return std::string(ip);
    }
    return "127.0.0.1";
}
