<script setup lang="ts">
defineProps<{
  current: number
  total: number
  pages: (number | '...')[]
}>()

const emit = defineEmits<{
  go: [page: number]
}>()
</script>

<template>
  <nav class="flex items-center gap-1">
    <button
      :disabled="current <= 1"
      @click="emit('go', current - 1)"
      class="h-8 w-8 flex items-center justify-center rounded-md text-sm hover:bg-accent disabled:opacity-30 disabled:pointer-events-none transition-colors"
    >
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
        <polyline points="15 18 9 12 15 6" />
      </svg>
    </button>

    <template v-for="(p, i) in pages" :key="i">
      <span v-if="p === '...'" class="px-1 text-muted-foreground text-sm">...</span>
      <button
        v-else
        @click="emit('go', p)"
        class="h-8 min-w-[2rem] px-2 flex items-center justify-center rounded-md text-sm transition-colors"
        :class="p === current
          ? 'bg-primary text-primary-foreground font-medium'
          : 'hover:bg-accent'"
      >
        {{ p }}
      </button>
    </template>

    <button
      :disabled="current >= total"
      @click="emit('go', current + 1)"
      class="h-8 w-8 flex items-center justify-center rounded-md text-sm hover:bg-accent disabled:opacity-30 disabled:pointer-events-none transition-colors"
    >
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
        <polyline points="9 18 15 12 9 6" />
      </svg>
    </button>
  </nav>
</template>
