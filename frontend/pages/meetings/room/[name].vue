<script setup lang="ts">
definePageMeta({ layout: false })

const route = useRoute()
const roomName = decodeURIComponent(route.params.name as string)

const {
  connected,
  currentRoomName,
  isHost,
  participants,
  cameraEnabled,
  micEnabled,
  screenShareEnabled,
  toggleCamera,
  toggleMic,
  toggleScreenShare,
  leaveRoom,
  joinRoom,
  joinRoomWithToken,
} = useMeetings()

const { t } = useI18n()

// 3단계: device-setup → meeting → ended
const phase = ref<'device-setup' | 'meeting' | 'ended'>('device-setup')

// URL query에서 토큰/ws 정보
const queryToken = route.query.t as string | undefined
const queryWs = route.query.ws as string | undefined
const queryHost = route.query.host === '1'

// 사이드바 상태
const sidebarOpen = ref(false)
const sidebarTab = ref<'participants' | 'waitingRoom' | 'chat'>('participants')

// 공유 링크
const shareToken = (route.query.st as string) || ''
const linkCopied = ref(false)

function getShareUrl() {
  if (!shareToken) return ''
  return `${window.location.origin}/meetings/join/${shareToken}`
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

// 화면공유 spotlight
const screenSharer = computed(() => participants.value.find(p => p.screenTrack))
const otherParticipants = computed(() => participants.value.filter(p => p !== screenSharer.value))

async function handleDeviceReady(opts: { cameraEnabled: boolean; micEnabled: boolean; selectedCameraId?: string; selectedMicId?: string }) {
  try {
    if (queryToken && queryWs) {
      // 게스트 or 외부 토큰
      await joinRoomWithToken(queryWs, queryToken, roomName, opts)
    } else {
      // 인증 사용자 — API로 토큰 발급
      await joinRoom(roomName, opts)
    }
    if (queryHost) {
      // 호스트 flag (lobby에서 전달)
      const { isHost: isHostRef } = useMeetings()
      isHostRef.value = true
    }
    phase.value = 'meeting'
  } catch (e: any) {
    alert(e?.data?.detail || t('meetings.join.joinFail'))
  }
}

function handleCancel() {
  closeWindow()
}

function closeWindow() {
  try {
    window.close()
  } catch { /* ignore */ }
  // window.close()가 무시될 경우 안내 표시
}

async function handleLeave() {
  await leaveRoom()
  phase.value = 'ended'
}

function handleSidebarToggle(tab: 'participants' | 'waitingRoom' | 'chat') {
  if (sidebarOpen.value && sidebarTab.value === tab) {
    sidebarOpen.value = false
  } else {
    sidebarTab.value = tab
    sidebarOpen.value = true
  }
}

// 창 닫기 시 자동 퇴장
if (import.meta.client) {
  window.addEventListener('beforeunload', () => {
    if (connected.value) {
      leaveRoom()
    }
  })
}

onBeforeUnmount(() => {
  if (connected.value) leaveRoom()
})
</script>

<template>
  <div class="min-h-screen bg-background text-foreground">
    <!-- 1. 장치 테스트 -->
    <MeetingsDeviceSetup
      v-if="phase === 'device-setup'"
      :room-name="roomName"
      @join="handleDeviceReady"
      @cancel="handleCancel"
    />

    <!-- 2. 회의 중 -->
    <ClientOnly v-else-if="phase === 'meeting' && connected">
      <div class="flex flex-col h-screen">
        <!-- 룸 헤더 -->
        <div class="flex items-center justify-between px-4 py-2 border-b bg-background gap-2 shrink-0">
          <h2 class="font-semibold text-base truncate">{{ currentRoomName }}</h2>
          <div class="flex items-center gap-2 shrink-0">
            <span class="text-sm text-muted-foreground hidden sm:inline">
              {{ participants.length }}{{ $t('meetings.room.participantCount') }}
            </span>
            <button
              v-if="shareToken"
              @click="copyShareLink"
              class="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md border hover:bg-accent transition-colors"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5">
                <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71" />
                <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71" />
              </svg>
              {{ linkCopied ? $t('common.copied') : $t('meetings.room.inviteLink') }}
            </button>
          </div>
        </div>

        <!-- 메인 영역: 비디오 + 사이드바 -->
        <div class="flex flex-1 overflow-hidden">
          <!-- 비디오 그리드 -->
          <div class="flex-1 overflow-auto p-2 sm:p-4 bg-muted/30">
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
                <MeetingsParticipant v-for="p in participants" :key="p.identity" v-bind="p" />
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
    </ClientOnly>

    <!-- 3. 회의 종료 -->
    <div v-else-if="phase === 'ended'" class="flex items-center justify-center min-h-screen">
      <div class="text-center">
        <div class="inline-flex items-center justify-center h-16 w-16 rounded-full bg-muted mb-4">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-8 w-8 text-muted-foreground">
            <path d="m22 8-6 4 6 4V8Z" /><rect width="14" height="12" x="1" y="6" rx="2" ry="2" />
          </svg>
        </div>
        <h2 class="text-lg font-semibold mb-1">{{ $t('meetings.room.ended') }}</h2>
        <p class="text-sm text-muted-foreground mb-4">{{ $t('meetings.room.endedDesc') }}</p>
        <button
          @click="closeWindow"
          class="px-5 py-2 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
        >
          {{ $t('meetings.room.closeWindow') }}
        </button>
      </div>
    </div>
  </div>
</template>
