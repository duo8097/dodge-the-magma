#include "LanManager.h"
#include <iostream>
#include <vector>
#include <cstring>
#include <chrono>

#ifdef _WIN32
    #pragma comment(lib, "ws2_32.lib")
    typedef SOCKET socket_t;
    #define INVALID_SOCKET_VAL INVALID_SOCKET
    #define SOCKET_ERROR_VAL SOCKET_ERROR
    #define CLOSE_SOCKET closesocket
#else
    #include <netdb.h>
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
    if (flags != -1) {
        fcntl(sock, F_SETFL, flags | O_NONBLOCK);
    }
#endif
}

static uint64_t GetTimeMs() {
    auto now = std::chrono::steady_clock::now();
    return std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count();
}

static bool AddrEqual(const sockaddr_in& a, const sockaddr_in& b) {
    return a.sin_addr.s_addr == b.sin_addr.s_addr && a.sin_port == b.sin_port;
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
    // m_isConnected and m_isHost will be set by HostGame/JoinGame or Shutdown
    m_isHost = false;

    m_isJoining = false;
    m_myPlayerId = (uint32_t)rand() + 1;
    m_myPlayerName = "Player_" + std::to_string(m_myPlayerId);
    m_statusMessage = "LAN Initialized";
    return true;
}

void LanManager::Tick() {
    uint64_t now = GetTimeMs();
    
    // 1. Client join retries
    if (!m_isHost && m_isJoining) {
        if (now - m_lastJoinAttemptTime >= 500) {
            m_lastJoinAttemptTime = now;
            socket_t sock = (socket_t)m_clientSocket;
            if (sock != INVALID_SOCKET_VAL) {
                PlayerJoinPacket joinPkt;
                joinPkt.type = 5;
                joinPkt.playerId = m_myPlayerId;
                
                strncpy(joinPkt.name, m_myPlayerName.c_str(), 31);
                joinPkt.name[31] = '\0';
                
                ssize_t sent = sendto(sock, (const char*)&joinPkt, sizeof(joinPkt), 0, (struct sockaddr*)&m_hostAddress, sizeof(m_hostAddress));
                if (sent < 0) {
                    std::cout << "Warning: sendto failed on join packet" << std::endl;
                }
            }
        }
    }
    
    // 2. Receive incoming data
    ReceiveData();
    
    // 3. Heartbeat timeout check
    if (m_isConnected) {
        if (m_isHost) {
            // Host checks clients timeout
            bool listChanged = false;
            for (int i = (int)m_players.size() - 1; i >= 0; --i) {
                if (m_players[i].isHost) continue;
                if (now - m_players[i].lastSeen > 4000) { // 4 seconds timeout
                    std::cout << "Player " << m_players[i].name << " timed out." << std::endl;
                    RemovePlayer(i);
                    listChanged = true;
                }
            }
            if (listChanged) {
                m_isConnected = (m_players.size() > 1);
                if (!m_isConnected) {
                    m_statusMessage = "Hosting LAN (UDP)...";
                }
                SendPlayerList();
            }
        } else {
            // Client checks host timeout
            if (now - m_lastPingTime > 4000) {
                std::cout << "Host timed out." << std::endl;
                Shutdown();
                m_statusMessage = "Disconnected (Timeout)";
                if (onConnectionEstablished) onConnectionEstablished(false);
            }
            // --- Bug #3 Fix: Send KeepAlivePacket periodically from client ---
            else if (now - m_lastPingTime > 1000) { // Send keep-alive every 1 second
                KeepAlivePacket alivePkt;
                SendPacket(&alivePkt, sizeof(alivePkt));
                m_lastPingTime = now; // Reset timer after sending
            }
            // --- End Bug #3 Fix ---
        }
    }
}

void LanManager::Shutdown() {
    if (m_clientSocket != INVALID_SOCKET_VAL) CLOSE_SOCKET((socket_t)m_clientSocket);
    if (m_serverSocket != INVALID_SOCKET_VAL) CLOSE_SOCKET((socket_t)m_serverSocket);
    m_clientSocket = INVALID_SOCKET_VAL;
    m_serverSocket = INVALID_SOCKET_VAL;
    m_isHost = false;
    m_isConnected = false;
    m_isJoining = false;
    m_players.clear();
#ifdef _WIN32
    WSACleanup();
#endif
}

void LanManager::HostGame() {
    m_isHost = true;
    m_isConnected = false;
    m_statusMessage = "Hosting LAN (UDP)...";
    m_players.clear();
    
    srand(static_cast<unsigned int>(GetTimeMs()));
    m_myPlayerId = (uint32_t)rand() + 1;
    
    std::string myName = "Player_" + std::to_string(rand() % 10000 + 1000);
    AddPlayer(m_myPlayerId, myName.c_str(), true); // Add host as first player
    
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
    m_isConnected = true; // Host is considered connected once bound and listening
}

void LanManager::JoinGame(const std::string& addressOrId) {
    m_isHost = false;
    m_isConnected = false; // Client is not connected until it receives PlayerList
    m_statusMessage = "Joining LAN (UDP)...";
    m_players.clear();
    
    srand(static_cast<unsigned int>(GetTimeMs()));
    m_myPlayerId = (uint32_t)rand() + 1;
    
    if (m_clientSocket != INVALID_SOCKET_VAL) {
        CLOSE_SOCKET((socket_t)m_clientSocket);
        m_clientSocket = INVALID_SOCKET_VAL;
    }
    
    socket_t sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == INVALID_SOCKET_VAL) return;
    
    memset(&m_hostAddress, 0, sizeof(m_hostAddress));
    m_hostAddress.sin_family = AF_INET;
    m_hostAddress.sin_port = htons(LAN_PORT);
    int r = inet_pton(AF_INET, addressOrId.empty() ? "127.0.0.1" : addressOrId.c_str(), &m_hostAddress.sin_addr);
    if (r <= 0) {
        m_statusMessage = "Invalid IP Address format";
        CLOSE_SOCKET(sock);
        return;
    }
    
    SetNonBlocking(sock);
    m_clientSocket = (size_t)sock;
    m_isJoining = true;
    m_lastJoinAttemptTime = GetTimeMs(); // Initialize join attempt timer
    m_lastPingTime = GetTimeMs();
    if (m_myPlayerName.empty()) {
        m_myPlayerName = "Player_" + std::to_string(m_myPlayerId);
    }

}

void LanManager::AcceptClients() {
    // Client acceptance logic is handled dynamically in ReceiveData and Tick.
    // No explicit accept() call is needed for UDP sockets.
}


void LanManager::SendPacket(const void* data, uint32_t length) {
    if (m_isHost) {
        socket_t sock = (socket_t)m_serverSocket;
        if (sock == INVALID_SOCKET_VAL) return;
        // Send to all peers
        for (const auto& peer : m_players) {
            if (peer.isHost) continue; // don't send to ourselves
            if (peer.addressValid) {
                ssize_t sent = sendto(sock, (const char*)data, length, 0, (struct sockaddr*)&peer.address, sizeof(peer.address));
                if (sent < 0) {
                    std::cout << "Warning: sendto failed to peer" << std::endl;
                }
            }
        }
    } else {
        socket_t sock = (socket_t)m_clientSocket;
        if (sock == INVALID_SOCKET_VAL) return;
        ssize_t sent = sendto(sock, (const char*)data, length, 0, (struct sockaddr*)&m_hostAddress, sizeof(m_hostAddress));
        if (sent < 0) {
            std::cout << "Warning: sendto failed to host" << std::endl;
        }
    }
}

void LanManager::ReceiveData() {
    socket_t sock = m_isHost ? (socket_t)m_serverSocket : (socket_t)m_clientSocket;
    if (sock == INVALID_SOCKET_VAL) return;
    
    char buffer[1024];
    while (true) {
        sockaddr_in senderAddr;
        socklen_t senderLen = sizeof(senderAddr);
        int r = recvfrom(sock, buffer, sizeof(buffer), 0, (struct sockaddr*)&senderAddr, &senderLen);
        if (r <= 0) break; // No more packets / non-blocking would block
        
        if (r < 1) continue; // Malformed / empty packet
        
        uint8_t type = buffer[0];
        uint64_t now = GetTimeMs();
        
        if (m_isHost) {
            // Host handles packets
            if (type == 5) { // PlayerJoinPacket
                if (r != sizeof(PlayerJoinPacket)) continue;
                PlayerJoinPacket* joinPkt = reinterpret_cast<PlayerJoinPacket*>(buffer);
                
                int idx = FindPlayerById(joinPkt->playerId);
                if (idx == -1) {
                    if (m_players.size() < 4) {
                        AddPlayer(joinPkt->playerId, joinPkt->name, false, true, &senderAddr);
                        std::cout << "Player joined: " << joinPkt->name << " ID: " << joinPkt->playerId << std::endl;
                        m_isConnected = true; // Now connected to at least one client
                        if (onConnectionEstablished) onConnectionEstablished(true);
                    }
                } else {
                    // Update existing player address and lastSeen
                    m_players[idx].address = senderAddr;
                    m_players[idx].addressValid = true;
                    m_players[idx].lastSeen = now;
                    // If the host was disconnected (e.g. player timed out) and this player re-joins, we need to re-establish connection state
                    if (!m_isConnected) {
                        m_isConnected = true;
                        if (onConnectionEstablished) onConnectionEstablished(true);
                    }
                }
                // --- Bug #1 Fix: Call onPlayerJoinReceived for the host --- 
                PlayerJoinPacket joinPktForCallback;
                joinPktForCallback.playerId = joinPkt->playerId;
                strncpy(joinPktForCallback.name, joinPkt->name, 31);
                joinPktForCallback.name[31] = '\0';
                int callbackIdx = FindPlayerById(joinPkt->playerId);
                joinPktForCallback.isHost = callbackIdx != -1 ? m_players[callbackIdx].isHost : false;
                if (onPlayerJoinReceived) {
                    onPlayerJoinReceived(joinPktForCallback);
                }
                // --- End Bug #1 Fix ---

                m_statusMessage = "Client Connected (UDP)!";
                SendPlayerList();

            } else {
                // Other packets must come from a registered client
                int idx = -1;
        // Find player by address to ensure packet is from a known client
        int idx = -1;
        for (size_t i = 0; i < m_players.size(); ++i) {
            if (!m_players[i].isHost && m_players[i].addressValid && AddrEqual(m_players[i].address, senderAddr)) {
                idx = (int)i;
                break;
            }
        }
        if (idx == -1) {
            // Packet from an unknown address, ignore unless it's a join packet (handled above)
            continue; 
        }
        
        m_players[idx].lastSeen = now; // Update last seen time for the known player
        
        if (type == 1 && onPlayerStateReceived && r == sizeof(PlayerStatePacket)) {
                    auto& pkt = *reinterpret_cast<PlayerStatePacket*>(buffer);
                    // Validate playerId matches the sender's registered player
                    if (pkt.playerId != m_players[idx].playerId) {
                        // PlayerId mismatch - potential spoofing, ignore packet
                        continue;
                    }
                    onPlayerStateReceived(pkt);
                } else if (type == 3 && onCoinPickupReceived && r == sizeof(CoinPickupPacket)) {
                    auto& pkt = *reinterpret_cast<CoinPickupPacket*>(buffer);
                    onCoinPickupReceived(pkt.count, pkt.team_coins);
                } else if (type == 4 && onTeamUpgradeReceived && r == sizeof(TeamUpgradePacket)) {
                    auto& pkt = *reinterpret_cast<TeamUpgradePacket*>(buffer);
                    onTeamUpgradeReceived(pkt.upgrade_id, pkt.new_value, pkt.transaction_id);
            } else if (type == 7 && onReadyStatusReceived && r == sizeof(ReadyStatusPacket)) {
                auto& pkt = *reinterpret_cast<ReadyStatusPacket*>(buffer);
                // Find player by ID, not name
                int playerIndex = FindPlayerById(pkt.playerId);
                if (playerIndex != -1) {
                    m_players[playerIndex].ready = pkt.ready;
                    onReadyStatusReceived(pkt); // Pass the packet with playerId
                    SendPlayerList(); // Broadcast updated list
                    continue; // Skip the standard forward below because SendPlayerList already broadcasts
                }
            } else if (type == 9) { // KeepAlivePacket
                // Just update last seen time, no further action needed
                // idx is already found from the loop above
                // m_players[idx].lastSeen = now; // This is handled by the loop already
                continue; // Do not forward keep-alive packets
            }
            
            // Forward/relay to all other peers
            for (const auto& other : m_players) {
                if (other.isHost || (other.addressValid && AddrEqual(other.address, senderAddr))) continue;
                ssize_t sent = sendto((socket_t)m_serverSocket, buffer, r, 0, (struct sockaddr*)&other.address, sizeof(other.address));
                if (sent < 0) {
                    std::cout << "Warning: sendto failed forwarding packet" << std::endl;
                }
            }

            }
        } else {
            // Client handles packets, verify sender is the host
            if (!AddrEqual(senderAddr, m_hostAddress)) continue;
            
            m_lastPingTime = now;
            
            if (type == 1 && onPlayerStateReceived && r == sizeof(PlayerStatePacket)) {
                onPlayerStateReceived(*reinterpret_cast<PlayerStatePacket*>(buffer));
            } else if (type == 2 && onMagmaSpawnReceived && r == sizeof(SpawnMagmaPacket)) {
                onMagmaSpawnReceived(*reinterpret_cast<SpawnMagmaPacket*>(buffer));
            } else if (type == 3 && onCoinPickupReceived && r == sizeof(CoinPickupPacket)) {
                auto& pkt = *reinterpret_cast<CoinPickupPacket*>(buffer);
                onCoinPickupReceived(pkt.count);
            } else if (type == 4 && onTeamUpgradeReceived && r == sizeof(TeamUpgradePacket)) {
                    auto& pkt = *reinterpret_cast<TeamUpgradePacket*>(buffer);
                    onTeamUpgradeReceived(pkt.upgrade_id, pkt.new_value, pkt.transaction_id);
            } else if (type == 6 && onPlayerListReceived && r == sizeof(PlayerListPacket)) {
                auto& pkt = *reinterpret_cast<PlayerListPacket*>(buffer);
                if (pkt.count <= 4) {
                    m_players.clear();
                    for (uint8_t i = 0; i < pkt.count; ++i) {
                        ConnectedPlayer p;
                        p.playerId = pkt.players[i].playerId;
                        strncpy(p.name, pkt.players[i].name, 31);
                        p.name[31] = '\0';
                        p.ready = pkt.players[i].ready;
                        p.isHost = pkt.players[i].isHost;
                        m_players.push_back(p);
                    }
                    if (m_isJoining) {
                        m_isJoining = false;
                        m_isConnected = true;
                        m_statusMessage = "Connected to LAN (UDP)!";
                        if (onConnectionEstablished) onConnectionEstablished(true);
                    }
                    onPlayerListReceived(pkt);
                }
            } else if (type == 8 && onStartGameReceived && r == sizeof(StartGamePacket)) {
                onStartGameReceived(*reinterpret_cast<StartGamePacket*>(buffer));
            }
        }
    }
}

void LanManager::AddPlayer(uint32_t id, const char* name, bool isHost, bool addressValid, const sockaddr_in* addr) {
    if (m_players.size() >= 4) return;
    ConnectedPlayer p;
    p.playerId = id;
    strncpy(p.name, name, 31);
    p.name[31] = '\0';
    p.ready = false;
    p.isHost = isHost;
    p.addressValid = addressValid;
    if (addr) p.address = *addr;
    p.lastSeen = GetTimeMs();
    m_players.push_back(p);
}

void LanManager::RemovePlayer(int index) {
    if (index >= 0 && index < (int)m_players.size()) {
        // --- Bug #4 Fix: Notify about player removal ---
        if (onPlayerRemoved) {
            // Need to pass player info to the callback
            // Construct a PlayerJoinPacket-like structure or similar if available
            // For now, assume we can pass playerId and name
            PlayerJoinPacket removedPlayerData;
            removedPlayerData.playerId = m_players[index].playerId;
            strncpy(removedPlayerData.name, m_players[index].name, 31);
            removedPlayerData.name[31] = '\0';
            removedPlayerData.isHost = m_players[index].isHost; // This might be misleading if player was not host
            onPlayerRemoved(removedPlayerData);
        }
        // --- End Bug #4 Fix ---
        m_players.erase(m_players.begin() + index);
    }
}

int LanManager::FindPlayerByName(const char* name) {
    for (size_t i = 0; i < m_players.size(); ++i) {
        if (strcmp(m_players[i].name, name) == 0) return (int)i;
    }
    return -1;
}

int LanManager::FindPlayerById(uint32_t id) {
    for (size_t i = 0; i < m_players.size(); ++i) {
        if (m_players[i].playerId == id) return (int)i;
    }
    return -1;
}

void LanManager::SendPlayerList() {
    if (!m_isHost) return;
    PlayerListPacket pkt;
    pkt.count = (uint8_t)m_players.size();
    for (size_t i = 0; i < m_players.size(); ++i) {
        pkt.players[i].playerId = m_players[i].playerId;
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