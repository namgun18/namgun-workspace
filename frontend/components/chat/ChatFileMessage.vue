<script setup lang="ts">
import type { ChatMessage } from '~/composables/useChat'

const props = defineProps<{
  message: ChatMessage
  grouped: boolean
  isOwn: boolean
}>()

const fileMeta = computed(() => {
  if (!props.message.file_meta) return null
  try {
    return JSON.parse(props.message.file_meta)
  } catch {
    return null
  }
})

const formattedTime = computed(() => {
  const d = new Date(props.message.created_at)
  return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
})

const fileSize = computed(() => {
  if (!fileMeta.value?.size) return ''
  const bytes = fileMeta.value.size
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1048576).toFixed(1)} MB`
})

function downloadFile() {
  if (!fileMeta.value?.path) return
  window.open(`/api/files/download?path=${encodeURIComponent(fileMeta.value.path)}`, '_blank')
}
</script>

<template>
  <div class="group relative px-1 py-0.5 hover:bg-accent/30 rounded transition-colors" :class="grouped ? '' : 'mt-3'">
    <div class="flex gap-2.5">
      <!-- Avatar -->
      <div v-if="!grouped" class="shrink-0 mt-0.5">
        <UiAvatar
          :src="message.sender?.avatar_url"
          :alt="message.sender?.display_name || message.sender?.username || ''"
          :fallback="(message.sender?.display_name || message.sender?.username || '?').charAt(0).toUpperCase()"
          class="h-8 w-8"
        />
      </div>
      <div v-else class="w-8 shrink-0" />

      <div class="flex-1 min-w-0">
        <div v-if="!grouped" class="flex items-baseline gap-2">
          <span class="text-sm font-semibold">{{ message.sender?.display_name || message.sender?.username }}</span>
          <span class="text-[10px] text-muted-foreground">{{ formattedTime }}</span>
        </div>

        <!-- Text content -->
        <p v-if="message.content" class="text-sm whitespace-pre-wrap break-words mb-1">{{ message.content }}</p>

        <!-- File card -->
        <div v-if="fileMeta" class="inline-flex items-center gap-2 px-3 py-2 border rounded-lg bg-accent/30 hover:bg-accent/50 cursor-pointer max-w-xs" @click="downloadFile">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5 text-muted-foreground shrink-0">
            <path d="M13 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z" /><polyline points="13 2 13 9 20 9" />
          </svg>
          <div class="min-w-0">
            <p class="text-sm font-medium truncate">{{ fileMeta.name || '파일' }}</p>
            <p v-if="fileSize" class="text-[10px] text-muted-foreground">{{ fileSize }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
