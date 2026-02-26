<script setup lang="ts">
import type { ChatMessage } from '~/composables/useChat'

const props = defineProps<{
  message: ChatMessage
  grouped: boolean
  isOwn: boolean
  isLastInGroup?: boolean
}>()

const emit = defineEmits<{
  'open-thread': [messageId: string]
}>()

const { deleteMessage, editMessage, toggleReaction } = useChat()
const { t } = useI18n()

const showActions = ref(false)
const editing = ref(false)
const editContent = ref('')

const readReceipts = computed(() => {
  if (!props.isLastInGroup) return []
  return props.message.read_by || []
})

const visibleReaders = computed(() => readReceipts.value.slice(0, 5))
const extraReaderCount = computed(() => Math.max(0, readReceipts.value.length - 5))

const formattedTime = computed(() => {
  const d = new Date(props.message.created_at)
  return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
})

interface ContentPart {
  type: 'text' | 'mention'
  value: string
}

const renderedContent = computed<ContentPart[]>(() => {
  const text = props.message.content
  const parts: ContentPart[] = []
  const regex = /@(\w+)/g
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push({ type: 'text', value: text.slice(lastIndex, match.index) })
    }
    parts.push({ type: 'mention', value: match[0] })
    lastIndex = regex.lastIndex
  }

  if (lastIndex < text.length) {
    parts.push({ type: 'text', value: text.slice(lastIndex) })
  }

  return parts.length > 0 ? parts : [{ type: 'text', value: text }]
})

const formattedDate = computed(() => {
  const d = new Date(props.message.created_at)
  const today = new Date()
  if (d.toDateString() === today.toDateString()) return t('common.today')
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  if (d.toDateString() === yesterday.toDateString()) return t('common.yesterday')
  return d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
})

function startEdit() {
  editContent.value = props.message.content
  editing.value = true
}

async function submitEdit() {
  if (!editContent.value.trim()) return
  try {
    await editMessage(props.message.id, editContent.value.trim())
    editing.value = false
  } catch (e: any) {
    console.error('editMessage error:', e)
  }
}

async function onDelete() {
  if (!confirm(t('chat.message.deleteConfirm'))) return
  try {
    await deleteMessage(props.message.id)
  } catch (e: any) {
    console.error('deleteMessage error:', e)
  }
}
</script>

<template>
  <div
    class="group relative px-1 py-0.5 hover:bg-accent/30 rounded transition-colors"
    :class="grouped ? '' : 'mt-3'"
    @mouseenter="showActions = true"
    @mouseleave="showActions = false"
  >
    <!-- Full message (with avatar) -->
    <div v-if="!grouped" class="flex gap-2.5">
      <!-- Avatar -->
      <div class="shrink-0 mt-0.5">
        <UiAvatar
          :src="message.sender?.avatar_url"
          :alt="message.sender?.display_name || message.sender?.username || ''"
          :fallback="(message.sender?.display_name || message.sender?.username || '?').charAt(0).toUpperCase()"
          class="h-8 w-8"
        />
      </div>

      <!-- Content -->
      <div class="flex-1 min-w-0">
        <div class="flex items-baseline gap-2">
          <span class="text-sm font-semibold">
            {{ message.sender?.display_name || message.sender?.username }}
          </span>
          <span class="text-[10px] text-muted-foreground">
            {{ formattedDate }} {{ formattedTime }}
          </span>
        </div>

        <!-- Editing -->
        <div v-if="editing" class="mt-1">
          <textarea
            v-model="editContent"
            @keydown.enter.exact.prevent="submitEdit"
            @keydown.escape="editing = false"
            class="w-full px-2 py-1 text-sm border rounded bg-background resize-none focus:outline-none focus:ring-1 focus:ring-ring"
            rows="2"
          />
          <div class="flex gap-1 mt-1">
            <button @click="submitEdit" class="text-xs px-2 py-0.5 rounded bg-primary text-primary-foreground hover:bg-primary/90">{{ $t('common.save') }}</button>
            <button @click="editing = false" class="text-xs px-2 py-0.5 rounded border hover:bg-accent">{{ $t('common.cancel') }}</button>
          </div>
        </div>

        <p v-else class="text-sm whitespace-pre-wrap break-words">
          <template v-for="(part, idx) in renderedContent" :key="idx">
            <span v-if="part.type === 'mention'" class="text-primary font-medium">{{ part.value }}</span>
            <template v-else>{{ part.value }}</template>
          </template>
          <span v-if="message.is_edited" class="text-[10px] text-muted-foreground ml-1">{{ $t('chat.message.edited') }}</span>
        </p>
      </div>
    </div>

    <!-- Grouped message (no avatar) -->
    <div v-else class="flex gap-2.5">
      <div class="w-8 shrink-0 flex items-start justify-center">
        <span class="text-[10px] text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity mt-0.5">
          {{ formattedTime }}
        </span>
      </div>
      <div class="flex-1 min-w-0">
        <div v-if="editing" class="mt-1">
          <textarea
            v-model="editContent"
            @keydown.enter.exact.prevent="submitEdit"
            @keydown.escape="editing = false"
            class="w-full px-2 py-1 text-sm border rounded bg-background resize-none focus:outline-none focus:ring-1 focus:ring-ring"
            rows="2"
          />
          <div class="flex gap-1 mt-1">
            <button @click="submitEdit" class="text-xs px-2 py-0.5 rounded bg-primary text-primary-foreground hover:bg-primary/90">{{ $t('common.save') }}</button>
            <button @click="editing = false" class="text-xs px-2 py-0.5 rounded border hover:bg-accent">{{ $t('common.cancel') }}</button>
          </div>
        </div>
        <p v-else class="text-sm whitespace-pre-wrap break-words">
          <template v-for="(part, idx) in renderedContent" :key="idx">
            <span v-if="part.type === 'mention'" class="text-primary font-medium">{{ part.value }}</span>
            <template v-else>{{ part.value }}</template>
          </template>
          <span v-if="message.is_edited" class="text-[10px] text-muted-foreground ml-1">{{ $t('chat.message.edited') }}</span>
        </p>
      </div>
    </div>

    <!-- Reactions -->
    <div v-if="message.reactions && message.reactions.length > 0" class="ml-10 mt-0.5">
      <ChatReactions :reactions="message.reactions" :message-id="message.id" />
    </div>

    <!-- Thread reply count -->
    <div v-if="message.reply_count > 0" class="ml-10 mt-0.5">
      <button
        @click="emit('open-thread', message.id)"
        class="text-xs text-primary hover:underline"
      >
        {{ message.reply_count }}{{ $t('chat.message.replies') }}
      </button>
    </div>

    <!-- Read receipts -->
    <div v-if="visibleReaders.length > 0" class="flex justify-end mt-0.5 mr-1 gap-[-2px]">
      <div class="flex -space-x-1" :title="readReceipts.map(r => r.display_name || r.username).join(', ')">
        <UiAvatar
          v-for="reader in visibleReaders"
          :key="reader.id"
          :src="reader.avatar_url"
          :alt="reader.display_name || reader.username"
          :fallback="(reader.display_name || reader.username || '?').charAt(0).toUpperCase()"
          class="h-4 w-4 ring-1 ring-background text-[8px]"
        />
        <span v-if="extraReaderCount > 0" class="inline-flex items-center justify-center h-4 min-w-4 px-0.5 rounded-full bg-muted text-[8px] text-muted-foreground ring-1 ring-background">
          +{{ extraReaderCount }}
        </span>
      </div>
    </div>

    <!-- Actions -->
    <div
      v-if="showActions && !editing"
      class="absolute -top-3 right-2 flex items-center gap-0.5 px-1 py-0.5 bg-background border rounded-md shadow-sm"
    >
      <!-- Reaction quick add -->
      <button @click="toggleReaction(message.id, '👍')" class="p-1 rounded hover:bg-accent" :title="$t('chat.message.reaction')">
        <span class="text-xs">😊</span>
      </button>
      <!-- Thread reply -->
      <button @click="emit('open-thread', message.id)" class="p-1 rounded hover:bg-accent" :title="$t('chat.message.reply')">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3 w-3">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </button>
      <!-- Edit (own only) -->
      <button v-if="isOwn" @click="startEdit" class="p-1 rounded hover:bg-accent" :title="$t('common.edit')">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3 w-3">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
        </svg>
      </button>
      <!-- Delete (own only) -->
      <button v-if="isOwn" @click="onDelete" class="p-1 rounded hover:bg-accent text-destructive" :title="$t('common.delete')">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3 w-3">
          <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
        </svg>
      </button>
    </div>
  </div>
</template>
