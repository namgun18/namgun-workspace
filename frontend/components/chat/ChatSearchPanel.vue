<script setup lang="ts">
const {
  searchQuery,
  searchResults,
  searchLoading,
  showSearchPanel,
  searchMessages,
  selectChannel,
} = useChat()

const inputRef = ref<HTMLInputElement | null>(null)
let debounceTimer: ReturnType<typeof setTimeout> | null = null

function onInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    if (searchQuery.value.trim().length >= 1) {
      searchMessages(searchQuery.value.trim())
    }
  }, 300)
}

function onResultClick(result: any) {
  selectChannel(result.channel_id)
  showSearchPanel.value = false
  searchQuery.value = ''
}

function formatTime(dateStr: string) {
  const d = new Date(dateStr)
  const now = new Date()
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })
}

function channelIcon(type: string) {
  if (type === 'dm') return 'user'
  if (type === 'private') return 'lock'
  return 'hash'
}

onMounted(() => {
  nextTick(() => inputRef.value?.focus())
})
</script>

<template>
  <div class="w-80 border-l h-full flex flex-col bg-background shrink-0">
    <!-- Header -->
    <div class="flex items-center justify-between px-3 py-2.5 border-b">
      <h4 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{{ $t('chat.search.title') }}</h4>
      <button @click="showSearchPanel = false" class="h-6 w-6 flex items-center justify-center rounded hover:bg-accent" :aria-label="$t('common.close')">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-3 w-3">
          <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>

    <!-- Search input -->
    <div class="px-3 py-2 border-b">
      <div class="relative">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="absolute left-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground">
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <input
          ref="inputRef"
          v-model="searchQuery"
          @input="onInput"
          :placeholder="$t('chat.search.placeholder')"
          class="w-full pl-7 pr-2 py-1.5 text-xs border rounded bg-background focus:outline-none focus:ring-1 focus:ring-ring"
        />
      </div>
    </div>

    <!-- Results -->
    <div class="flex-1 overflow-y-auto">
      <div v-if="searchLoading" class="flex items-center justify-center py-4">
        <span class="text-xs text-muted-foreground">{{ $t('chat.search.loading') }}</span>
      </div>

      <div v-else-if="searchResults.length === 0 && searchQuery.trim()" class="flex items-center justify-center py-4">
        <span class="text-xs text-muted-foreground">{{ $t('chat.search.noResults') }}</span>
      </div>

      <button
        v-for="result in searchResults"
        :key="result.id"
        @click="onResultClick(result)"
        class="w-full text-left px-3 py-2 hover:bg-accent/50 transition-colors border-b border-border/50"
      >
        <!-- Channel info -->
        <div class="flex items-center gap-1 mb-0.5">
          <span class="text-muted-foreground">
            <svg v-if="channelIcon(result.channel_type) === 'hash'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-2.5 w-2.5">
              <line x1="4" y1="9" x2="20" y2="9" /><line x1="4" y1="15" x2="20" y2="15" /><line x1="10" y1="3" x2="8" y2="21" /><line x1="16" y1="3" x2="14" y2="21" />
            </svg>
            <svg v-else-if="channelIcon(result.channel_type) === 'lock'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-2.5 w-2.5">
              <rect x="3" y="11" width="18" height="11" rx="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-2.5 w-2.5">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
            </svg>
          </span>
          <span class="text-[10px] text-muted-foreground font-medium">{{ result.channel_name }}</span>
          <span class="text-[10px] text-muted-foreground ml-auto">{{ formatTime(result.created_at) }}</span>
        </div>
        <!-- Sender + content -->
        <div class="flex items-start gap-1.5">
          <span class="text-[10px] text-muted-foreground shrink-0">{{ result.sender?.display_name || result.sender?.username || $t('chat.search.system') }}:</span>
          <p class="text-xs line-clamp-2 break-words">{{ result.content }}</p>
        </div>
      </button>
    </div>
  </div>
</template>
