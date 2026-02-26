<script setup lang="ts">
defineProps<{
  categories: string[]
  selected: string | null
}>()

const emit = defineEmits<{
  select: [category: string | null]
}>()
</script>

<template>
  <div class="flex items-center gap-1 overflow-x-auto">
    <button
      @click="emit('select', null)"
      class="px-2.5 py-1 rounded-md text-sm whitespace-nowrap transition-colors"
      :class="!selected ? 'bg-accent font-medium' : 'text-muted-foreground hover:bg-accent/50'"
    >
      {{ $t('common.all') }}
    </button>
    <button
      v-for="cat in categories"
      :key="cat"
      @click="emit('select', cat)"
      class="px-2.5 py-1 rounded-md text-sm whitespace-nowrap transition-colors"
      :class="selected === cat ? 'bg-accent font-medium' : 'text-muted-foreground hover:bg-accent/50'"
    >
      {{ cat }}
    </button>
  </div>
</template>
