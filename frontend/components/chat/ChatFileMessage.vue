<script setup lang="ts">
import type { ChatMessage } from '~/composables/useChat'

const props = defineProps<{
  message: ChatMessage
  grouped: boolean
  isOwn: boolean
  isLastInGroup?: boolean
}>()

const readReceipts = computed(() => {
  if (!props.isLastInGroup) return []
  return props.message.read_by || []
})

const visibleReaders = computed(() => readReceipts.value.slice(0, 5))
const extraReaderCount = computed(() => Math.max(0, readReceipts.value.length - 5))

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

const isImage = computed(() => {
  const mime = fileMeta.value?.mime_type || ''
  if (mime.startsWith('image/')) return true
  // Fallback: check file extension
  const name = (fileMeta.value?.name || '').toLowerCase()
  return /\.(jpg|jpeg|png|webp|gif|svg)$/.test(name)
})

const isGif = computed(() => {
  const mime = fileMeta.value?.mime_type || ''
  if (mime === 'image/gif') return true
  return (fileMeta.value?.name || '').toLowerCase().endsWith('.gif')
})

const imagePreviewUrl = computed(() => {
  if (!fileMeta.value?.path) return ''
  // GIFs: use download to preserve animation (preview generates static thumbnail)
  if (isGif.value) {
    return `/api/files/download?path=${encodeURIComponent(fileMeta.value.path)}`
  }
  return `/api/files/preview?path=${encodeURIComponent(fileMeta.value.path)}`
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

        <!-- Inline image preview -->
        <div v-if="fileMeta && isImage" class="mt-1">
          <img
            :src="imagePreviewUrl"
            :alt="fileMeta.name || '이미지'"
            class="max-w-[400px] max-h-[300px] rounded-lg border cursor-pointer object-contain"
            loading="lazy"
            @click="downloadFile"
          />
          <p class="text-[10px] text-muted-foreground mt-0.5">{{ fileMeta.name }} · {{ fileSize }}</p>
        </div>

        <!-- File card (non-image) -->
        <div v-else-if="fileMeta" class="inline-flex items-center gap-2 px-3 py-2 border rounded-lg bg-accent/30 hover:bg-accent/50 cursor-pointer max-w-xs" @click="downloadFile">
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

    <!-- Reactions -->
    <div v-if="message.reactions && message.reactions.length > 0" class="ml-10 mt-0.5">
      <ChatReactions :reactions="message.reactions" :message-id="message.id" />
    </div>

    <!-- Read receipts -->
    <div v-if="visibleReaders.length > 0" class="flex justify-end mt-0.5 mr-1">
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
  </div>
</template>
