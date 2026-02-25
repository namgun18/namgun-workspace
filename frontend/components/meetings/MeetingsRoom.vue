<script setup lang="ts">
const {
  participants,
  isHost,
  currentRoomName,
  cameraEnabled,
  micEnabled,
  screenShareEnabled,
  toggleCamera,
  toggleMic,
  toggleScreenShare,
  leaveRoom,
} = useMeetings()

const props = defineProps<{
  roomName: string
  shareToken?: string
}>()

const emit = defineEmits<{
  left: []
}>()

const linkCopied = ref(false)

// 사이드바
const sidebarOpen = ref(false)
const sidebarTab = ref<'participants' | 'waitingRoom' | 'chat'>('participants')

async function handleLeave() {
  await leaveRoom()
  emit('left')
}

function getShareUrl() {
  if (!props.shareToken) return ''
  return `${window.location.origin}/meetings/join/${props.shareToken}`
}

async function copyShareLink() {
  const url = getShareUrl()
  if (!url) return
  try {
    await navigator.clipboard.writeText(url)
    linkCopied.value = true
    setTimeout(() => { linkCopied.value = false }, 2000)
  } catch { /* ignore */ }
}

function handleSidebarToggle(tab: 'participants' | 'waitingRoom' | 'chat') {
  if (sidebarOpen.value && sidebarTab.value === tab) {
    sidebarOpen.value = false
  } else {
    sidebarTab.value = tab
    sidebarOpen.value = true
  }
}

// 화면공유 spotlight
const screenSharer = computed(() => participants.value.find((p) => p.screenTrack))
const otherParticipants = computed(() => participants.value.filter((p) => p !== screenSharer.value))
</script>

<template>
  <div class="flex flex-col h-[calc(100vh-3.5rem)]">
    <!-- 헤더 -->
    <div class="flex items-center justify-between px-4 py-2 border-b bg-background gap-2 shrink-0">
      <h2 class="font-semibold text-base truncate">{{ roomName }}</h2>
      <div class="flex items-center gap-2 shrink-0">
        <span class="text-sm text-muted-foreground hidden sm:inline">
          {{ participants.length }}명 참여 중
        </span>

        <!-- 공유링크 버튼 -->
        <button
          v-if="shareToken"
          @click="copyShareLink"
          class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md border hover:bg-accent transition-colors"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
          </svg>
          {{ linkCopied ? '복사됨' : '초대 링크' }}
        </button>
      </div>
    </div>

    <!-- 메인 영역: 비디오 + 사이드바 -->
    <div class="flex flex-1 overflow-hidden">
      <!-- 비디오 그리드 -->
      <div class="flex-1 overflow-auto p-2 sm:p-4 bg-muted/30">
        <!-- 화면공유 spotlight -->
        <template v-if="screenSharer">
          <div class="grid gap-2 h-full" style="grid-template-rows: 1fr auto;">
            <MeetingsParticipant v-bind="screenSharer" class="w-full" />
            <div class="flex gap-2 overflow-x-auto pb-1">
              <div v-for="p in otherParticipants" :key="p.identity" class="w-40 shrink-0">
                <MeetingsParticipant v-bind="p" />
              </div>
            </div>
          </div>
        </template>

        <!-- 일반 그리드 -->
        <template v-else>
          <div
            class="grid gap-2 sm:gap-3 h-full"
            :class="{
              'grid-cols-1': participants.length <= 1,
              'grid-cols-1 sm:grid-cols-2': participants.length === 2,
              'grid-cols-2': participants.length >= 3 && participants.length <= 4,
              'grid-cols-2 sm:grid-cols-3': participants.length >= 5,
            }"
          >
            <MeetingsParticipant
              v-for="p in participants"
              :key="p.identity"
              v-bind="p"
            />
          </div>
        </template>
      </div>

      <!-- 사이드바 -->
      <MeetingsSidebar
        v-if="sidebarOpen"
        :active-tab="sidebarTab"
        @update:active-tab="sidebarTab = $event"
        @close="sidebarOpen = false"
      />
    </div>

    <!-- 컨트롤 바 -->
    <MeetingsControls
      :camera-enabled="cameraEnabled"
      :mic-enabled="micEnabled"
      :screen-share-enabled="screenShareEnabled"
      :sidebar-open="sidebarOpen"
      :sidebar-tab="sidebarTab"
      @toggle-camera="toggleCamera"
      @toggle-mic="toggleMic"
      @toggle-screen="toggleScreenShare"
      @leave="handleLeave"
      @toggle-sidebar="handleSidebarToggle"
    />
  </div>
</template>
