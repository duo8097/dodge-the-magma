#include "EOSManager.h"
#include <iostream>
#include <cstring>
#include <chrono>
#include <vector>

#define _CRT_SECURE_NO_WARNINGS

// PLACEHOLDER CREDENTIALS
static const char* EOS_PRODUCT_ID = "00000000000000000000000000000000";
static const char* EOS_SANDBOX_ID = "00000000000000000000000000000000";
static const char* EOS_DEPLOYMENT_ID = "00000000000000000000000000000000";
static const char* EOS_CLIENT_ID = "00000000000000000000000000000000";
static const char* EOS_CLIENT_SECRET = "00000000000000000000000000000000";

static uint64_t GetTimeMs() {
    auto now = std::chrono::steady_clock::now();
    return std::chrono::duration_cast<std::chrono::milliseconds>(now.time_since_epoch()).count();
}

EOSManager& EOSManager::Get() {
    static EOSManager instance;
    return instance;
}

bool EOSManager::Init() {
    EOS_InitializeOptions InitOptions = {0};
    InitOptions.ApiVersion = EOS_INITIALIZE_API_LATEST;
    InitOptions.ProductName = "DodgeTheMagma";
    InitOptions.ProductVersion = "1.0";

    if (EOS_Initialize(&InitOptions) != EOS_EResult::EOS_Success) return false;

    EOS_Platform_Options PlatformOptions = {0};
    PlatformOptions.ApiVersion = EOS_PLATFORM_OPTIONS_API_LATEST;
    PlatformOptions.ProductId = EOS_PRODUCT_ID;
    PlatformOptions.SandboxId = EOS_SANDBOX_ID;
    PlatformOptions.DeploymentId = EOS_DEPLOYMENT_ID;
    PlatformOptions.ClientCredentials.ClientId = EOS_CLIENT_ID;
    PlatformOptions.ClientCredentials.ClientSecret = EOS_CLIENT_SECRET;
    PlatformOptions.bIsServer = EOS_FALSE;

    m_platform = EOS_Platform_Create(&PlatformOptions);
    if (!m_platform) {
        EOS_Shutdown();
        return false;
    }

    m_connect = EOS_Platform_GetConnectInterface(m_platform);
    m_p2p = EOS_Platform_GetP2PInterface(m_platform);
    
    memset(&m_socketId, 0, sizeof(m_socketId));
    m_socketId.ApiVersion = EOS_P2P_SOCKETID_API_LATEST;
    strncpy(m_socketId.SocketName, "GAME_SOCKET", sizeof(m_socketId.SocketName));

    // Try to login via Device ID right away
    m_statusMessage = "Logging in...";
    EOS_Connect_CreateDeviceIdOptions CreateDevIdOpts = {0};
    CreateDevIdOpts.ApiVersion = EOS_CONNECT_CREATEDEVICEID_API_LATEST;
    CreateDevIdOpts.DeviceModel = "PC";
    EOS_Connect_CreateDeviceId(m_connect, &CreateDevIdOpts, this, OnCreateDeviceIdCallback);

    return true;
}

void EOSManager::Tick() {
    if (m_platform) {
        EOS_Platform_Tick(m_platform);

        uint64_t now = GetTimeMs();
        if (!m_isHost && m_isJoining && m_remotePUID) {
            if (now - m_lastJoinAttemptTime >= 500) {
                m_lastJoinAttemptTime = now;

                PlayerJoinPacket joinPkt;
                joinPkt.type = 5;
                joinPkt.protocolVersion = CURRENT_PROTOCOL_VERSION;
                joinPkt.playerId = GetPlayerId();
                // Use cached name (set in JoinGame) so every retry sends the
                // same identity. Previously a fresh rand() each retry produced
                // a different name for the same player — bug #41.
                std::string myName = m_myPlayerName;
                if (myName.empty()) myName = "Player_" + std::to_string(joinPkt.playerId);
                strncpy(joinPkt.name, myName.c_str(), 31);
                joinPkt.name[31] = '\0';

                SendPacket(&joinPkt, sizeof(joinPkt));
            }
        }

        if (m_isConnected) {
            ReceivePackets();
        }
    }
}

void EOSManager::Shutdown() {
    if (m_p2p) {
        if (m_connectionNotificationId != EOS_INVALID_NOTIFICATIONID) {
            EOS_P2P_RemoveNotifyPeerConnectionRequest(m_p2p, m_connectionNotificationId);
            m_connectionNotificationId = EOS_INVALID_NOTIFICATIONID;
        }
        if (m_connectionEstablishedNotificationId != EOS_INVALID_NOTIFICATIONID) {
            EOS_P2P_RemoveNotifyPeerConnectionEstablished(m_p2p, m_connectionEstablishedNotificationId);
            m_connectionEstablishedNotificationId = EOS_INVALID_NOTIFICATIONID;
        }
        if (m_connectionClosedNotificationId != EOS_INVALID_NOTIFICATIONID) {
            EOS_P2P_RemoveNotifyPeerConnectionClosed(m_p2p, m_connectionClosedNotificationId);
            m_connectionClosedNotificationId = EOS_INVALID_NOTIFICATIONID;
        }
    }
    if (m_platform) {
        EOS_Platform_Release(m_platform);
        m_platform = nullptr;
    }
    m_connect = nullptr;
    m_p2p = nullptr;
    m_localPUID = nullptr;
    m_remotePUID = nullptr;
    m_isHost = false;
    m_isConnected = false;
    m_isJoining = false;
    m_myPlayerName.clear();
    m_statusMessage = "Offline";
    EOS_Shutdown();
}

void EOSManager::LoginSuccess(EOS_ProductUserId localUserId) {
    m_localPUID = localUserId;
    m_statusMessage = "Logged In (EOS)";
    
    // Listen for connections
    EOS_P2P_AddNotifyPeerConnectionRequestOptions reqOpts = {0};
    reqOpts.ApiVersion = EOS_P2P_ADDNOTIFYPEERCONNECTIONREQUEST_API_LATEST;
    reqOpts.LocalUserId = m_localPUID;
    reqOpts.SocketId = &m_socketId;
    m_connectionNotificationId = EOS_P2P_AddNotifyPeerConnectionRequest(m_p2p, &reqOpts, this, OnIncomingConnectionRequest);
        
    EOS_P2P_AddNotifyPeerConnectionEstablishedOptions estOpts = {0};
    estOpts.ApiVersion = EOS_P2P_ADDNOTIFYPEERCONNECTIONESTABLISHED_API_LATEST;
    estOpts.LocalUserId = m_localPUID;
    estOpts.SocketId = &m_socketId;
    m_connectionEstablishedNotificationId = EOS_P2P_AddNotifyPeerConnectionEstablished(m_p2p, &estOpts, this, OnConnectionEstablishedCallback);
    
    EOS_P2P_AddNotifyPeerConnectionClosedOptions closedOpts = {0};
    closedOpts.ApiVersion = EOS_P2P_ADDNOTIFYPEERCONNECTIONCLOSED_API_LATEST;
    closedOpts.LocalUserId = m_localPUID;
    closedOpts.SocketId = &m_socketId;
    m_connectionClosedNotificationId = EOS_P2P_AddNotifyPeerConnectionClosed(m_p2p, &closedOpts, this, OnConnectionClosedCallback);
}

void EOS_CALL EOSManager::OnCreateDeviceIdCallback(const EOS_Connect_CreateDeviceIdCallbackInfo* Data) {
    EOSManager* manager = static_cast<EOSManager*>(Data->ClientData);
    if (Data->ResultCode != EOS_EResult::EOS_Success && Data->ResultCode != EOS_EResult::EOS_DuplicateNotAllowed) {
        manager->m_statusMessage = "Failed to create Device ID";
        return;
    }
    
    EOS_Connect_Credentials Credentials = {0};
    Credentials.ApiVersion = EOS_CONNECT_CREDENTIALS_API_LATEST;
    Credentials.Type = EOS_EExternalCredentialType::EOS_ECT_DEVICEID_ACCESS_TOKEN;

    EOS_Connect_LoginOptions LoginOpts = {0};
    LoginOpts.ApiVersion = EOS_CONNECT_LOGIN_API_LATEST;
    LoginOpts.Credentials = &Credentials;

    EOS_Connect_Login(manager->m_connect, &LoginOpts, manager, OnLoginCallback);
}

void EOS_CALL EOSManager::OnLoginCallback(const EOS_Connect_LoginCallbackInfo* Data) {
    EOSManager* manager = static_cast<EOSManager*>(Data->ClientData);
    if (Data->ResultCode == EOS_EResult::EOS_Success) {
        manager->LoginSuccess(Data->LocalUserId);
    } else if (Data->ResultCode == EOS_EResult::EOS_InvalidUser) {
        // Create user
        EOS_Connect_CreateUserOptions CreateUserOpts = {0};
        CreateUserOpts.ApiVersion = EOS_CONNECT_CREATEUSER_API_LATEST;
        CreateUserOpts.ContinuanceToken = Data->ContinuanceToken;
        EOS_Connect_CreateUser(manager->m_connect, &CreateUserOpts, manager, OnCreateUserCallback);
    } else {
        manager->m_statusMessage = "EOS Login Failed";
    }
}

void EOS_CALL EOSManager::OnCreateUserCallback(const EOS_Connect_CreateUserCallbackInfo* Data) {
    EOSManager* manager = static_cast<EOSManager*>(Data->ClientData);
    if (Data->ResultCode == EOS_EResult::EOS_Success) {
        manager->LoginSuccess(Data->LocalUserId);
    } else {
        manager->m_statusMessage = "Failed to create EOS User";
    }
}

void EOSManager::HostGame() {
    m_isHost = true;
    m_isConnected = false;
    m_remotePUID = nullptr;
    m_statusMessage = "Hosting... (Waiting for Client PUID)";
}

void EOSManager::JoinGame(const std::string& addressOrId) {
    if (!m_localPUID) {
        m_statusMessage = "Not Logged In (EOS)";
        return;
    }
    m_isHost = false;
    m_remotePUID = EOS_ProductUserId_FromString(addressOrId.c_str());
    if (m_remotePUID) {
        m_isJoining = true;
        m_lastJoinAttemptTime = 0;
        // Lock in the player's display name for the lifetime of this join
        // attempt. Identical to the LAN path so both transports show the same
        // identity. Reset in Shutdown().
        m_myPlayerName = "Player_" + std::to_string(GetPlayerId());
        m_statusMessage = "Joining...";
    } else {
        m_statusMessage = "Invalid PUID format";
    }
}

void EOS_CALL EOSManager::OnIncomingConnectionRequest(const EOS_P2P_OnIncomingConnectionRequestInfo* Data) {
    EOSManager* manager = static_cast<EOSManager*>(Data->ClientData);
    EOS_P2P_AcceptConnectionOptions options = {0};
    options.ApiVersion = EOS_P2P_ACCEPTCONNECTION_API_LATEST;
    options.LocalUserId = manager->m_localPUID;
    options.RemoteUserId = Data->RemoteUserId;
    options.SocketId = Data->SocketId;
    if (EOS_P2P_AcceptConnection(manager->m_p2p, &options) == EOS_EResult::EOS_Success) {
        manager->m_remotePUID = Data->RemoteUserId;
    }
}

void EOS_CALL EOSManager::OnConnectionEstablishedCallback(const EOS_P2P_OnPeerConnectionEstablishedInfo* Data) {
    EOSManager* manager = static_cast<EOSManager*>(Data->ClientData);
    manager->m_isConnected = true;
    manager->m_isJoining = false;
    manager->m_statusMessage = "Connected!";
    if (manager->onConnectionEstablished) manager->onConnectionEstablished(true);
}

void EOS_CALL EOSManager::OnConnectionClosedCallback(const EOS_P2P_OnRemoteConnectionClosedInfo* Data) {
    EOSManager* manager = static_cast<EOSManager*>(Data->ClientData);
    manager->m_isConnected = false;
    manager->m_isJoining = false;
    manager->m_statusMessage = "Disconnected";
    if (manager->onConnectionEstablished) manager->onConnectionEstablished(false);
}

void EOSManager::SendPacket(const void* data, uint32_t length) {
    if (!m_localPUID || !m_remotePUID) return;
    EOS_P2P_SendPacketOptions options = {0};
    options.ApiVersion = EOS_P2P_SENDPACKET_API_LATEST;
    options.LocalUserId = m_localPUID;
    options.RemoteUserId = m_remotePUID;
    options.SocketId = &m_socketId;
    options.Channel = 0;
    options.DataLengthBytes = length;
    options.Data = data;
    options.bAllowDelayedDelivery = EOS_FALSE;
    options.Reliability = EOS_EPacketReliability::EOS_PR_ReliableUnordered;
    options.bDisableAutoAcceptConnection = EOS_FALSE;
    
    EOS_EResult result = EOS_P2P_SendPacket(m_p2p, &options);
    if (result != EOS_EResult::EOS_Success) {
        std::cerr << "EOS_P2P_SendPacket failed: " << (int)result << std::endl;
    }
}

void EOSManager::ReceivePackets() {
    EOS_P2P_GetNextReceivedPacketSizeOptions sizeOptions = {0};
    sizeOptions.ApiVersion = EOS_P2P_GETNEXTRECEIVEDPACKETSIZE_API_LATEST;
    sizeOptions.LocalUserId = m_localPUID;
    sizeOptions.RequestedChannel = nullptr;
    
    uint32_t nextSize = 0;
    while (EOS_P2P_GetNextReceivedPacketSize(m_p2p, &sizeOptions, &nextSize) == EOS_EResult::EOS_Success) {
        std::vector<uint8_t> buffer(nextSize);
        EOS_P2P_ReceivePacketOptions recvOpts = {0};
        recvOpts.ApiVersion = EOS_P2P_RECEIVEPACKET_API_LATEST;
        recvOpts.LocalUserId = m_localPUID;
        recvOpts.MaxDataSizeBytes = nextSize;
        
        EOS_ProductUserId outPeerId = nullptr;
        EOS_P2P_SocketId outSocketId;
        uint8_t outChannel = 0;
        uint32_t outBytes = 0;
        
        if (EOS_P2P_ReceivePacket(m_p2p, &recvOpts, &outPeerId, &outSocketId, &outChannel, buffer.data(), &outBytes) == EOS_EResult::EOS_Success && outBytes > 0) {
            uint8_t type = buffer[0];
            if (outBytes >= 2 && buffer[1] != CURRENT_PROTOCOL_VERSION) {
                // All currently-versioned packet types now carry a protocolVersion
                // byte (was previously only types 1/3/4/8). Drop mismatched builds.
                continue;
            }
            if (type == 1 && onPlayerStateReceived && outBytes == sizeof(PlayerStatePacket)) {
                onPlayerStateReceived(*reinterpret_cast<PlayerStatePacket*>(buffer.data()));
            } else if (type == 2 && onMagmaSpawnReceived && outBytes == sizeof(SpawnMagmaPacket)) {
                onMagmaSpawnReceived(*reinterpret_cast<SpawnMagmaPacket*>(buffer.data()));
            } else if (type == 3 && onCoinPickupReceived && outBytes == sizeof(CoinPickupPacket)) {
                auto& pkt = *reinterpret_cast<CoinPickupPacket*>(buffer.data());
                onCoinPickupReceived(pkt.count, pkt.team_coins);
            } else if (type == 4 && onTeamUpgradeReceived && outBytes == sizeof(TeamUpgradePacket)) {
                auto& pkt = *reinterpret_cast<TeamUpgradePacket*>(buffer.data());
                onTeamUpgradeReceived(pkt.upgrade_id, pkt.new_value, pkt.playerId, pkt.transaction_id);
            } else if (type == 5 && onPlayerJoinReceived && outBytes == sizeof(PlayerJoinPacket)) {
                onPlayerJoinReceived(*reinterpret_cast<PlayerJoinPacket*>(buffer.data()));
            } else if (type == 6 && onPlayerListReceived && outBytes == sizeof(PlayerListPacket)) {
                onPlayerListReceived(*reinterpret_cast<PlayerListPacket*>(buffer.data()));
            } else if (type == 7 && onReadyStatusReceived && outBytes == sizeof(ReadyStatusPacket)) {
                onReadyStatusReceived(*reinterpret_cast<ReadyStatusPacket*>(buffer.data()));
            } else if (type == 8 && onStartGameReceived && outBytes == sizeof(StartGamePacket)) {
                onStartGameReceived(*reinterpret_cast<StartGamePacket*>(buffer.data()));
            }
        }
    }
}

std::string EOSManager::GetMyId() const {
    if (!m_localPUID) return "";
    char buffer[256];
    int32_t len = sizeof(buffer);
    EOS_ProductUserId_ToString(m_localPUID, buffer, &len);
    return std::string(buffer);
}

uint32_t EOSManager::GetPlayerId() const {
    if (!m_localPUID) return 0;
    // Hash the PUID to a 32-bit ID for use in packet fields
    char buffer[256];
    int32_t len = sizeof(buffer);
    if (EOS_ProductUserId_ToString(m_localPUID, buffer, &len) != EOS_EResult::EOS_Success) return 0;
    uint32_t hash = 0;
    for (int32_t i = 0; i < len; ++i) {
        hash = hash * 31 + (uint8_t)buffer[i];
    }
    return hash;
}