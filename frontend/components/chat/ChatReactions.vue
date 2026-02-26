<script setup lang="ts">
import type { ReactionGroup } from '~/composables/useChat'

const props = defineProps<{
  reactions: ReactionGroup[]
  messageId: string
  size?: 'sm' | 'md'
}>()

const { toggleReaction } = useChat()

const PRESET_EMOJIS = ['👍', '❤️', '😂', '😮', '😢', '🔥']
const showPicker = ref(false)

function onToggle(emoji: string) {
  toggleReaction(props.messageId, emoji)
  showPicker.value = false
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-1 mt-0.5">
    <!-- Existing reaction badges -->
    <button
      v-for="r in reactions"
      :key="r.emoji"
      @click="onToggle(r.emoji)"
      class="inline-flex items-center gap-0.5 px-1.5 rounded-full border text-xs transition-colors"
      :class="[
        r.reacted
          ? 'bg-primary/10 border-primary/30 text-primary'
          : 'bg-muted/50 border-transparent hover:bg-accent',
        size === 'sm' ? 'py-0 text-[10px]' : 'py-0.5',
      ]"
      :title="$t('board.reaction.countLabel', { n: r.user_ids.length })"
    >
      <span>{{ r.emoji }}</span>
      <span>{{ r.count }}</span>
    </button>

    <!-- Add reaction button -->
    <div class="relative">
      <button
        @click="showPicker = !showPicker"
        class="inline-flex items-center justify-center rounded-full border border-dashed border-muted-foreground/30 hover:bg-accent transition-colors"
        :class="size === 'sm' ? 'h-4 w-4 text-[9px]' : 'h-5 w-5 text-[10px]'"
        :title="$t('chat.reactions.add')"
      >
        +
      </button>

      <!-- Quick picker -->
      <div
        v-if="showPicker"
        class="absolute bottom-full left-0 mb-1 flex gap-0.5 px-1.5 py-1 bg-popover border rounded-lg shadow-md z-10"
      >
        <button
          v-for="emoji in PRESET_EMOJIS"
          :key="emoji"
          @click="onToggle(emoji)"
          class="p-0.5 hover:bg-accent rounded transition-colors text-sm"
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
