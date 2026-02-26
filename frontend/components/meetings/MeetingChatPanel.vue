<script setup lang="ts">
/**
 * Meeting-specific chat panel.
 * Uses direct $fetch instead of useChat singleton to avoid interference.
 */

const props = defineProps<{
  channelId: string
}>()

interface MeetingMsg {
  id: string
  sender: { id: string; username: string; display_name: string | null; avatar_url: string | null } | null
  content: string
  message_type: string
  created_at: string
}

const { user } = useAuth()
const messages = ref<MeetingMsg[]>([])
const newMessage = ref('')
const loading = ref(false)
const listRef = ref<HTMLDivElement | null>(null)
let pollTimer: ReturnType<typeof setInterval> | null = null

async function fetchMessages() {
  try {
    const data = await $fetch<{ messages: MeetingMsg[]; has_more: boolean }>(
      `/api/chat/channels/${props.channelId}/messages`,
      { params: { limit: 50 } }
    )
    messages.value = data.messages
  } catch (e: any) {
    console.error('MeetingChat fetch error:', e)
  }
}

async function sendMessage() {
  const content = newMessage.value.trim()
  if (!content) return
  newMessage.value = ''
  try {
    await $fetch(`/api/chat/channels/${props.channelId}/messages`, {
      method: 'POST',
      body: { content, message_type: 'text' },
    })
    await fetchMessages()
    scrollToBottom()
  } catch (e: any) {
    console.error('MeetingChat send error:', e)
  }
}

function scrollToBottom() {
  nextTick(() => {
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  })
}

function formatTime(dateStr: string) {
  const d = new Date(dateStr)
  return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    sendMessage()
  }
}

onMounted(async () => {
  loading.value = true
  await fetchMessages()
  loading.value = false
  scrollToBottom()
  // Poll for new messages (simple approach, avoids WS coupling)
  pollTimer = setInterval(fetchMessages, 3000)
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>

<template>
  <div class="flex flex-col h-full bg-background border-l w-72">
    <!-- Header -->
    <div class="px-3 py-2 border-b">
      <h4 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{{ $t('meetings.chat.title') }}</h4>
    </div>

    <!-- Messages -->
    <div ref="listRef" class="flex-1 overflow-y-auto px-2 py-1 space-y-1">
      <div v-if="loading" class="flex items-center justify-center py-4">
        <span class="text-xs text-muted-foreground">{{ $t('common.loading') }}</span>
      </div>

      <div v-for="msg in messages" :key="msg.id" class="py-0.5">
        <div v-if="msg.message_type === 'system'" class="text-center">
          <span class="text-[10px] text-muted-foreground">{{ msg.content }}</span>
        </div>
        <div v-else>
          <div class="flex items-baseline gap-1">
            <span class="text-[10px] font-semibold" :class="msg.sender?.id === user?.id ? 'text-primary' : ''">
              {{ msg.sender?.display_name || msg.sender?.username || '?' }}
            </span>
            <span class="text-[9px] text-muted-foreground">{{ formatTime(msg.created_at) }}</span>
          </div>
          <p class="text-xs whitespace-pre-wrap break-words">{{ msg.content }}</p>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="border-t px-2 py-1.5">
      <div class="flex gap-1">
        <input
          v-model="newMessage"
          @keydown="onKeydown"
          :placeholder="$t('meetings.chat.placeholder')"
          class="flex-1 px-2 py-1 text-xs border rounded bg-background focus:outline-none focus:ring-1 focus:ring-ring"
        />
        <button
          @click="sendMessage"
          :disabled="!newMessage.trim()"
          class="px-2 py-1 text-xs rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {{ $t('common.send') }}
        </button>
      </div>
    </div>
  </div>
</template>
