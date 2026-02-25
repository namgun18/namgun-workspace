<script setup lang="ts">
definePageMeta({ layout: false })

const route = useRoute()
const token = route.params.token as string

const {
  connected,
  currentRoomName,
  joinRoomWithToken,
  leaveRoom,
  participants,
  cameraEnabled,
  micEnabled,
  screenShareEnabled,
  toggleCamera,
  toggleMic,
  toggleScreenShare,
} = useMeetings()

// 페이지 상태: loading → form → waiting → device-setup → room → denied → error
const step = ref<'loading' | 'form' | 'waiting' | 'device-setup' | 'room' | 'denied' | 'error'>('loading')
const roomInfo = ref<{ name: string; host_name: string; num_participants: number; max_participants: number } | null>(null)
const nickname = ref('')
const requestId = ref<string | null>(null)
const errorMsg = ref('')

// 승인 후 받은 토큰 저장
const approvedToken = ref('')
const approvedWsUrl = ref('')

// 사이드바 상태
const sidebarOpen = ref(false)
const sidebarTab = ref<'participants' | 'waitingRoom' | 'chat'>('participants')

// 1. 회의실 정보 조회
onMounted(async () => {
  try {
    const data = await $fetch<typeof roomInfo.value>(`/api/meetings/join/${token}`)
    roomInfo.value = data
    step.value = 'form'
  } catch (e: any) {
    errorMsg.value = e?.data?.detail || '초대 링크가 유효하지 않습니다'
    step.value = 'error'
  }
})

// 2. 참가 신청
async function submitRequest() {
  if (!nickname.value.trim()) return
  try {
    const data = await $fetch<{ request_id: string }>(`/api/meetings/join/${token}/request`, {
      method: 'POST',
      body: { nickname: nickname.value.trim() },
    })
    requestId.value = data.request_id
    step.value = 'waiting'
    startPolling()
  } catch (e: any) {
    errorMsg.value = e?.data?.detail || '참가 신청에 실패했습니다'
    step.value = 'error'
  }
}

// 3. 승인 상태 폴링
let pollTimer: ReturnType<typeof setInterval> | null = null

function startPolling() {
  pollTimer = setInterval(async () => {
    if (!requestId.value) return
    try {
      const data = await $fetch<{ status: string; token?: string; livekit_url?: string }>(
        `/api/meetings/join/${token}/request/${requestId.value}/status`
      )
      if (data.status === 'approved' && data.token && data.livekit_url) {
        stopPolling()
        approvedToken.value = data.token
        approvedWsUrl.value = data.livekit_url
        step.value = 'device-setup'
      } else if (data.status === 'denied') {
        stopPolling()
        step.value = 'denied'
      }
    } catch { /* 네트워크 오류 무시, 재시도 */ }
  }, 2000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

onBeforeUnmount(() => {
  stopPolling()
  if (connected.value) leaveRoom()
})

// 장치 테스트 완료 → 회의 입장
async function handleDeviceReady(opts: { cameraEnabled: boolean; micEnabled: boolean; selectedCameraId?: string; selectedMicId?: string }) {
  try {
    await joinRoomWithToken(approvedWsUrl.value, approvedToken.value, roomInfo.value?.name || '', opts)
    step.value = 'room'
  } catch (e: any) {
    errorMsg.value = e?.data?.detail || '회의 참여에 실패했습니다'
    step.value = 'error'
  }
}

function handleDeviceCancel() {
  step.value = 'form'
  nickname.value = ''
  requestId.value = null
  approvedToken.value = ''
  approvedWsUrl.value = ''
}

async function handleLeave() {
  await leaveRoom()
  step.value = 'form'
  nickname.value = ''
  requestId.value = null
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
const screenSharer = computed(() => participants.value.find(p => p.screenTrack))
const otherParticipants = computed(() => participants.value.filter(p => p !== screenSharer.value))
</script>

<template>
  <div class="min-h-screen bg-background text-foreground">
    <!-- 간소화 헤더 -->
    <header v-if="step !== 'device-setup' && step !== 'room'" class="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur">
      <div class="flex h-14 items-center justify-between px-4">
        <span class="font-bold text-lg">namgun.or.kr</span>
        <span class="text-sm text-muted-foreground">화상회의</span>
      </div>
      <div class="h-0.5 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 opacity-80" />
    </header>

    <!-- 장치 테스트 -->
    <MeetingsDeviceSetup
      v-if="step === 'device-setup'"
      :room-name="roomInfo?.name || ''"
      @join="handleDeviceReady"
      @cancel="handleDeviceCancel"
    />

    <!-- 회의 참여 중 -->
    <ClientOnly v-else-if="step === 'room' && connected">
      <div class="flex flex-col h-screen">
        <!-- 룸 헤더 -->
        <div class="flex items-center justify-between px-4 py-2 border-b bg-background">
          <h2 class="font-semibold text-base truncate">{{ currentRoomName }}</h2>
          <span class="text-sm text-muted-foreground">{{ participants.length }}명 참여 중</span>
        </div>

        <!-- 메인 영역 -->
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

    <!-- 로비 상태들 (form, waiting, denied, error, loading) -->
    <div v-else-if="step !== 'device-setup'" class="flex items-center justify-center min-h-[calc(100vh-3.75rem)]">
      <div class="w-full max-w-sm mx-4">

        <!-- 로딩 -->
        <div v-if="step === 'loading'" class="text-center py-12">
          <div class="inline-block h-8 w-8 animate-spin rounded-full border-4 border-primary border-r-transparent mb-3" />
          <p class="text-muted-foreground">회의실 정보를 불러오는 중...</p>
        </div>

        <!-- 닉네임 입력 폼 -->
        <div v-else-if="step === 'form' && roomInfo" class="rounded-lg border bg-card p-6">
          <div class="text-center mb-6">
            <div class="inline-flex items-center justify-center h-12 w-12 rounded-full bg-primary/10 mb-3">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-6 w-6 text-primary">
                <path d="m22 8-6 4 6 4V8Z" /><rect width="14" height="12" x="1" y="6" rx="2" ry="2" />
              </svg>
            </div>
            <h2 class="text-lg font-semibold">{{ roomInfo.name }}</h2>
            <p class="text-sm text-muted-foreground mt-1">
              호스트: {{ roomInfo.host_name }}
            </p>
            <p class="text-xs text-muted-foreground mt-0.5">
              {{ roomInfo.num_participants }}/{{ roomInfo.max_participants }}명 참여 중
            </p>
          </div>

          <form @submit.prevent="submitRequest">
            <label class="block text-sm font-medium mb-1.5">표시 이름</label>
            <input
              v-model="nickname"
              type="text"
              placeholder="회의에서 사용할 이름"
              maxlength="30"
              class="w-full px-3 py-2 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              autofocus
            />
            <p class="text-xs text-muted-foreground mt-1.5">호스트가 참여를 승인하면 회의에 입장합니다</p>
            <button
              type="submit"
              :disabled="!nickname.trim()"
              class="w-full mt-4 px-4 py-2.5 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
            >
              참여 요청
            </button>
          </form>
        </div>

        <!-- 대기 중 -->
        <div v-else-if="step === 'waiting'" class="rounded-lg border bg-card p-6 text-center">
          <div class="inline-block h-10 w-10 animate-spin rounded-full border-4 border-primary border-r-transparent mb-4" />
          <h2 class="text-lg font-semibold mb-1">승인 대기 중</h2>
          <p class="text-sm text-muted-foreground">
            호스트가 참여를 승인할 때까지 잠시 기다려 주세요
          </p>
          <p class="text-xs text-muted-foreground mt-3">
            "{{ nickname }}" (으)로 참여 요청됨
          </p>
        </div>

        <!-- 거절 -->
        <div v-else-if="step === 'denied'" class="rounded-lg border bg-card p-6 text-center">
          <div class="inline-flex items-center justify-center h-12 w-12 rounded-full bg-destructive/10 mb-3">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-6 w-6 text-destructive">
              <circle cx="12" cy="12" r="10" /><line x1="15" y1="9" x2="9" y2="15" /><line x1="9" y1="9" x2="15" y2="15" />
            </svg>
          </div>
          <h2 class="text-lg font-semibold mb-1">참여가 거절되었습니다</h2>
          <p class="text-sm text-muted-foreground">호스트가 참여 요청을 거절했습니다</p>
          <button
            @click="step = 'form'; nickname = ''; requestId = null"
            class="mt-4 px-4 py-2 text-sm rounded-md border hover:bg-accent transition-colors"
          >
            다시 시도
          </button>
        </div>

        <!-- 에러 -->
        <div v-else-if="step === 'error'" class="rounded-lg border bg-card p-6 text-center">
          <div class="inline-flex items-center justify-center h-12 w-12 rounded-full bg-destructive/10 mb-3">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-6 w-6 text-destructive">
              <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h2 class="text-lg font-semibold mb-1">오류</h2>
          <p class="text-sm text-muted-foreground">{{ errorMsg }}</p>
        </div>

      </div>
    </div>
  </div>
</template>
