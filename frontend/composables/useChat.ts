/**
 * Chat composable — WebSocket client + state management.
 * Follows useMail.ts singleton pattern.
 */

export interface Channel {
  id: string
  name: string
  type: 'public' | 'private' | 'dm'
  description: string | null
  created_by: string
  is_archived: boolean
  created_at: string
  updated_at: string
  member_count: number
  unread_count: number
}

export interface MessageSender {
  id: string
  username: string
  display_name: string | null
  avatar_url: string | null
}

export interface ReadByUser {
  id: string
  username: string
  display_name: string | null
  avatar_url: string | null
}

export interface ChatMessage {
  id: string
  channel_id: string
  sender: MessageSender | null
  content: string
  message_type: 'text' | 'file' | 'system'
  file_meta: string | null
  is_edited: boolean
  is_deleted: boolean
  created_at: string
  updated_at: string
  read_by?: ReadByUser[]
}

export interface ChannelMember {
  user_id: string
  username: string
  display_name: string | null
  avatar_url: string | null
  role: string
  is_online: boolean
}

export interface TypingUser {
  user_id: string
  username: string
  timeout: ReturnType<typeof setTimeout>
}

export interface WorkspaceUser {
  id: string
  username: string
  display_name: string | null
  avatar_url: string | null
}

// Module-level singleton state
const channels = ref<Channel[]>([])
const selectedChannelId = ref<string | null>(null)
const messages = ref<ChatMessage[]>([])
const members = ref<ChannelMember[]>([])
const loadingChannels = ref(false)
const loadingMessages = ref(false)
const hasMoreMessages = ref(false)
const loadingMore = ref(false)
const wsConnected = ref(false)
const onlineUsers = ref<Set<string>>(new Set())
const typingUsers = ref<Map<string, TypingUser>>(new Map())
const showMemberPanel = ref(false)
const allUsers = ref<WorkspaceUser[]>([])

let _ws: WebSocket | null = null
let _reconnectTimer: ReturnType<typeof setTimeout> | null = null
let _reconnectDelay = 1000
let _pingInterval: ReturnType<typeof setInterval> | null = null
let _typingThrottleTimer: ReturnType<typeof setTimeout> | null = null
let _initialized = false

export function useChat() {
  const { user } = useAuth()
  const config = useRuntimeConfig()
  const isDemo = config.public.demoMode

  // ─── Computed ───

  const selectedChannel = computed(() =>
    channels.value.find(c => c.id === selectedChannelId.value) || null
  )

  const sortedChannels = computed(() => {
    const pub = channels.value.filter(c => c.type !== 'dm')
    const dms = channels.value.filter(c => c.type === 'dm')
    return { channels: pub, dms }
  })

  const totalUnread = computed(() =>
    channels.value.reduce((sum, c) => sum + c.unread_count, 0)
  )

  // ─── REST Actions ───

  async function fetchChannels() {
    loadingChannels.value = true
    try {
      const data = await $fetch<Channel[]>('/api/chat/channels')
      channels.value = data
    } catch (e: any) {
      console.error('fetchChannels error:', e)
    } finally {
      loadingChannels.value = false
    }
  }

  async function selectChannel(id: string) {
    selectedChannelId.value = id
    messages.value = []
    typingUsers.value = new Map()
    await Promise.all([fetchMessages(), fetchMembers()])
  }

  async function fetchMessages(before?: string) {
    if (!selectedChannelId.value) return
    if (before) {
      loadingMore.value = true
    } else {
      loadingMessages.value = true
    }
    try {
      const params: Record<string, any> = { limit: 50 }
      if (before) params.before = before

      const data = await $fetch<{ messages: ChatMessage[]; has_more: boolean }>(
        `/api/chat/channels/${selectedChannelId.value}/messages`,
        { params }
      )

      if (before) {
        messages.value = [...data.messages, ...messages.value]
      } else {
        messages.value = data.messages
      }
      hasMoreMessages.value = data.has_more

      // Mark last message as read
      if (!before && data.messages.length > 0) {
        const last = data.messages[data.messages.length - 1]
        markRead(selectedChannelId.value!, last.id)
        // Reset unread locally
        const ch = channels.value.find(c => c.id === selectedChannelId.value)
        if (ch) ch.unread_count = 0
      }
    } catch (e: any) {
      console.error('fetchMessages error:', e)
    } finally {
      loadingMessages.value = false
      loadingMore.value = false
    }
  }

  async function fetchMembers() {
    if (!selectedChannelId.value) return
    try {
      const data = await $fetch<ChannelMember[]>(
        `/api/chat/channels/${selectedChannelId.value}/members`
      )
      // Merge online status
      members.value = data.map(m => ({
        ...m,
        is_online: onlineUsers.value.has(m.user_id),
      }))
    } catch (e: any) {
      console.error('fetchMembers error:', e)
    }
  }

  async function createChannel(name: string, type: string, description?: string, memberIds?: string[]) {
    const result = await $fetch<{ id: string; name: string; type: string }>(
      '/api/chat/channels',
      {
        method: 'POST',
        body: { name, type, description, member_ids: memberIds || [] },
      }
    )
    await fetchChannels()
    return result
  }

  async function addMembers(channelId: string, userIds: string[]) {
    await $fetch(`/api/chat/channels/${channelId}/members`, {
      method: 'POST',
      body: { user_ids: userIds },
    })
    await fetchMembers()
  }

  async function leaveChannel(channelId: string) {
    if (!user.value) return
    await $fetch(`/api/chat/channels/${channelId}/members/${user.value.id}`, {
      method: 'DELETE',
    })
    channels.value = channels.value.filter(c => c.id !== channelId)
    if (selectedChannelId.value === channelId) {
      selectedChannelId.value = null
      messages.value = []
      members.value = []
    }
  }

  async function openDM(userId: string) {
    const result = await $fetch<{ id: string; name: string; type: string }>(
      '/api/chat/dm',
      { method: 'POST', body: { user_id: userId } }
    )
    await fetchChannels()
    await selectChannel(result.id)
  }

  async function searchUsers(query: string) {
    if (!query.trim()) return []
    return await $fetch<Array<{ id: string; username: string; display_name: string | null; avatar_url: string | null }>>(
      '/api/chat/users',
      { params: { q: query } }
    )
  }

  async function sendMessageREST(channelId: string, content: string, messageType = 'text', fileMeta?: string) {
    return await $fetch<ChatMessage>(
      `/api/chat/channels/${channelId}/messages`,
      {
        method: 'POST',
        body: { content, message_type: messageType, file_meta: fileMeta },
      }
    )
  }

  async function editMessage(messageId: string, content: string) {
    await $fetch(`/api/chat/messages/${messageId}`, {
      method: 'PATCH',
      body: { content },
    })
  }

  async function deleteMessage(messageId: string) {
    await $fetch(`/api/chat/messages/${messageId}`, {
      method: 'DELETE',
    })
    messages.value = messages.value.filter(m => m.id !== messageId)
  }

  async function fetchPresence() {
    try {
      const data = await $fetch<{ online_user_ids: string[] }>('/api/chat/presence')
      onlineUsers.value = new Set(data.online_user_ids)
    } catch (e: any) {
      console.error('fetchPresence error:', e)
    }
  }

  async function fetchAllUsers() {
    try {
      const data = await $fetch<WorkspaceUser[]>('/api/chat/users')
      allUsers.value = data
    } catch (e: any) {
      console.error('fetchAllUsers error:', e)
    }
  }

  // ─── WebSocket ───

  function connectWS() {
    if (!import.meta.client) return
    if (isDemo) return
    if (_ws && (_ws.readyState === WebSocket.OPEN || _ws.readyState === WebSocket.CONNECTING)) return

    const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const url = `${proto}//${window.location.host}/ws/chat`

    _ws = new WebSocket(url)

    _ws.onopen = () => {
      wsConnected.value = true
      _reconnectDelay = 1000
      // Start ping
      _pingInterval = setInterval(() => {
        if (_ws?.readyState === WebSocket.OPEN) {
          _ws.send(JSON.stringify({ type: 'ping' }))
        }
      }, 30000)
    }

    _ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        handleWSMessage(data)
      } catch (e) {
        console.error('WS parse error:', e)
      }
    }

    _ws.onclose = () => {
      wsConnected.value = false
      if (_pingInterval) {
        clearInterval(_pingInterval)
        _pingInterval = null
      }
      // Reconnect with exponential backoff
      _reconnectTimer = setTimeout(() => {
        _reconnectDelay = Math.min(_reconnectDelay * 2, 30000)
        connectWS()
      }, _reconnectDelay)
    }

    _ws.onerror = () => {
      // onclose will fire after onerror
    }
  }

  function disconnectWS() {
    if (_reconnectTimer) {
      clearTimeout(_reconnectTimer)
      _reconnectTimer = null
    }
    if (_pingInterval) {
      clearInterval(_pingInterval)
      _pingInterval = null
    }
    if (_ws) {
      _ws.onclose = null  // prevent reconnect
      _ws.close()
      _ws = null
    }
    wsConnected.value = false
  }

  function handleWSMessage(data: any) {
    switch (data.type) {
      case 'new_message': {
        const msg = data.message as ChatMessage
        // If in current channel, append
        if (msg.channel_id === selectedChannelId.value) {
          // Avoid duplicates
          if (!messages.value.find(m => m.id === msg.id)) {
            messages.value = [...messages.value, msg]
          }
          // Auto mark read
          markRead(msg.channel_id, msg.id)
          // Clear typing for sender
          if (msg.sender) {
            const t = typingUsers.value.get(msg.sender.id)
            if (t) {
              clearTimeout(t.timeout)
              typingUsers.value.delete(msg.sender.id)
              typingUsers.value = new Map(typingUsers.value)
            }
          }
        } else {
          // Increment unread for other channel
          const ch = channels.value.find(c => c.id === msg.channel_id)
          if (ch) ch.unread_count++
        }
        break
      }

      case 'typing': {
        const uid = data.user_id as string
        if (uid === user.value?.id) break
        if (data.channel_id !== selectedChannelId.value) break

        // Clear existing timeout
        const existing = typingUsers.value.get(uid)
        if (existing) clearTimeout(existing.timeout)

        const timeout = setTimeout(() => {
          typingUsers.value.delete(uid)
          typingUsers.value = new Map(typingUsers.value)
        }, 3000)

        typingUsers.value.set(uid, {
          user_id: uid,
          username: data.username,
          timeout,
        })
        typingUsers.value = new Map(typingUsers.value)
        break
      }

      case 'presence': {
        const uid = data.user_id as string
        if (data.status === 'online') {
          onlineUsers.value.add(uid)
        } else {
          onlineUsers.value.delete(uid)
        }
        onlineUsers.value = new Set(onlineUsers.value)
        // Update members list
        const m = members.value.find(m => m.user_id === uid)
        if (m) m.is_online = data.status === 'online'
        break
      }

      case 'message_read': {
        const readUserId = data.user_id as string
        const readMessageId = data.message_id as string
        if (data.channel_id !== selectedChannelId.value) break
        if (readUserId === user.value?.id) break

        const reader: ReadByUser = {
          id: readUserId,
          username: data.username,
          display_name: data.username,
          avatar_url: data.avatar_url || null,
        }

        // Find the read message's created_at to update all messages up to that point
        const readMsg = messages.value.find(m => m.id === readMessageId)
        if (!readMsg) break

        const readTs = readMsg.created_at
        messages.value = messages.value.map(m => {
          if (m.created_at <= readTs && m.sender?.id !== readUserId) {
            const existing = m.read_by || []
            if (!existing.find(r => r.id === readUserId)) {
              return { ...m, read_by: [...existing, reader] }
            }
          }
          return m
        })
        break
      }

      case 'notification': {
        const { handleNotificationEvent } = useNotifications()
        handleNotificationEvent(data.notification)
        break
      }

      case 'channel_update':
        // Refresh channel list
        fetchChannels()
        break

      case 'pong':
        break

      case 'error':
        console.error('WS error:', data.detail)
        break
    }
  }

  function sendMessage(content: string, messageType = 'text', fileMeta?: string | null) {
    if (!selectedChannelId.value) return
    if (_ws?.readyState === WebSocket.OPEN) {
      _ws.send(JSON.stringify({
        type: 'send_message',
        channel_id: selectedChannelId.value,
        content,
        message_type: messageType,
        file_meta: fileMeta || null,
      }))
    } else {
      // Fallback to REST
      sendMessageREST(selectedChannelId.value, content, messageType, fileMeta || undefined)
        .then((msg) => {
          if (!messages.value.find(m => m.id === msg.id)) {
            messages.value = [...messages.value, msg]
          }
        })
        .catch(e => console.error('sendMessage REST fallback error:', e))
    }
  }

  function sendTyping() {
    if (!selectedChannelId.value) return
    if (_typingThrottleTimer) return
    if (_ws?.readyState === WebSocket.OPEN) {
      _ws.send(JSON.stringify({
        type: 'typing',
        channel_id: selectedChannelId.value,
      }))
      _typingThrottleTimer = setTimeout(() => {
        _typingThrottleTimer = null
      }, 2000)
    }
  }

  function markRead(channelId: string, messageId: string) {
    if (_ws?.readyState === WebSocket.OPEN) {
      _ws.send(JSON.stringify({
        type: 'mark_read',
        channel_id: channelId,
        message_id: messageId,
      }))
    }
  }

  async function loadMore() {
    if (!hasMoreMessages.value || loadingMore.value) return
    if (messages.value.length === 0) return
    const oldest = messages.value[0]
    await fetchMessages(oldest.id)
  }

  function getDMDisplayName(channel: Channel): string {
    if (!user.value) return channel.name
    const names = channel.name.split(',')
    const otherUsername = names.find(n => n !== user.value!.username) || channel.name
    // Look up display_name from allUsers
    const otherUser = allUsers.value.find(u => u.username === otherUsername)
    return otherUser?.display_name || otherUsername
  }

  // ─── Init ───

  async function init() {
    if (_initialized) return
    _initialized = true
    const { fetchNotifications, requestBrowserPermission } = useNotifications()
    await Promise.all([fetchChannels(), fetchPresence(), fetchAllUsers(), fetchNotifications()])
    requestBrowserPermission()
    connectWS()
  }

  function cleanup() {
    _initialized = false
    disconnectWS()
  }

  return {
    // State (readonly)
    channels: readonly(channels),
    selectedChannelId: readonly(selectedChannelId),
    messages: readonly(messages),
    members: readonly(members),
    loadingChannels: readonly(loadingChannels),
    loadingMessages: readonly(loadingMessages),
    hasMoreMessages: readonly(hasMoreMessages),
    loadingMore: readonly(loadingMore),
    wsConnected: readonly(wsConnected),
    onlineUsers: readonly(onlineUsers),
    typingUsers: readonly(typingUsers),
    showMemberPanel,
    allUsers: readonly(allUsers),
    // Computed
    selectedChannel,
    sortedChannels,
    totalUnread,
    // Actions
    init,
    cleanup,
    fetchChannels,
    fetchAllUsers,
    selectChannel,
    fetchMessages,
    fetchMembers,
    createChannel,
    addMembers,
    leaveChannel,
    openDM,
    searchUsers,
    sendMessage,
    sendTyping,
    editMessage,
    deleteMessage,
    loadMore,
    getDMDisplayName,
    connectWS,
    disconnectWS,
  }
}
