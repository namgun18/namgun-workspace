<script setup lang="ts">
const emit = defineEmits<{
  navigate: []
  'create-channel': []
}>()

const { sortedChannels, selectedChannelId, selectChannel, getDMDisplayName, totalUnread } = useChat()
const { user } = useAuth()

async function onSelect(id: string) {
  await selectChannel(id)
  emit('navigate')
}
</script>

<template>
  <div class="flex flex-col h-full border-r">
    <!-- Header -->
    <div class="flex items-center justify-between px-4 py-3 border-b">
      <h2 class="text-sm font-semibold">채팅</h2>
      <button
        @click="$emit('create-channel')"
        class="inline-flex items-center justify-center h-7 w-7 rounded-md hover:bg-accent transition-colors"
        title="새 채널"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
          <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
        </svg>
      </button>
    </div>

    <!-- Channel list -->
    <div class="flex-1 overflow-y-auto py-1">
      <!-- Channels -->
      <div v-if="sortedChannels.channels.length > 0" class="mb-2">
        <div class="px-4 py-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">채널</div>
        <ChatChannelItem
          v-for="ch in sortedChannels.channels"
          :key="ch.id"
          :channel="ch"
          :selected="ch.id === selectedChannelId"
          @click="onSelect(ch.id)"
        />
      </div>

      <!-- DMs -->
      <div v-if="sortedChannels.dms.length > 0">
        <div class="px-4 py-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">다이렉트 메시지</div>
        <ChatChannelItem
          v-for="ch in sortedChannels.dms"
          :key="ch.id"
          :channel="ch"
          :selected="ch.id === selectedChannelId"
          :dm-name="getDMDisplayName(ch)"
          @click="onSelect(ch.id)"
        />
      </div>

      <!-- Empty state -->
      <div v-if="sortedChannels.channels.length === 0 && sortedChannels.dms.length === 0" class="px-4 py-8 text-center text-sm text-muted-foreground">
        채널이 없습니다.<br>새 채널을 만들어보세요.
      </div>
    </div>
  </div>
</template>
