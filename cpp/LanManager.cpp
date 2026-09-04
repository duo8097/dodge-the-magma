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

static uint64_t GetTimeMs();
static int g_wsaRefcount = 0;
static void WSAStartupOnce() {
#ifdef _WIN32
    if (g_wsaRefcount++ == 0) {
        WSADATA wsaData;
        int rc = WSAStartup(MAKEWORD(2, 2), &wsaData);
        if (rc != 0) {
            // Roll back the refcount bump; subsequent socket() calls will
            // fail with WSANOTINITIALISED, but at least we don't claim to
            // have a successful startup.
            g_wsaRefcount--;
            std::cerr << "WSAStartup failed: " << rc << std::endl;
        }
    }
#endif
    // Seed rand() exactly once per process so GeneratePlayerId() doesn't
    // produce the same series across all instances (regression bug #38).
    // Guarded with a separate static so non-Windows builds still seed.
    static bool srandSeeded = false;
    if (!srandSeeded) {
        std::srand(static_cast<unsigned int>(GetTimeMs()) ^ 0x9E3779B9u);
        srandSeeded = true;
    }
}
static void WSACleanupOnce() {
#ifdef _WIN32
    if (g_wsaRefcount > 0 && --g_wsaRefcount == 0) {
        WSACleanup();
    }
#endif
}

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

static bool ProtocolVersionOK(const char* buf, int bytes) {
    // Skip packets that don't carry a protocolVersion byte (type 5/6/7/9)
    // by relying on caller to check type first. Caller must validate type and
    // size before invoking this.
    if (bytes < 2) return false;
    return static_cast<uint8_t>(buf[1]) == CURRENT_PROTOCOL_VERSION;
}

void LanManager::GeneratePlayerId(uint32_t mixSalt) {
    // Per-instance identity. mixSalt lets callers (HostGame/JoinGame) refresh
    // the ID with extra entropy while Init() passes 0 to stay deterministic
    // relative to (this, time). Two instances initialised within the same
    // millisecond still get distinct IDs because (uintptr_t)this differs.
    uint64_t t = GetTimeMs();
    uint32_t r = (uint32_t)rand();
    m_myPlayerId = (uint32_t)((t ^ (uint64_t)r ^ (uint64_t)mixSalt ^ (uintptr_t)this) & 0x7FFFFFFFu);
    if (m_myPlayerId == 0) m_myPlayerId = 1;
}

LanManager& LanManager::Get() {
    static LanManager instance;
    return instance;
}

LanManager::LanManager() = default;
LanManager::~LanManager() {
    // Best-effort cleanup. Shutdown() also handles WSACleanup on Windows.
    Shutdown();
}

bool LanManager::Init() {
    // Close any sockets we already own. WSAStartup/Cleanup are paired per-instance
    // lifetime, not per-Init/Shutdown cycle: multiple Init() calls on one instance
    // must not stack WSAStartup, and Shutdown() must not drop a refcount we don't own.
    if (m_clientSocket != INVALID_SOCKET_VAL) CLOSE_SOCKET((socket_t)m_clientSocket);
    if (m_serverSocket != INVALID_SOCKET_VAL) CLOSE_SOCKET((socket_t)m_serverSocket);
    m_clientSocket = INVALID_SOCKET_VAL;
    m_serverSocket = INVALID_SOCKET_VAL;
    m_isHost = false;
    m_isConnected = false;
    m_isJoining = false;
    m_players.clear();

    if (!m_wsaInitialized) {
        WSAStartupOnce();
        m_wsaInitialized = true;
    }

    // Per-instance identity. mixSalt=0 keeps Init() deterministic relative to (this),
    // while HostGame()/JoinGame() pass extra entropy to refresh the identity.
    GeneratePlayerId(0);
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
                bool wasConnected = m_isConnected;
                m_isConnected = (m_players.size() > 1);
                if (!m_isConnected) {
                    m_statusMessage = "Hosting LAN (UDP)...";
                }
                SendPlayerList();
                // Bug fix: notify the game-side state machine when the host
                // drops down to no peers, so is_multiplayer / lobby UI can
                // reset to a consistent state instead of staying stale.
                if (wasConnected && !m_isConnected && onConnectionEstablished) {
                    onConnectionEstablished(false);
                }
            }
        } else {
            // Client checks host timeout using a clean "last packet from host"
            // timestamp, not the keep-alive send timer (bug #51).
            if (now - m_lastHostPacketTime > 4000) {
                std::cout << "Host timed out." << std::endl;
                Shutdown();
                m_statusMessage = "Disconnected (Timeout)";
                if (onConnectionEstablished) onConnectionEstablished(false);
            }
            // --- Bug #3 Fix: Send KeepAlivePacket periodically from client ---
            else if (now - m_lastKeepAliveSendTime > 1000) { // Send keep-alive every 1 second
                KeepAlivePacket alivePkt;
                alivePkt.type = 9;
                alivePkt.protocolVersion = CURRENT_PROTOCOL_VERSION;
                SendPacket(&alivePkt, sizeof(alivePkt));
                m_lastKeepAliveSendTime = now; // Reset timer after sending
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
    if (m_wsaInitialized) {
        WSACleanupOnce();
        m_wsaInitialized = false;
    }
}

void LanManager::HostGame() {
    m_isHost = true;
    m_isConnected = false;
    m_statusMessage = "Hosting LAN (UDP)...";
    m_players.clear();

    GeneratePlayerId(0);
    // Regenerate name to match the new ID. Without this, a fresh HostGame()
    // call after a previous JoinGame (or vice versa) could broadcast a name
    // that doesn't correspond to m_myPlayerId, breaking lobby identity.
    m_myPlayerName = "Player_" + std::to_string(m_myPlayerId);
    AddPlayer(m_myPlayerId, m_myPlayerName.c_str(), true); // Add host as first player
    
    if (m_serverSocket != INVALID_SOCKET_VAL) {
        CLOSE_SOCKET((socket_t)m_serverSocket);
        m_serverSocket = INVALID_SOCKET_VAL;
    }
    
    socket_t sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == INVALID_SOCKET_VAL) {
        // Bug fix: socket() failed — roll back the optimistic state set above
        // so the manager isn't left claiming "host" with no underlying socket.
        m_isHost = false;
        m_isConnected = false;
        m_players.clear();
        m_statusMessage = "Failed to create socket";
        return;
    }

    int opt = 1;
    setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));

    sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(LAN_PORT);

    if (bind(sock, (struct sockaddr*)&addr, sizeof(addr)) == SOCKET_ERROR_VAL) {
        CLOSE_SOCKET(sock);
        // Bug fix: bind() failed — same rollback as socket() failure.
        m_isHost = false;
        m_isConnected = false;
        m_players.clear();
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

    // Distinct salt so a client that has previously hosted on the same instance
    // gets a fresh identity, while keeping ID generation in one place.
    GeneratePlayerId(0x9E3779B9u);
    
    if (m_clientSocket != INVALID_SOCKET_VAL) {
        CLOSE_SOCKET((socket_t)m_clientSocket);
        m_clientSocket = INVALID_SOCKET_VAL;
    }
    
    socket_t sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == INVALID_SOCKET_VAL) {
        // Bug fix: socket() failed — leave manager in a consistent state.
        m_statusMessage = "Failed to create socket";
        return;
    }

    memset(&m_hostAddress, 0, sizeof(m_hostAddress));
    m_hostAddress.sin_family = AF_INET;
    m_hostAddress.sin_port = htons(LAN_PORT);
    int r = inet_pton(AF_INET, addressOrId.empty() ? "127.0.0.1" : addressOrId.c_str(), &m_hostAddress.sin_addr);
    if (r <= 0) {
        CLOSE_SOCKET(sock);
        m_statusMessage = "Invalid IP Address format";
        return;
    }

    SetNonBlocking(sock);
    m_clientSocket = (size_t)sock;
    m_isJoining = true;
    m_lastJoinAttemptTime = GetTimeMs(); // Initialize join attempt timer
    // Bug #51: seed both timers; host-packet timer also resets on first join
    // attempt so the host has ~4s to respond before we time out.
    m_lastHostPacketTime = GetTimeMs();
    m_lastKeepAliveSendTime = GetTimeMs();
    // Always regenerate name from the current ID. Init() pre-populates
    // m_myPlayerName, so the previous "only-if-empty" check could leave a
    // stale name that no longer matches m_myPlayerId after GeneratePlayerId().
    m_myPlayerName = "Player_" + std::to_string(m_myPlayerId);

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
                if (!ProtocolVersionOK(buffer, r)) continue;
                PlayerJoinPacket* joinPkt = reinterpret_cast<PlayerJoinPacket*>(buffer);

                // Bug #44 fix: identity is bound to sender address, not the
                // playerId in the wire packet. First, see if this exact
                // address already has a slot (the legitimate reconnect case).
                int idx = FindPlayerByAddress(senderAddr);
                bool isFreshJoin = false;
                if (idx != -1) {
                    // Legitimate reconnect from the same peer. Trust the
                    // existing playerId — do NOT overwrite it from the wire,
                    // otherwise any peer could hijack their own slot's ID,
                    // and a separate address-spoofing attacker could not
                    // rebind here either because AddrEqual already matched.
                    m_players[idx].lastSeen = now;
                    if (!m_isConnected) {
                        m_isConnected = true;
                        if (onConnectionEstablished) onConnectionEstablished(true);
                    }
                } else {
                    // Unknown address. If the claimed playerId is already in
                    // use by a *different* address, this is a hijack attempt
                    // — drop silently and do not add or rebind.
                    // Reject playerId == 0 too: GeneratePlayerId never emits
                    // 0, so any join claiming 0 is malformed or hostile.
                    if (joinPkt->playerId == 0 ||
                        FindPlayerById(joinPkt->playerId) != -1) {
                        std::cout << "Warning: Join packet claimed invalid playerId "
                                  << joinPkt->playerId << ", dropping." << std::endl;
                        continue;
                    }
                    // Fresh peer claiming a fresh id. Accept (still rate-
                    // limited by the 4-player cap in AddPlayer).
                    if (m_players.size() < 4) {
                        AddPlayer(joinPkt->playerId, joinPkt->name, false, true, &senderAddr);
                        std::cout << "Player joined: " << joinPkt->name
                                  << " ID: " << joinPkt->playerId << std::endl;
                        idx = (int)m_players.size() - 1;
                        isFreshJoin = true; // Bug #47: only fire callback for fresh joins
                        m_isConnected = true; // Now connected to at least one client
                        if (onConnectionEstablished) onConnectionEstablished(true);
                    } else {
                        continue; // lobby full
                    }
                }
                // Bug #47 fix: clients retry Join every ~500ms, so without this
                // guard the host would fire onPlayerJoinReceived + SendPlayerList
                // on every retry — spamming callbacks, resetting UI state, and
                // racing with ready toggles.
                if (isFreshJoin) {
                    PlayerJoinPacket joinPktForCallback;
                    // Always emit the authoritative playerId (from the slot we
                    // created), not the raw wire value.
                    joinPktForCallback.playerId = m_players[idx].playerId;
                    strncpy(joinPktForCallback.name, m_players[idx].name, 31);
                    joinPktForCallback.name[31] = '\0';
                    if (onPlayerJoinReceived) {
                        onPlayerJoinReceived(joinPktForCallback);
                    }
                    m_statusMessage = "Client Connected (UDP)!";
                    SendPlayerList();
                }
                // --- End Bug #1 / #47 Fix ---

            } else {
                // Other packets must come from a registered client
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
                    if (!ProtocolVersionOK(buffer, r)) continue;
                    auto& pkt = *reinterpret_cast<PlayerStatePacket*>(buffer);
                    // Validate playerId matches the sender's registered player
                    if (pkt.playerId != m_players[idx].playerId) {
                        // PlayerId mismatch - potential spoofing, ignore packet
                        continue;
                    }
                    onPlayerStateReceived(pkt);
                } else if (type == 3 && (onCoinPickupReceived || onCoinPickupRequest) && r == sizeof(CoinPickupPacket)) {
                    if (!ProtocolVersionOK(buffer, r)) continue;
                    auto& pkt = *reinterpret_cast<CoinPickupPacket*>(buffer);
                    // Security: only the host may send isRequest=0 (authoritative
                    // broadcast). A client sending isRequest=0 is impersonating
                    // an authoritative state update and must be dropped, even
                    // though the sender is a registered peer.
                    if (!pkt.isRequest) continue;
                    pkt.playerId = m_players[idx].playerId;
                    if (onCoinPickupRequest) onCoinPickupRequest(pkt.count, pkt.playerId);
} else if (type == 4 && (onTeamUpgradeReceived || onTeamShopRequest) && r == sizeof(TeamUpgradePacket)) {
                    if (!ProtocolVersionOK(buffer, r)) continue;
                    auto& pkt = *reinterpret_cast<TeamUpgradePacket*>(buffer);
                    // Same security gate as coin pickup: only the host may
                    // produce authoritative state broadcasts. Reject forged
                    // isRequest=0 from any client.
                    if (!pkt.isRequest) continue;
                    pkt.playerId = m_players[idx].playerId;
                    if (onTeamShopRequest) onTeamShopRequest(pkt);
                        // Forward the request to other peers so host can
                        // process it from any peer path (e.g. relayed).
                        // Don't deliver as an authoritative upgrade here.
            } else if (type == 7 && onReadyStatusReceived && r == sizeof(ReadyStatusPacket)) {
                if (!ProtocolVersionOK(buffer, r)) continue;
                auto& pkt = *reinterpret_cast<ReadyStatusPacket*>(buffer);
                // Override wire playerId with the sender we authenticated by
                // address, preventing a malicious client from toggling
                // someone else's ready state.
                pkt.playerId = m_players[idx].playerId;
                // Find player by ID, not name
                int playerIndex = FindPlayerById(pkt.playerId);
                if (playerIndex != -1) {
                    m_players[playerIndex].ready = pkt.ready;
                    onReadyStatusReceived(pkt); // Pass the packet with playerId
                    SendPlayerList(); // Broadcast updated list
                    continue; // Skip the standard forward below because SendPlayerList already broadcasts
                }
            } else if (type == 9) { // KeepAlivePacket
                if (!ProtocolVersionOK(buffer, r)) continue;
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

            // Bug #51: track host packets separately from the keep-alive
            // send timer so idle lobby doesn't false-timeout.
            m_lastHostPacketTime = now;
            
            if (type == 1 && onPlayerStateReceived && r == sizeof(PlayerStatePacket)) {
                if (!ProtocolVersionOK(buffer, r)) continue;
                // Bug #50: validate the claimed playerId is one the host has
                // registered. Rejects stale state broadcasts about players we
                // never learned about (e.g. player timed out, host replayed).
                auto& statePkt = *reinterpret_cast<PlayerStatePacket*>(buffer);
                if (FindPlayerById(statePkt.playerId) == -1) continue;
                onPlayerStateReceived(statePkt);
            } else if (type == 2 && onMagmaSpawnReceived && r == sizeof(SpawnMagmaPacket)) {
                if (!ProtocolVersionOK(buffer, r)) continue;
                onMagmaSpawnReceived(*reinterpret_cast<SpawnMagmaPacket*>(buffer));
            } else if (type == 3 && onCoinPickupReceived && r == sizeof(CoinPickupPacket)) {
                if (!ProtocolVersionOK(buffer, r)) continue;
                auto& pkt = *reinterpret_cast<CoinPickupPacket*>(buffer);
                // Clients should only see authoritative broadcasts. A stray
                // request packet reaching a client (e.g. via a future relay
                // path) is meaningless to apply.
                if (pkt.isRequest) continue;
                onCoinPickupReceived(pkt.count, pkt.team_coins);
            } else if (type == 4 && onTeamUpgradeReceived && r == sizeof(TeamUpgradePacket)) {
                    if (!ProtocolVersionOK(buffer, r)) continue;
                    auto& pkt = *reinterpret_cast<TeamUpgradePacket*>(buffer);
                    // Authoritative only: drop client requests on clients.
                    if (pkt.isRequest) continue;
                    // Trust host's playerId tag (host has already authoritative
                    // sender mapping), so transaction dedup is correct per-player.
                    onTeamUpgradeReceived(pkt.upgrade_id, pkt.new_value, pkt.playerId, pkt.transaction_id);
            } else if (type == 6 && onPlayerListReceived && r == sizeof(PlayerListPacket)) {
                if (!ProtocolVersionOK(buffer, r)) continue;
                auto& pkt = *reinterpret_cast<PlayerListPacket*>(buffer);
                if (pkt.count <= 4) {
                    // Bug #49: validate lobby state shape before adopting it.
                    // Reject packets with no host, multiple hosts, duplicate
                    // IDs, or any zero playerId — these would desync lobby UI
                    // even though the packet passed size + version checks.
                    bool hasHost = false;
                    bool validShape = true;
                    for (uint8_t i = 0; i < pkt.count && validShape; ++i) {
                        const auto& pi = pkt.players[i];
                        if (pi.playerId == 0) { validShape = false; break; }
                        if (pi.isHost) {
                            if (hasHost) { validShape = false; break; }
                            hasHost = true;
                        }
                        for (uint8_t j = i + 1; j < pkt.count; ++j) {
                            if (pi.playerId == pkt.players[j].playerId) {
                                validShape = false; break;
                            }
                        }
                    }
                    if (!validShape || !hasHost) continue;

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
                if (!ProtocolVersionOK(buffer, r)) continue;
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
            PlayerJoinPacket removedPlayerData;
            removedPlayerData.playerId = m_players[index].playerId;
            strncpy(removedPlayerData.name, m_players[index].name, 31);
            removedPlayerData.name[31] = '\0';
            // isHost is not part of the wire packet
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

int LanManager::FindPlayerByAddress(const sockaddr_in& addr) {
    for (size_t i = 0; i < m_players.size(); ++i) {
        if (m_players[i].addressValid && AddrEqual(m_players[i].address, addr)) return (int)i;
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
    // For LAN, return the playerId (avoids fragile getaddrinfo/inet_ntop chain
    // that previously crashed with SIGSEGV due to invalid ai_addr/sa->sin_addr).
    return std::to_string(m_myPlayerId);
}

uint32_t LanManager::GetPlayerId() const {
    return m_myPlayerId;
}

int LanManager::GetPlayerCount() const {
    return (int)m_players.size();
}

uint32_t LanManager::GetPlayerIdAt(int slot) const {
    if (slot < 0 || slot >= (int)m_players.size()) return 0;
    return m_players[slot].playerId;
}