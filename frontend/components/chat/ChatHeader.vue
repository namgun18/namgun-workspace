<script setup lang="ts">
const { selectedChannel, showMemberPanel, showSearchPanel, members } = useChat()

const memberCount = computed(() => selectedChannel.value?.member_count || members.value.length)

const displayName = computed(() => {
  if (!selectedChannel.value) return ''
  if (selectedChannel.value.type === 'dm') {
    const { getDMDisplayName } = useChat()
    return getDMDisplayName(selectedChannel.value)
  }
  return selectedChannel.value.name
})

const typeIcon = computed(() => {
  if (!selectedChannel.value) return ''
  if (selectedChannel.value.type === 'dm') return 'user'
  if (selectedChannel.value.type === 'private') return 'lock'
  return 'hash'
})
</script>

<template>
  <div class="flex items-center justify-between px-4 py-2.5 border-b bg-background shrink-0">
    <div class="flex items-center gap-2 min-w-0">
      <!-- Icon -->
      <span class="text-muted-foreground shrink-0">
        <svg v-if="typeIcon === 'hash'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
          <line x1="4" y1="9" x2="20" y2="9" /><line x1="4" y1="15" x2="20" y2="15" /><line x1="10" y1="3" x2="8" y2="21" /><line x1="16" y1="3" x2="14" y2="21" />
        </svg>
        <svg v-else-if="typeIcon === 'lock'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
        </svg>
        <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
          <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
        </svg>
      </span>

      <h3 class="text-sm font-semibold truncate">{{ displayName }}</h3>

      <span v-if="selectedChannel?.description" class="hidden sm:inline text-xs text-muted-foreground truncate">
        {{ selectedChannel.description }}
      </span>
    </div>

    <div class="flex items-center gap-1">
      <!-- Search toggle -->
      <button
        @click="showSearchPanel = !showSearchPanel"
        class="inline-flex items-center justify-center px-2 py-1 rounded-md hover:bg-accent transition-colors"
        :class="showSearchPanel ? 'bg-accent' : ''"
        :title="$t('chat.header.searchMessages')"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5">
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      </button>
      <!-- Member count / toggle -->
      <button
        @click="showMemberPanel = !showMemberPanel"
        class="inline-flex items-center gap-1.5 px-2 py-1 text-xs rounded-md hover:bg-accent transition-colors"
        :class="showMemberPanel ? 'bg-accent' : ''"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M23 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
        {{ memberCount }}
      </button>
    </div>
  </div>
</template>
