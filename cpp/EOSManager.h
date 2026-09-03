#ifndef EOS_MANAGER_H
#define EOS_MANAGER_H

#include "NetworkProvider.h"
#include "eos_sdk.h"
#include "eos_p2p.h"
#include "eos_connect.h"
#include "eos_common.h"

class EOSManager : public NetworkProvider {
public:
    static EOSManager& Get();

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
    EOSManager() = default;
    ~EOSManager() = default;

    EOS_HPlatform m_platform = nullptr;
    EOS_HConnect m_connect = nullptr;
    EOS_HP2P m_p2p = nullptr;

    EOS_ProductUserId m_localPUID = nullptr;
    EOS_ProductUserId m_remotePUID = nullptr;
    EOS_P2P_SocketId m_socketId;

    bool m_isHost = false;
    bool m_isConnected = false;
    std::string m_statusMessage = "Offline";
    EOS_NotificationId m_connectionNotificationId = EOS_INVALID_NOTIFICATIONID;
    EOS_NotificationId m_connectionEstablishedNotificationId = EOS_INVALID_NOTIFICATIONID;
    EOS_NotificationId m_connectionClosedNotificationId = EOS_INVALID_NOTIFICATIONID;

    bool m_isJoining = false;
    uint64_t m_lastJoinAttemptTime = 0;

    void LoginSuccess(EOS_ProductUserId localUserId);

    // Connect callbacks
    static void EOS_CALL OnCreateDeviceIdCallback(const EOS_Connect_CreateDeviceIdCallbackInfo* Data);
    static void EOS_CALL OnLoginCallback(const EOS_Connect_LoginCallbackInfo* Data);
    static void EOS_CALL OnCreateUserCallback(const EOS_Connect_CreateUserCallbackInfo* Data);

    // P2P callbacks
    static void EOS_CALL OnIncomingConnectionRequest(const EOS_P2P_OnIncomingConnectionRequestInfo* Data);
    static void EOS_CALL OnConnectionEstablishedCallback(const EOS_P2P_OnPeerConnectionEstablishedInfo* Data);
    static void EOS_CALL OnConnectionClosedCallback(const EOS_P2P_OnRemoteConnectionClosedInfo* Data);
    
    void ReceivePackets();
};

#endif // EOS_MANAGER_H
