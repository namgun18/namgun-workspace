<script setup lang="ts">
import type { Channel } from '~/composables/useChat'

const props = defineProps<{
  channel: Channel
  selected: boolean
  dmName?: string
}>()

const displayName = computed(() => {
  if (props.dmName) return props.dmName
  return props.channel.name
})

const icon = computed(() => {
  if (props.channel.type === 'dm') return 'user'
  if (props.channel.type === 'private') return 'lock'
  return 'hash'
})
</script>

<template>
  <button
    class="w-full flex items-center gap-2 px-4 py-1.5 text-sm transition-colors"
    :class="selected ? 'bg-accent text-accent-foreground' : 'text-foreground hover:bg-accent/50'"
  >
    <!-- Icon -->
    <span class="shrink-0 text-muted-foreground w-4 text-center">
      <svg v-if="icon === 'hash'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5 inline">
        <line x1="4" y1="9" x2="20" y2="9" /><line x1="4" y1="15" x2="20" y2="15" /><line x1="10" y1="3" x2="8" y2="21" /><line x1="16" y1="3" x2="14" y2="21" />
      </svg>
      <svg v-else-if="icon === 'lock'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5 inline">
        <rect x="3" y="11" width="18" height="11" rx="2" ry="2" /><path d="M7 11V7a5 5 0 0 1 10 0v4" />
      </svg>
      <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5 inline">
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" />
      </svg>
    </span>

    <!-- Name -->
    <span class="flex-1 truncate text-left" :class="channel.unread_count > 0 ? 'font-semibold' : ''">
      {{ displayName }}
    </span>

    <!-- Unread badge -->
    <span
      v-if="channel.unread_count > 0"
      class="shrink-0 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold rounded-full bg-primary text-primary-foreground"
    >
      {{ channel.unread_count > 99 ? '99+' : channel.unread_count }}
    </span>
  </button>
</template>
