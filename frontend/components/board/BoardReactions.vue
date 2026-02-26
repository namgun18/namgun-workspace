<script setup lang="ts">
import type { ReactionGroup } from '~/composables/useBoard'

const props = defineProps<{
  reactions: ReactionGroup[]
  postId: string
}>()

const { toggleReaction } = useBoard()

const PRESET_EMOJIS = ['👍', '❤️', '😂', '😮', '😢', '🔥']
const showPicker = ref(false)

function onToggle(emoji: string) {
  toggleReaction(props.postId, emoji)
  showPicker.value = false
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-1.5 mt-4">
    <!-- Existing reaction badges -->
    <button
      v-for="r in reactions"
      :key="r.emoji"
      @click="onToggle(r.emoji)"
      class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full border text-sm transition-colors"
      :class="r.reacted
        ? 'bg-primary/10 border-primary/30 text-primary'
        : 'bg-muted/50 border-transparent hover:bg-accent'"
      :title="$t('board.reaction.countLabel', { n: r.count })"
    >
      <span>{{ r.emoji }}</span>
      <span class="text-xs">{{ r.count }}</span>
    </button>

    <!-- Add reaction -->
    <div class="relative">
      <button
        @click="showPicker = !showPicker"
        class="inline-flex items-center justify-center h-6 w-6 rounded-full border border-dashed border-muted-foreground/30 hover:bg-accent transition-colors text-xs"
        :title="$t('board.reaction.addTitle')"
      >
        +
      </button>
      <div
        v-if="showPicker"
        class="absolute bottom-full left-0 mb-1 flex gap-1 px-2 py-1.5 bg-popover border rounded-lg shadow-md z-10"
      >
        <button
          v-for="emoji in PRESET_EMOJIS"
          :key="emoji"
          @click="onToggle(emoji)"
          class="p-0.5 hover:bg-accent rounded transition-colors text-base"
        >
          {{ emoji }}
        </button>
      </div>
    </div>
  </div>

  <!-- Click outside to close picker -->
  <Teleport to="body">
    <div v-if="showPicker" class="fixed inset-0 z-[9]" @click="showPicker = false" />
  </Teleport>
</template>
