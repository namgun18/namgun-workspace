<script setup lang="ts">
import type { ChatMessage } from '~/composables/useChat'

const props = defineProps<{
  messages: readonly ChatMessage[]
  loading: boolean
  hasMore: boolean
  loadingMore: boolean
}>()

const emit = defineEmits<{
  'load-more': []
  'open-thread': [messageId: string]
}>()

const { user } = useAuth()
const listRef = ref<HTMLDivElement | null>(null)
let _autoScroll = true

function shouldGroup(msg: ChatMessage, prev: ChatMessage | null): boolean {
  if (!prev) return false
  if (msg.sender?.id !== prev.sender?.id) return false
  if (msg.message_type !== prev.message_type) return false
  const diff = new Date(msg.created_at).getTime() - new Date(prev.created_at).getTime()
  return diff < 60000 // 1 minute
}

function isLastInGroup(idx: number): boolean {
  const next = idx < props.messages.length - 1 ? props.messages[idx + 1] : null
  if (!next) return true
  return !shouldGroup(next, props.messages[idx])
}

function scrollToBottom() {
  nextTick(() => {
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  })
}

function onScroll() {
  if (!listRef.value) return
  const el = listRef.value
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 100
  _autoScroll = atBottom

  // Load more when scrolled to top
  if (el.scrollTop < 50 && props.hasMore && !props.loadingMore) {
    emit('load-more')
  }
}

// Auto-scroll on new messages
watch(() => props.messages.length, (newLen, oldLen) => {
  if (_autoScroll && newLen > oldLen) {
    scrollToBottom()
  }
})

watch(() => props.loading, (loading) => {
  if (!loading) scrollToBottom()
})

onMounted(scrollToBottom)
</script>

<template>
  <div ref="listRef" @scroll="onScroll" class="flex-1 overflow-y-auto px-4 py-2">
    <!-- Loading more indicator -->
    <div v-if="loadingMore" class="text-center py-2">
      <span class="text-xs text-muted-foreground">{{ $t('chat.messages.loadingMore') }}</span>
    </div>

    <!-- Loading skeleton -->
    <div v-if="loading" class="space-y-4 py-4">
      <div v-for="i in 5" :key="i" class="flex gap-3">
        <div class="w-8 h-8 rounded-full bg-muted animate-pulse shrink-0" />
        <div class="space-y-1 flex-1">
          <div class="h-3 w-24 bg-muted animate-pulse rounded" />
          <div class="h-4 w-48 bg-muted animate-pulse rounded" />
        </div>
      </div>
    </div>

    <!-- Messages -->
    <template v-else>
      <div v-for="(msg, idx) in messages" :key="msg.id">
        <ChatSystemMessage v-if="msg.message_type === 'system'" :message="msg" />
        <ChatFileMessage
          v-else-if="msg.message_type === 'file'"
          :message="msg"
          :grouped="shouldGroup(msg, idx > 0 ? messages[idx - 1] : null)"
          :is-own="msg.sender?.id === user?.id"
          :is-last-in-group="isLastInGroup(idx)"
        />
        <ChatMessage
          v-else
          :message="msg"
          :grouped="shouldGroup(msg, idx > 0 ? messages[idx - 1] : null)"
          :is-own="msg.sender?.id === user?.id"
          :is-last-in-group="isLastInGroup(idx)"
          @open-thread="emit('open-thread', $event)"
        />
      </div>

      <!-- Empty -->
      <div v-if="messages.length === 0 && !loading" class="flex items-center justify-center h-full text-sm text-muted-foreground">
        {{ $t('chat.messages.empty') }}
      </div>
    </template>
  </div>
</template>
