<script setup lang="ts">
const {
  activeThreadId,
  threadMessages,
  threadParent,
  loadingThread,
  closeThread,
  sendThreadReply,
  toggleReaction,
} = useChat()
const { user } = useAuth()

const replyContent = ref('')

function onSendReply() {
  const content = replyContent.value.trim()
  if (!content || !activeThreadId.value) return
  sendThreadReply(content, activeThreadId.value)
  replyContent.value = ''
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    onSendReply()
  }
}

const formattedTime = (dateStr: string) => {
  const d = new Date(dateStr)
  return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
}
</script>

<template>
  <div class="w-80 border-l h-full flex flex-col bg-background shrink-0">
    <!-- Header -->
    <div class="flex items-center justify-between px-3 py-2.5 border-b">
      <h4 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{{ $t('chat.thread.title') }}</h4>
      <button @click="closeThread" class="h-6 w-6 flex items-center justify-center rounded hover:bg-accent" :aria-label="$t('common.close')">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-3 w-3">
          <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>

    <!-- Parent message -->
    <div v-if="threadParent" class="px-3 py-2 border-b bg-accent/20">
      <div class="flex items-center gap-2 mb-1">
        <UiAvatar
          :src="threadParent.sender?.avatar_url"
          :alt="threadParent.sender?.display_name || threadParent.sender?.username || ''"
          :fallback="(threadParent.sender?.display_name || threadParent.sender?.username || '?').charAt(0).toUpperCase()"
          class="h-6 w-6"
        />
        <span class="text-xs font-semibold">{{ threadParent.sender?.display_name || threadParent.sender?.username }}</span>
        <span class="text-[10px] text-muted-foreground">{{ formattedTime(threadParent.created_at) }}</span>
      </div>
      <p class="text-xs text-muted-foreground line-clamp-3 whitespace-pre-wrap">{{ threadParent.content }}</p>
    </div>

    <!-- Thread replies -->
    <div class="flex-1 overflow-y-auto px-3 py-2 space-y-2">
      <div v-if="loadingThread" class="flex items-center justify-center py-4">
        <span class="text-xs text-muted-foreground">{{ $t('common.loading') }}</span>
      </div>

      <div v-else-if="threadMessages.length === 0" class="flex items-center justify-center py-4">
        <span class="text-xs text-muted-foreground">{{ $t('chat.thread.empty') }}</span>
      </div>

      <div v-for="msg in threadMessages" :key="msg.id" class="group">
        <div class="flex gap-2">
          <UiAvatar
            :src="msg.sender?.avatar_url"
            :alt="msg.sender?.display_name || msg.sender?.username || ''"
            :fallback="(msg.sender?.display_name || msg.sender?.username || '?').charAt(0).toUpperCase()"
            class="h-6 w-6 shrink-0 mt-0.5"
          />
          <div class="flex-1 min-w-0">
            <div class="flex items-baseline gap-1.5">
              <span class="text-xs font-semibold">{{ msg.sender?.display_name || msg.sender?.username }}</span>
              <span class="text-[9px] text-muted-foreground">{{ formattedTime(msg.created_at) }}</span>
            </div>
            <p class="text-xs whitespace-pre-wrap break-words">{{ msg.content }}</p>
            <!-- Reactions -->
            <ChatReactions
              v-if="msg.reactions && msg.reactions.length > 0"
              :reactions="msg.reactions"
              :message-id="msg.id"
              size="sm"
            />
          </div>
        </div>
      </div>
    </div>

    <!-- Reply input -->
    <div class="border-t px-3 py-2">
      <textarea
        v-model="replyContent"
        @keydown="onKeydown"
        :placeholder="$t('chat.thread.replyPlaceholder')"
        class="w-full px-2 py-1.5 text-xs border rounded bg-background resize-none focus:outline-none focus:ring-1 focus:ring-ring"
        rows="2"
      />
      <div class="flex justify-end mt-1">
        <button
          @click="onSendReply"
          :disabled="!replyContent.trim()"
          class="px-2 py-1 text-xs rounded bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {{ $t('common.send') }}
        </button>
      </div>
    </div>
  </div>
</template>
