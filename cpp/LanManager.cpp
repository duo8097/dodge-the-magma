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
    
    // Send a dummy heartbeat/join packet so the host knows our address
    uint8_t joinPacket[1] = {99};
    send(sock, (const char*)joinPacket, 1, 0);
    
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
        // We received a packet! We can now "connect" the server socket to this client
        // so we can just use send() instead of sendto().
        connect(server, (struct sockaddr*)&clientAddr, clientLen);
        
        m_isConnected = true;
        m_statusMessage = "Client Connected (UDP)!";
        if (onConnectionEstablished) onConnectionEstablished(true);
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
        }
    }
}

std::string LanManager::GetMyId() const {
    return "127.0.0.1"; // Stub for UI
}
