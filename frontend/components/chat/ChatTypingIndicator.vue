<script setup lang="ts">
import type { TypingUser } from '~/composables/useChat'

const props = defineProps<{
  typingUsers: ReadonlyMap<string, TypingUser>
}>()

const { t } = useI18n()

const typingText = computed(() => {
  const users = Array.from(props.typingUsers.values())
  if (users.length === 0) return ''
  if (users.length === 1) return t('chat.typing.one', { name: users[0].username })
  if (users.length === 2) return t('chat.typing.two', { name1: users[0].username, name2: users[1].username })
  return t('chat.typing.many', { name: users[0].username, n: users.length - 1 })
})
</script>

<template>
  <div class="h-5 px-4 shrink-0">
    <p v-if="typingText" class="text-xs text-muted-foreground animate-pulse">
      {{ typingText }}
    </p>
  </div>
</template>
