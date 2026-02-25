<script setup lang="ts">
const props = defineProps<{
  activeTab: 'participants' | 'waitingRoom' | 'chat'
}>()

const emit = defineEmits<{
  'update:activeTab': [tab: 'participants' | 'waitingRoom' | 'chat']
  close: []
}>()

const {
  participants,
  isHost,
  pendingRequests,
  chatMessages,
  unreadChat,
  fetchPendingRequests,
  approveRequest,
  denyRequest,
  sendChatMessage,
  clearUnreadChat,
} = useMeetings()

const chatInput = ref('')
const chatListEl = ref<HTMLDivElement | null>(null)

// 3초 폴링 (대기실)
let pollTimer: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  if (isHost.value) {
    fetchPendingRequests()
    pollTimer = setInterval(fetchPendingRequests, 3000)
  }
})

onBeforeUnmount(() => {
  if (pollTimer) clearInterval(pollTimer)
})

// 탭 변경 시 읽음 처리
watch(() => props.activeTab, (tab) => {
  if (tab === 'chat') clearUnreadChat()
})

// 채팅 자동 스크롤
watch(chatMessages, () => {
  nextTick(() => {
    if (chatListEl.value) {
      chatListEl.value.scrollTop = chatListEl.value.scrollHeight
    }
  })
}, { deep: true })

function handleSendChat() {
  if (!chatInput.value.trim()) return
  sendChatMessage(chatInput.value)
  chatInput.value = ''
}

function formatTime(ts: number): string {
  const d = new Date(ts)
  return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
}

function setTab(tab: 'participants' | 'waitingRoom' | 'chat') {
  emit('update:activeTab', tab)
}
</script>

<template>
  <div class="flex flex-col h-full w-72 border-l bg-background shrink-0">
    <!-- 탭 헤더 -->
    <div class="flex border-b shrink-0">
      <button
        @click="setTab('participants')"
        class="flex-1 py-2.5 text-xs font-medium text-center transition-colors border-b-2"
        :class="activeTab === 'participants' ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'"
      >
        참여자 ({{ participants.length }})
      </button>
      <button
        @click="setTab('waitingRoom')"
        class="flex-1 py-2.5 text-xs font-medium text-center transition-colors border-b-2 relative"
        :class="activeTab === 'waitingRoom' ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'"
      >
        대기실
        <span
          v-if="pendingRequests.length > 0"
          class="absolute top-1.5 ml-0.5 inline-flex items-center justify-center h-4 min-w-[1rem] px-1 text-[10px] font-bold rounded-full bg-orange-500 text-white"
        >
          {{ pendingRequests.length }}
        </span>
      </button>
      <button
        @click="setTab('chat')"
        class="flex-1 py-2.5 text-xs font-medium text-center transition-colors border-b-2 relative"
        :class="activeTab === 'chat' ? 'border-primary text-foreground' : 'border-transparent text-muted-foreground hover:text-foreground'"
      >
        채팅
        <span
          v-if="unreadChat > 0 && activeTab !== 'chat'"
          class="absolute top-1.5 ml-0.5 inline-flex items-center justify-center h-4 min-w-[1rem] px-1 text-[10px] font-bold rounded-full bg-blue-500 text-white"
        >
          {{ unreadChat > 99 ? '99+' : unreadChat }}
        </span>
      </button>
      <button
        @click="emit('close')"
        class="px-2 text-muted-foreground hover:text-foreground transition-colors"
        title="닫기"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
          <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>

    <!-- 참여자 탭 -->
    <div v-if="activeTab === 'participants'" class="flex-1 overflow-y-auto">
      <div class="divide-y">
        <div
          v-for="p in participants"
          :key="p.identity"
          class="flex items-center gap-3 px-3 py-2.5"
        >
          <div class="h-8 w-8 rounded-full bg-primary/15 flex items-center justify-center text-sm font-semibold text-primary shrink-0">
            {{ p.name.charAt(0).toUpperCase() }}
          </div>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-medium truncate">
              {{ p.name }}
              <span v-if="p.isLocal" class="text-muted-foreground font-normal"> (나)</span>
            </p>
          </div>
          <div class="shrink-0">
            <svg
              v-if="p.isMuted"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="h-4 w-4 text-red-400"
            >
              <line x1="1" y1="1" x2="23" y2="23" />
              <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6" />
              <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2c0 .76-.12 1.5-.34 2.18" />
              <line x1="12" y1="19" x2="12" y2="23" /><line x1="8" y1="23" x2="16" y2="23" />
            </svg>
            <svg
              v-else
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="h-4 w-4 text-green-500"
            >
              <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" y1="19" x2="12" y2="22" />
            </svg>
          </div>
        </div>
      </div>
    </div>

    <!-- 대기실 탭 -->
    <div v-else-if="activeTab === 'waitingRoom'" class="flex-1 overflow-y-auto">
      <template v-if="isHost">
        <div v-if="pendingRequests.length === 0" class="px-4 py-8 text-center text-sm text-muted-foreground">
          대기 중인 참가자가 없습니다
        </div>
        <div v-else class="divide-y">
          <div
            v-for="req in pendingRequests"
            :key="req.id"
            class="flex items-center justify-between px-3 py-2.5"
          >
            <div class="min-w-0 flex-1">
              <p class="text-sm font-medium truncate">{{ req.nickname }}</p>
              <p class="text-[11px] text-muted-foreground">참가 요청</p>
            </div>
            <div class="flex gap-1 shrink-0 ml-2">
              <button
                @click="approveRequest(req.id)"
                class="px-2.5 py-1 text-xs font-medium rounded bg-green-600 text-white hover:bg-green-700 transition-colors"
              >
                수락
              </button>
              <button
                @click="denyRequest(req.id)"
                class="px-2.5 py-1 text-xs font-medium rounded border text-destructive hover:bg-destructive/10 transition-colors"
              >
                거절
              </button>
            </div>
          </div>
        </div>
      </template>
      <div v-else class="px-4 py-8 text-center text-sm text-muted-foreground">
        호스트만 대기실을 관리할 수 있습니다
      </div>
    </div>

    <!-- 채팅 탭 -->
    <template v-else-if="activeTab === 'chat'">
      <div ref="chatListEl" class="flex-1 overflow-y-auto px-3 py-2 space-y-3">
        <div v-if="chatMessages.length === 0" class="text-center text-sm text-muted-foreground py-8">
          메시지가 없습니다
        </div>
        <div
          v-for="msg in chatMessages"
          :key="msg.id"
          class="group"
        >
          <div class="flex items-baseline gap-1.5">
            <span class="text-xs font-semibold" :class="msg.isLocal ? 'text-primary' : 'text-foreground'">
              {{ msg.sender }}
            </span>
            <span class="text-[10px] text-muted-foreground">{{ formatTime(msg.ts) }}</span>
          </div>
          <p class="text-sm mt-0.5 break-words">{{ msg.text }}</p>
        </div>
      </div>

      <!-- 채팅 입력 -->
      <div class="border-t px-3 py-2 shrink-0">
        <form @submit.prevent="handleSendChat" class="flex gap-2">
          <input
            v-model="chatInput"
            type="text"
            placeholder="메시지 입력..."
            maxlength="500"
            class="flex-1 text-sm px-3 py-1.5 rounded-md border bg-background focus:outline-none focus:ring-2 focus:ring-ring"
          />
          <button
            type="submit"
            :disabled="!chatInput.trim()"
            class="px-3 py-1.5 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            전송
          </button>
        </form>
      </div>
    </template>
  </div>
</template>
