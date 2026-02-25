<script setup lang="ts">
import type { ChatMessage } from '~/composables/useChat'

defineProps<{
  message: ChatMessage
}>()
</script>

<template>
  <div class="flex items-center gap-3 py-2 my-1">
    <div class="flex-1 h-px bg-border" />
    <span class="text-xs text-muted-foreground shrink-0">
      {{ message.content }}
    </span>
    <div class="flex-1 h-px bg-border" />
  </div>
</template>
