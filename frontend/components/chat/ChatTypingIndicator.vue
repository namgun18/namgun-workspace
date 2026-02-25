<script setup lang="ts">
import type { TypingUser } from '~/composables/useChat'

const props = defineProps<{
  typingUsers: ReadonlyMap<string, TypingUser>
}>()

const typingText = computed(() => {
  const users = Array.from(props.typingUsers.values())
  if (users.length === 0) return ''
  if (users.length === 1) return `${users[0].username}님이 입력 중...`
  if (users.length === 2) return `${users[0].username}, ${users[1].username}님이 입력 중...`
  return `${users[0].username} 외 ${users.length - 1}명이 입력 중...`
})
</script>

<template>
  <div class="h-5 px-4 shrink-0">
    <p v-if="typingText" class="text-xs text-muted-foreground animate-pulse">
      {{ typingText }}
    </p>
  </div>
</template>
