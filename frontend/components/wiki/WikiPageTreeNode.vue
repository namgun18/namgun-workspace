<script setup lang="ts">
const props = defineProps<{
  node: any
  selectedId: string | undefined
  depth: number
}>()

const emit = defineEmits<{
  select: [id: string]
}>()

const expanded = ref(true)
const hasChildren = computed(() => props.node.children?.length > 0)
</script>

<template>
  <div>
    <button
      class="w-full text-left flex items-center gap-1 py-1 px-1 rounded text-sm transition-colors group"
      :class="[
        selectedId === node.id ? 'bg-accent font-medium' : 'hover:bg-accent/50',
      ]"
      :style="{ paddingLeft: `${depth * 16 + 4}px` }"
      @click="emit('select', node.id)"
    >
      <!-- Expand/collapse -->
      <button
        v-if="hasChildren"
        class="w-4 h-4 flex items-center justify-center shrink-0 text-muted-foreground"
        @click.stop="expanded = !expanded"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
          stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
          class="w-3 h-3 transition-transform"
          :class="expanded ? 'rotate-90' : ''"
        >
          <polyline points="9 18 15 12 9 6" />
        </svg>
      </button>
      <span v-else class="w-4 shrink-0" />

      <!-- Page icon -->
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="w-4 h-4 shrink-0 text-muted-foreground">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
      </svg>

      <span class="truncate">{{ node.title }}</span>

      <span v-if="node.is_pinned" class="text-xs text-primary ml-auto shrink-0">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="w-3 h-3"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
      </span>
    </button>

    <!-- Children -->
    <div v-if="hasChildren && expanded">
      <WikiPageTreeNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :selected-id="selectedId"
        :depth="depth + 1"
        @select="emit('select', $event)"
      />
    </div>
  </div>
</template>
