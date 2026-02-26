<script setup lang="ts">
import type { BoardInfo } from '~/composables/useBoard'

defineProps<{
  board: BoardInfo
}>()
</script>

<template>
  <NuxtLink
    :to="`/board/${board.id}`"
    class="block p-4 border rounded-lg hover:bg-accent/50 transition-colors"
  >
    <div class="flex items-start gap-3">
      <div class="h-10 w-10 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-5 w-5">
          <rect x="3" y="3" width="18" height="18" rx="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" />
        </svg>
      </div>
      <div class="flex-1 min-w-0">
        <h3 class="font-medium text-sm">{{ board.name }}</h3>
        <p v-if="board.description" class="text-xs text-muted-foreground mt-0.5 line-clamp-1">
          {{ board.description }}
        </p>
        <div v-if="board.categories.length > 0" class="flex gap-1 mt-1.5 flex-wrap">
          <span
            v-for="cat in board.categories.slice(0, 4)"
            :key="cat"
            class="text-[10px] px-1.5 py-0.5 rounded bg-muted text-muted-foreground"
          >{{ cat }}</span>
          <span v-if="board.categories.length > 4" class="text-[10px] text-muted-foreground">+{{ board.categories.length - 4 }}</span>
        </div>
      </div>
    </div>
  </NuxtLink>
</template>
