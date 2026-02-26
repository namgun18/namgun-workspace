<script setup lang="ts">
const { unreadChat, pendingRequests } = useMeetings()

const props = defineProps<{
  cameraEnabled: boolean
  micEnabled: boolean
  screenShareEnabled: boolean
  sidebarOpen?: boolean
  sidebarTab?: 'participants' | 'waitingRoom' | 'chat'
}>()

const emit = defineEmits<{
  toggleCamera: []
  toggleMic: []
  toggleScreen: []
  leave: []
  toggleSidebar: [tab: 'participants' | 'waitingRoom' | 'chat']
}>()
</script>

<template>
  <div class="flex items-center justify-center gap-2 sm:gap-3 py-3 px-4 bg-background border-t shrink-0">
    <!-- 카메라 토글 -->
    <button
      @click="emit('toggleCamera')"
      class="inline-flex items-center justify-center h-11 w-11 rounded-full transition-colors"
      :class="cameraEnabled ? 'bg-muted hover:bg-muted/80' : 'bg-destructive/15 text-destructive hover:bg-destructive/25'"
      :title="cameraEnabled ? $t('meetings.controls.cameraOff') : $t('meetings.controls.cameraOn')"
    >
      <svg v-if="cameraEnabled" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5">
        <path d="m22 8-6 4 6 4V8Z" /><rect width="14" height="12" x="1" y="6" rx="2" ry="2" />
      </svg>
      <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5">
        <path d="M10.66 6H14a2 2 0 0 1 2 2v2.34l1 1L22 8v8" />
        <path d="M16 16a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h2l10 10Z" />
        <line x1="2" y1="2" x2="22" y2="22" />
      </svg>
    </button>

    <!-- 마이크 토글 -->
    <button
      @click="emit('toggleMic')"
      class="inline-flex items-center justify-center h-11 w-11 rounded-full transition-colors"
      :class="micEnabled ? 'bg-muted hover:bg-muted/80' : 'bg-destructive/15 text-destructive hover:bg-destructive/25'"
      :title="micEnabled ? $t('meetings.controls.micOff') : $t('meetings.controls.micOn')"
    >
      <svg v-if="micEnabled" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5">
        <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
        <path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" y1="19" x2="12" y2="22" />
      </svg>
      <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5">
        <line x1="2" y1="2" x2="22" y2="22" />
        <path d="M18.89 13.23A7.12 7.12 0 0 0 19 12v-2" />
        <path d="M5 10v2a7 7 0 0 0 12 5" />
        <path d="M15 9.34V5a3 3 0 0 0-5.68-1.33" />
        <path d="M9 9v3a3 3 0 0 0 5.12 2.12" />
        <line x1="12" y1="19" x2="12" y2="22" />
      </svg>
    </button>

    <!-- 화면공유 토글 -->
    <button
      @click="emit('toggleScreen')"
      class="inline-flex items-center justify-center h-11 w-11 rounded-full transition-colors"
      :class="screenShareEnabled ? 'bg-blue-500/15 text-blue-600 dark:text-blue-400 hover:bg-blue-500/25' : 'bg-muted hover:bg-muted/80'"
      :title="screenShareEnabled ? $t('meetings.controls.screenStop') : $t('meetings.controls.screenShare')"
    >
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5">
        <rect width="20" height="14" x="2" y="3" rx="2" /><line x1="8" y1="21" x2="16" y2="21" /><line x1="12" y1="17" x2="12" y2="21" />
      </svg>
    </button>

    <!-- 구분선 -->
    <div class="w-px h-7 bg-border mx-1 hidden sm:block" />

    <!-- 참여자 사이드바 토글 -->
    <button
      @click="emit('toggleSidebar', 'participants')"
      class="relative inline-flex items-center justify-center h-11 w-11 rounded-full transition-colors"
      :class="sidebarOpen && sidebarTab === 'participants' ? 'bg-primary/15 text-primary' : 'bg-muted hover:bg-muted/80'"
      :title="$t('meetings.controls.participants')"
    >
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5">
        <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
        <path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </svg>
      <span
        v-if="pendingRequests.length > 0"
        class="absolute -top-0.5 -right-0.5 flex items-center justify-center h-4 min-w-[1rem] px-1 text-[10px] font-bold rounded-full bg-orange-500 text-white"
      >
        {{ pendingRequests.length }}
      </span>
    </button>

    <!-- 채팅 사이드바 토글 -->
    <button
      @click="emit('toggleSidebar', 'chat')"
      class="relative inline-flex items-center justify-center h-11 w-11 rounded-full transition-colors"
      :class="sidebarOpen && sidebarTab === 'chat' ? 'bg-primary/15 text-primary' : 'bg-muted hover:bg-muted/80'"
      :title="$t('meetings.controls.chat')"
    >
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
      <span
        v-if="unreadChat > 0 && !(sidebarOpen && sidebarTab === 'chat')"
        class="absolute -top-0.5 -right-0.5 flex items-center justify-center h-4 min-w-[1rem] px-1 text-[10px] font-bold rounded-full bg-blue-500 text-white"
      >
        {{ unreadChat > 99 ? '99+' : unreadChat }}
      </span>
    </button>

    <!-- 나가기 -->
    <button
      @click="emit('leave')"
      class="inline-flex items-center justify-center h-11 px-5 rounded-full bg-destructive text-destructive-foreground hover:bg-destructive/90 transition-colors font-medium text-sm"
    >
      {{ $t('meetings.controls.leave') }}
    </button>
  </div>
</template>
