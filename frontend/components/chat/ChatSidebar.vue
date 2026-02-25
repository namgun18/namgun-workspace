<script setup lang="ts">
const emit = defineEmits<{
  navigate: []
  'create-channel': []
}>()

const { sortedChannels, selectedChannelId, selectChannel, getDMDisplayName, allUsers, onlineUsers, openDM } = useChat()
const { user } = useAuth()

// Sidebar tab: 'channels' or 'users'
const activeTab = ref<'channels' | 'users'>('channels')

async function onSelect(id: string) {
  await selectChannel(id)
  emit('navigate')
}

async function onUserClick(userId: string) {
  if (userId === user.value?.id) return
  await openDM(userId)
  activeTab.value = 'channels'
  emit('navigate')
}

const onlineUsersList = computed(() =>
  allUsers.value.filter(u => u.id !== user.value?.id && onlineUsers.value.has(u.id))
)

const offlineUsersList = computed(() =>
  allUsers.value.filter(u => u.id !== user.value?.id && !onlineUsers.value.has(u.id))
)
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

    <!-- Tab switcher -->
    <div class="flex border-b">
      <button
        @click="activeTab = 'channels'"
        class="flex-1 py-2 text-xs font-medium text-center transition-colors"
        :class="activeTab === 'channels' ? 'text-foreground border-b-2 border-primary' : 'text-muted-foreground hover:text-foreground'"
      >
        채널
      </button>
      <button
        @click="activeTab = 'users'"
        class="flex-1 py-2 text-xs font-medium text-center transition-colors"
        :class="activeTab === 'users' ? 'text-foreground border-b-2 border-primary' : 'text-muted-foreground hover:text-foreground'"
      >
        사용자
      </button>
    </div>

    <!-- Channels tab -->
    <div v-if="activeTab === 'channels'" class="flex-1 overflow-y-auto py-1">
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

    <!-- Users tab -->
    <div v-else class="flex-1 overflow-y-auto py-1">
      <!-- Online users -->
      <div v-if="onlineUsersList.length > 0">
        <div class="px-4 py-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
          온라인 — {{ onlineUsersList.length }}
        </div>
        <button
          v-for="u in onlineUsersList"
          :key="u.id"
          @click="onUserClick(u.id)"
          class="w-full flex items-center gap-2.5 px-4 py-1.5 text-sm hover:bg-accent/50 transition-colors"
        >
          <div class="relative shrink-0">
            <UiAvatar
              :src="u.avatar_url"
              :alt="u.display_name || u.username"
              :fallback="(u.display_name || u.username).charAt(0).toUpperCase()"
              class="h-7 w-7"
            />
            <span class="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-green-500 border-2 border-background" />
          </div>
          <span class="truncate">{{ u.display_name || u.username }}</span>
        </button>
      </div>

      <!-- Offline users -->
      <div v-if="offlineUsersList.length > 0">
        <div class="px-4 py-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
          오프라인 — {{ offlineUsersList.length }}
        </div>
        <button
          v-for="u in offlineUsersList"
          :key="u.id"
          @click="onUserClick(u.id)"
          class="w-full flex items-center gap-2.5 px-4 py-1.5 text-sm hover:bg-accent/50 transition-colors opacity-60"
        >
          <div class="relative shrink-0">
            <UiAvatar
              :src="u.avatar_url"
              :alt="u.display_name || u.username"
              :fallback="(u.display_name || u.username).charAt(0).toUpperCase()"
              class="h-7 w-7"
            />
            <span class="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-gray-400 border-2 border-background" />
          </div>
          <span class="truncate">{{ u.display_name || u.username }}</span>
        </button>
      </div>

      <!-- No users -->
      <div v-if="allUsers.length <= 1" class="px-4 py-8 text-center text-sm text-muted-foreground">
        다른 사용자가 없습니다.
      </div>
    </div>
  </div>
</template>
