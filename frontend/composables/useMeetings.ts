import {
  Room,
  RoomEvent,
  Track,
  VideoPresets,
  type Participant,
} from 'livekit-client'

interface RoomInfo {
  name: string
  num_participants: number
  max_participants: number
  creation_time: number
  share_token: string
  is_host: boolean
  pending_count: number
}

interface ParticipantTrack {
  identity: string
  name: string
  videoTrack: any | null
  audioTrack: any | null
  screenTrack: any | null
  isMuted: boolean
  isLocal: boolean
}

interface PendingReq {
  id: string
  nickname: string
  created_at: number
}

interface ChatMessage {
  id: string
  type: 'chat'
  sender: string
  text: string
  ts: number
  isLocal: boolean
}

export const useMeetings = () => {
  const rooms = useState<RoomInfo[]>('meetings-rooms', () => [])
  const loading = useState<boolean>('meetings-loading', () => false)
  const error = useState<string | null>('meetings-error', () => null)

  const currentRoom = useState<Room | null>('meetings-current-room', () => null)
  const currentRoomName = useState<string | null>('meetings-current-room-name', () => null)
  const isHost = useState<boolean>('meetings-is-host', () => false)
  const connected = useState<boolean>('meetings-connected', () => false)
  const participants = useState<ParticipantTrack[]>('meetings-participants', () => [])
  const cameraEnabled = useState<boolean>('meetings-camera', () => true)
  const micEnabled = useState<boolean>('meetings-mic', () => true)
  const screenShareEnabled = useState<boolean>('meetings-screen', () => false)

  // 호스트: 대기 중인 참가 신청
  const pendingRequests = useState<PendingReq[]>('meetings-pending', () => [])

  // 채팅
  const chatMessages = useState<ChatMessage[]>('meetings-chat', () => [])
  const unreadChat = useState<number>('meetings-unread-chat', () => 0)

  // ─── Room 목록 (인증 사용자) ───

  const fetchRooms = async () => {
    loading.value = true
    error.value = null
    try {
      const data = await $fetch<{ rooms: RoomInfo[] }>('/api/meetings/rooms', {
        credentials: 'include',
      })
      rooms.value = data.rooms
    } catch (e: any) {
      error.value = e?.data?.detail || '회의실 목록을 불러올 수 없습니다'
    } finally {
      loading.value = false
    }
  }

  const createRoom = async (
    name: string,
    opts?: {
      invitees?: Array<{ type: string; user_id?: string; username?: string; display_name?: string; email?: string }>
      scheduled_at?: string | null
      duration_minutes?: number
    },
  ): Promise<RoomInfo> => {
    const data = await $fetch<RoomInfo>('/api/meetings/rooms', {
      method: 'POST',
      body: {
        name,
        max_participants: 10,
        invitees: opts?.invitees || [],
        scheduled_at: opts?.scheduled_at || null,
        duration_minutes: opts?.duration_minutes || 60,
      },
      credentials: 'include',
    })
    await fetchRooms()
    return data
  }

  const deleteRoom = async (name: string) => {
    await $fetch(`/api/meetings/rooms/${encodeURIComponent(name)}`, {
      method: 'DELETE',
      credentials: 'include',
    })
    await fetchRooms()
  }

  // ─── LiveKit 연결 (공통) ───

  function buildParticipantTrack(p: Participant, isLocal: boolean): ParticipantTrack {
    let videoTrack: any = null
    let audioTrack: any = null
    let screenTrack: any = null
    let isMuted = true

    p.trackPublications.forEach((pub) => {
      if (!pub.track) return
      if (pub.source === Track.Source.Camera) videoTrack = pub.track
      else if (pub.source === Track.Source.Microphone) {
        audioTrack = pub.track
        isMuted = pub.isMuted
      } else if (pub.source === Track.Source.ScreenShare) screenTrack = pub.track
    })

    return { identity: p.identity, name: p.name || p.identity, videoTrack, audioTrack, screenTrack, isMuted, isLocal }
  }

  function refreshParticipants() {
    const room = currentRoom.value
    if (!room) { participants.value = []; return }
    const list: ParticipantTrack[] = []
    list.push(buildParticipantTrack(room.localParticipant, true))
    room.remoteParticipants.forEach((p) => list.push(buildParticipantTrack(p, false)))
    participants.value = list
  }

  // 채팅 DataChannel 설정
  function setupChat(room: Room) {
    const decoder = new TextDecoder()
    room.on(RoomEvent.DataReceived, (payload: Uint8Array, participant?: Participant) => {
      try {
        const data = JSON.parse(decoder.decode(payload))
        if (data.type === 'chat') {
          const msg: ChatMessage = {
            id: `${data.ts}-${data.sender}`,
            type: 'chat',
            sender: data.sender,
            text: data.text,
            ts: data.ts,
            isLocal: participant?.identity === room.localParticipant.identity,
          }
          chatMessages.value = [...chatMessages.value, msg]
          if (!msg.isLocal) {
            unreadChat.value++
          }
        }
      } catch { /* ignore non-chat data */ }
    })
  }

  function sendChatMessage(text: string) {
    const room = currentRoom.value
    if (!room || !text.trim()) return
    const encoder = new TextEncoder()
    const msg = {
      type: 'chat',
      sender: room.localParticipant.name || room.localParticipant.identity,
      text: text.trim(),
      ts: Date.now(),
    }
    room.localParticipant.publishData(encoder.encode(JSON.stringify(msg)), { reliable: true })
    // 로컬 메시지 즉시 추가
    chatMessages.value = [...chatMessages.value, {
      id: `${msg.ts}-local`,
      ...msg,
      isLocal: true,
    }]
  }

  function clearUnreadChat() {
    unreadChat.value = 0
  }

  interface ConnectOptions {
    cameraEnabled?: boolean
    micEnabled?: boolean
    selectedCameraId?: string
    selectedMicId?: string
  }

  async function connectToRoom(wsUrl: string, token: string, opts?: ConnectOptions) {
    const room = new Room({
      adaptiveStream: true,
      dynacast: true,
      videoCaptureDefaults: {
        resolution: VideoPresets.h1080.resolution,
        facingMode: 'user',
        ...(opts?.selectedCameraId ? { deviceId: opts.selectedCameraId } : {}),
      },
      audioCaptureDefaults: {
        ...(opts?.selectedMicId ? { deviceId: opts.selectedMicId } : {}),
      },
      publishDefaults: {
        videoEncoding: {
          maxBitrate: 4_000_000,
          maxFramerate: 30,
        },
        videoSimulcastLayers: [VideoPresets.h360, VideoPresets.h720],
        screenShareEncoding: {
          maxBitrate: 8_000_000,
          maxFramerate: 30,
        },
        videoCodec: 'vp9',
        backupCodec: { codec: 'vp8', encoding: {} },
      },
    })

    room.on(RoomEvent.TrackSubscribed, () => refreshParticipants())
    room.on(RoomEvent.TrackUnsubscribed, () => refreshParticipants())
    room.on(RoomEvent.TrackMuted, () => refreshParticipants())
    room.on(RoomEvent.TrackUnmuted, () => refreshParticipants())
    room.on(RoomEvent.ParticipantConnected, () => refreshParticipants())
    room.on(RoomEvent.ParticipantDisconnected, () => refreshParticipants())
    room.on(RoomEvent.LocalTrackPublished, () => refreshParticipants())
    room.on(RoomEvent.LocalTrackUnpublished, () => refreshParticipants())
    room.on(RoomEvent.Disconnected, () => {
      connected.value = false
      currentRoom.value = null
      currentRoomName.value = null
      participants.value = []
    })

    setupChat(room)

    await room.connect(wsUrl, token)

    currentRoom.value = room as any
    connected.value = true

    // 장치 테스트에서 선택한 on/off 상태 반영
    const wantCamera = opts?.cameraEnabled ?? true
    const wantMic = opts?.micEnabled ?? true

    if (wantCamera || wantMic) {
      try {
        if (wantCamera && wantMic) {
          await room.localParticipant.enableCameraAndMicrophone()
        } else if (wantCamera) {
          await room.localParticipant.setCameraEnabled(true)
        } else {
          await room.localParticipant.setMicrophoneEnabled(true)
        }
        cameraEnabled.value = wantCamera
        micEnabled.value = wantMic
        // 한쪽만 켜야 하는 경우 나머지 끄기
        if (wantCamera && !wantMic) {
          await room.localParticipant.setMicrophoneEnabled(false)
          micEnabled.value = false
        } else if (!wantCamera && wantMic) {
          await room.localParticipant.setCameraEnabled(false)
          cameraEnabled.value = false
        }
      } catch {
        cameraEnabled.value = false
        micEnabled.value = false
      }
    } else {
      cameraEnabled.value = false
      micEnabled.value = false
    }

    screenShareEnabled.value = false
    refreshParticipants()
  }

  // ─── 인증 사용자 참여 ───

  const getToken = async (roomName: string) => {
    return await $fetch<{ token: string; livekit_url: string }>(
      '/api/meetings/token',
      { method: 'POST', body: { room: roomName }, credentials: 'include' }
    )
  }

  const joinRoom = async (roomName: string, opts?: ConnectOptions) => {
    const tokenData = await getToken(roomName)
    currentRoomName.value = roomName
    const roomInfo = rooms.value.find(r => r.name === roomName)
    isHost.value = roomInfo?.is_host ?? false
    await connectToRoom(tokenData.livekit_url, tokenData.token, opts)
  }

  // ─── 외부인 (토큰 직접) ───

  const joinRoomWithToken = async (wsUrl: string, token: string, roomName: string, opts?: ConnectOptions) => {
    currentRoomName.value = roomName
    isHost.value = false
    await connectToRoom(wsUrl, token, opts)
  }

  // ─── 퇴장 ───

  const leaveRoom = async () => {
    const room = currentRoom.value
    if (room) await room.disconnect()
    currentRoom.value = null
    currentRoomName.value = null
    connected.value = false
    participants.value = []
    isHost.value = false
    pendingRequests.value = []
    chatMessages.value = []
    unreadChat.value = 0
    cameraEnabled.value = true
    micEnabled.value = true
    screenShareEnabled.value = false
  }

  // ─── 미디어 토글 ───

  const toggleCamera = async () => {
    const room = currentRoom.value
    if (!room) return
    const enabled = !cameraEnabled.value
    await room.localParticipant.setCameraEnabled(enabled)
    cameraEnabled.value = enabled
    refreshParticipants()
  }

  const toggleMic = async () => {
    const room = currentRoom.value
    if (!room) return
    const enabled = !micEnabled.value
    await room.localParticipant.setMicrophoneEnabled(enabled)
    micEnabled.value = enabled
    refreshParticipants()
  }

  const toggleScreenShare = async () => {
    const room = currentRoom.value
    if (!room) return
    const enabled = !screenShareEnabled.value
    if (enabled) {
      await room.localParticipant.setScreenShareEnabled(true, {
        contentHint: 'detail',
        resolution: { width: 1920, height: 1080 },
      })
    } else {
      await room.localParticipant.setScreenShareEnabled(false)
    }
    screenShareEnabled.value = enabled
    refreshParticipants()
  }

  // ─── 호스트: 참가 신청 관리 ───

  const fetchPendingRequests = async () => {
    if (!currentRoomName.value || !isHost.value) return
    try {
      const data = await $fetch<PendingReq[]>(
        `/api/meetings/rooms/${encodeURIComponent(currentRoomName.value)}/requests`,
        { credentials: 'include' }
      )
      pendingRequests.value = data
    } catch { /* ignore */ }
  }

  const approveRequest = async (reqId: string) => {
    if (!currentRoomName.value) return
    await $fetch(
      `/api/meetings/rooms/${encodeURIComponent(currentRoomName.value)}/requests/${reqId}/approve`,
      { method: 'POST', credentials: 'include' }
    )
    await fetchPendingRequests()
  }

  const denyRequest = async (reqId: string) => {
    if (!currentRoomName.value) return
    await $fetch(
      `/api/meetings/rooms/${encodeURIComponent(currentRoomName.value)}/requests/${reqId}/deny`,
      { method: 'POST', credentials: 'include' }
    )
    await fetchPendingRequests()
  }

  return {
    rooms, loading, error,
    currentRoom, currentRoomName, isHost, connected,
    participants, cameraEnabled, micEnabled, screenShareEnabled,
    pendingRequests,
    chatMessages, unreadChat,
    fetchRooms, createRoom, deleteRoom,
    getToken, joinRoom, joinRoomWithToken, leaveRoom,
    toggleCamera, toggleMic, toggleScreenShare,
    sendChatMessage, clearUnreadChat,
    fetchPendingRequests, approveRequest, denyRequest,
  }
}
