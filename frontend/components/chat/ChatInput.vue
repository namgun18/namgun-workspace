<script setup lang="ts">
import type { ChannelMember } from '~/composables/useChat'

const emit = defineEmits<{
  send: [content: string, messageType?: string, fileMeta?: string | null]
  typing: []
}>()

const { members } = useChat()

const content = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const uploading = ref(false)

// Mention autocomplete state
const showMentionDropdown = ref(false)
const mentionQuery = ref('')
const mentionStartIndex = ref(-1)
const selectedMentionIndex = ref(0)

const mentionCandidates = computed(() => {
  if (!showMentionDropdown.value) return []
  const q = mentionQuery.value.toLowerCase()
  return members.value
    .filter(m => {
      if (!q) return true
      return (m.display_name || '').toLowerCase().includes(q)
        || m.username.toLowerCase().includes(q)
    })
    .slice(0, 10)
})

function onKeydown(e: KeyboardEvent) {
  // Mention dropdown keyboard navigation
  if (showMentionDropdown.value && mentionCandidates.value.length > 0) {
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      selectedMentionIndex.value = (selectedMentionIndex.value + 1) % mentionCandidates.value.length
      return
    }
    if (e.key === 'ArrowUp') {
      e.preventDefault()
      selectedMentionIndex.value = (selectedMentionIndex.value - 1 + mentionCandidates.value.length) % mentionCandidates.value.length
      return
    }
    if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault()
      insertMention(mentionCandidates.value[selectedMentionIndex.value])
      return
    }
    if (e.key === 'Escape') {
      e.preventDefault()
      closeMentionDropdown()
      return
    }
  }

  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    submit()
  }
}

function onInput() {
  emit('typing')
  checkMention()
}

function checkMention() {
  const el = textareaRef.value
  if (!el) return

  const cursorPos = el.selectionStart
  const text = content.value.slice(0, cursorPos)

  // Find the last @ that starts a mention (preceded by whitespace or at start)
  const lastAtIndex = text.lastIndexOf('@')
  if (lastAtIndex === -1) {
    closeMentionDropdown()
    return
  }

  // @ must be at start or preceded by whitespace
  if (lastAtIndex > 0 && !/\s/.test(text[lastAtIndex - 1])) {
    closeMentionDropdown()
    return
  }

  const query = text.slice(lastAtIndex + 1)
  // If there's a space after @query, mention is complete
  if (/\s/.test(query)) {
    closeMentionDropdown()
    return
  }

  mentionStartIndex.value = lastAtIndex
  mentionQuery.value = query
  selectedMentionIndex.value = 0
  showMentionDropdown.value = true
}

function insertMention(member: ChannelMember) {
  const before = content.value.slice(0, mentionStartIndex.value)
  const after = content.value.slice(textareaRef.value?.selectionStart || mentionStartIndex.value + mentionQuery.value.length + 1)
  content.value = `${before}@${member.username} ${after}`
  closeMentionDropdown()

  // Focus and move cursor
  nextTick(() => {
    const el = textareaRef.value
    if (el) {
      const pos = before.length + member.username.length + 2 // @username + space
      el.selectionStart = pos
      el.selectionEnd = pos
      el.focus()
    }
  })
}

function closeMentionDropdown() {
  showMentionDropdown.value = false
  mentionQuery.value = ''
  mentionStartIndex.value = -1
  selectedMentionIndex.value = 0
}

function submit() {
  const text = content.value.trim()
  if (!text) return
  emit('send', text)
  content.value = ''
  closeMentionDropdown()
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
  <div class="border-t px-4 py-3 bg-background shrink-0 relative">
    <!-- Mention autocomplete dropdown -->
    <div
      v-if="showMentionDropdown && mentionCandidates.length > 0"
      class="absolute bottom-full left-4 right-4 mb-1 bg-popover border rounded-lg shadow-lg max-h-48 overflow-y-auto z-50"
    >
      <div
        v-for="(member, idx) in mentionCandidates"
        :key="member.user_id"
        @mousedown.prevent="insertMention(member)"
        class="flex items-center gap-2 px-3 py-2 cursor-pointer text-sm transition-colors"
        :class="idx === selectedMentionIndex ? 'bg-accent text-accent-foreground' : 'hover:bg-accent/50'"
      >
        <UiAvatar
          :src="member.avatar_url"
          :alt="member.display_name || member.username"
          :fallback="(member.display_name || member.username || '?').charAt(0).toUpperCase()"
          class="h-6 w-6"
        />
        <span class="font-medium">{{ member.display_name || member.username }}</span>
        <span class="text-muted-foreground text-xs">@{{ member.username }}</span>
      </div>
    </div>

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
        ref="textareaRef"
        v-model="content"
        @keydown="onKeydown"
        @input="onInput"
        placeholder="메시지 입력... (@로 멘션)"
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
