<script setup lang="ts">
import type { ChatMessage } from '~/composables/useChat'

const props = defineProps<{
  message: ChatMessage
  grouped: boolean
  isOwn: boolean
}>()

const { deleteMessage, editMessage } = useChat()

const showActions = ref(false)
const editing = ref(false)
const editContent = ref('')

const formattedTime = computed(() => {
  const d = new Date(props.message.created_at)
  return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
})

const formattedDate = computed(() => {
  const d = new Date(props.message.created_at)
  const today = new Date()
  if (d.toDateString() === today.toDateString()) return '오늘'
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)
  if (d.toDateString() === yesterday.toDateString()) return '어제'
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
  if (!confirm('메시지를 삭제하시겠습니까?')) return
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
            <button @click="submitEdit" class="text-xs px-2 py-0.5 rounded bg-primary text-primary-foreground hover:bg-primary/90">저장</button>
            <button @click="editing = false" class="text-xs px-2 py-0.5 rounded border hover:bg-accent">취소</button>
          </div>
        </div>

        <p v-else class="text-sm whitespace-pre-wrap break-words">
          {{ message.content }}
          <span v-if="message.is_edited" class="text-[10px] text-muted-foreground ml-1">(수정됨)</span>
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
            <button @click="submitEdit" class="text-xs px-2 py-0.5 rounded bg-primary text-primary-foreground hover:bg-primary/90">저장</button>
            <button @click="editing = false" class="text-xs px-2 py-0.5 rounded border hover:bg-accent">취소</button>
          </div>
        </div>
        <p v-else class="text-sm whitespace-pre-wrap break-words">
          {{ message.content }}
          <span v-if="message.is_edited" class="text-[10px] text-muted-foreground ml-1">(수정됨)</span>
        </p>
      </div>
    </div>

    <!-- Actions (own messages only) -->
    <div
      v-if="showActions && isOwn && !editing"
      class="absolute -top-3 right-2 flex items-center gap-0.5 px-1 py-0.5 bg-background border rounded-md shadow-sm"
    >
      <button @click="startEdit" class="p-1 rounded hover:bg-accent" title="수정">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3 w-3">
          <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
        </svg>
      </button>
      <button @click="onDelete" class="p-1 rounded hover:bg-accent text-destructive" title="삭제">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3 w-3">
          <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
        </svg>
      </button>
    </div>
  </div>
</template>
