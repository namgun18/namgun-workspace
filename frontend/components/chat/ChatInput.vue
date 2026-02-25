<script setup lang="ts">
const emit = defineEmits<{
  send: [content: string, messageType?: string, fileMeta?: string | null]
  typing: []
}>()

const content = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const uploading = ref(false)

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    submit()
  }
}

function onInput() {
  emit('typing')
}

function submit() {
  const text = content.value.trim()
  if (!text) return
  emit('send', text)
  content.value = ''
}

function triggerFileUpload() {
  fileInput.value?.click()
}

async function onFileSelected(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return

  uploading.value = true
  try {
    const { selectedChannelId } = useChat()
    const channelId = selectedChannelId.value
    if (!channelId) return

    const formData = new FormData()
    formData.append('file', file)

    const result = await $fetch<{ path: string; name: string; size: number }>('/api/files/upload', {
      method: 'POST',
      body: formData,
      params: { path: `shared/chat/${channelId}` },
    })

    const fileMeta = JSON.stringify({
      path: result.path,
      name: result.name,
      size: result.size,
      mime_type: file.type || null,
    })

    emit('send', file.name, 'file', fileMeta)
  } catch (err: any) {
    console.error('File upload error:', err)
  } finally {
    uploading.value = false
    if (target) target.value = ''
  }
}
</script>

<template>
  <div class="border-t px-4 py-3 bg-background shrink-0">
    <div class="flex items-end gap-2">
      <!-- File attach -->
      <button
        @click="triggerFileUpload"
        :disabled="uploading"
        class="shrink-0 inline-flex items-center justify-center h-9 w-9 rounded-md hover:bg-accent transition-colors disabled:opacity-50"
        title="파일 첨부"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
          <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48" />
        </svg>
      </button>
      <input ref="fileInput" type="file" class="hidden" @change="onFileSelected" />

      <!-- Text input -->
      <textarea
        v-model="content"
        @keydown="onKeydown"
        @input="onInput"
        placeholder="메시지 입력..."
        class="flex-1 px-3 py-2 text-sm border rounded-lg bg-background resize-none focus:outline-none focus:ring-2 focus:ring-ring min-h-[36px] max-h-[120px]"
        rows="1"
      />

      <!-- Send -->
      <button
        @click="submit"
        :disabled="!content.trim() || uploading"
        class="shrink-0 inline-flex items-center justify-center h-9 w-9 rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
        title="전송"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
          <line x1="22" y1="2" x2="11" y2="13" /><polygon points="22 2 15 22 11 13 2 9 22 2" />
        </svg>
      </button>
    </div>

    <!-- Upload progress -->
    <div v-if="uploading" class="mt-2 text-xs text-muted-foreground">
      파일 업로드 중...
    </div>
  </div>
</template>
