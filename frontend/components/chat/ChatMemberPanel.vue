<script setup lang="ts">
const { members, selectedChannel, onlineUsers, leaveChannel, openDM, showMemberPanel } = useChat()
const { user } = useAuth()

const onlineMembers = computed(() => members.value.filter(m => m.is_online))
const offlineMembers = computed(() => members.value.filter(m => !m.is_online))

async function onLeave() {
  if (!selectedChannel.value) return
  if (!confirm('이 채널을 나가시겠습니까?')) return
  await leaveChannel(selectedChannel.value.id)
}

async function onDM(userId: string) {
  if (userId === user.value?.id) return
  await openDM(userId)
  showMemberPanel.value = false
}
</script>

<template>
  <div class="w-56 border-l h-full flex flex-col bg-background shrink-0">
    <div class="flex items-center justify-between px-3 py-2.5 border-b">
      <h4 class="text-xs font-semibold uppercase tracking-wider text-muted-foreground">멤버</h4>
      <button @click="showMemberPanel = false" class="h-6 w-6 flex items-center justify-center rounded hover:bg-accent">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-3 w-3">
          <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>

    <div class="flex-1 overflow-y-auto py-1">
      <!-- Online -->
      <div v-if="onlineMembers.length > 0">
        <div class="px-3 py-1 text-[10px] font-medium text-muted-foreground uppercase">
          온라인 — {{ onlineMembers.length }}
        </div>
        <button
          v-for="m in onlineMembers"
          :key="m.user_id"
          @click="onDM(m.user_id)"
          class="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-accent/50 transition-colors"
        >
          <div class="relative shrink-0">
            <UiAvatar
              :src="m.avatar_url"
              :alt="m.display_name || m.username"
              :fallback="(m.display_name || m.username).charAt(0).toUpperCase()"
              class="h-6 w-6"
            />
            <span class="absolute -bottom-0.5 -right-0.5 h-2.5 w-2.5 rounded-full bg-green-500 border-2 border-background" />
          </div>
          <span class="text-xs truncate">{{ m.display_name || m.username }}</span>
          <span v-if="m.role === 'owner'" class="text-[9px] text-muted-foreground ml-auto">소유자</span>
        </button>
      </div>

      <!-- Offline -->
      <div v-if="offlineMembers.length > 0">
        <div class="px-3 py-1 text-[10px] font-medium text-muted-foreground uppercase">
          오프라인 — {{ offlineMembers.length }}
        </div>
        <button
          v-for="m in offlineMembers"
          :key="m.user_id"
          @click="onDM(m.user_id)"
          class="w-full flex items-center gap-2 px-3 py-1.5 hover:bg-accent/50 transition-colors opacity-60"
        >
          <UiAvatar
            :src="m.avatar_url"
            :alt="m.display_name || m.username"
            :fallback="(m.display_name || m.username).charAt(0).toUpperCase()"
            class="h-6 w-6"
          />
          <span class="text-xs truncate">{{ m.display_name || m.username }}</span>
        </button>
      </div>
    </div>

    <!-- Leave channel -->
    <div v-if="selectedChannel && selectedChannel.type !== 'dm'" class="border-t px-3 py-2">
      <button
        @click="onLeave"
        class="w-full text-xs text-destructive hover:bg-destructive/10 px-2 py-1.5 rounded transition-colors"
      >
        채널 나가기
      </button>
    </div>
  </div>
</template>
