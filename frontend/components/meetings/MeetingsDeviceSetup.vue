<script setup lang="ts">
const props = defineProps<{
  roomName: string
}>()

const emit = defineEmits<{
  join: [opts: { cameraEnabled: boolean; micEnabled: boolean; selectedCameraId?: string; selectedMicId?: string }]
  cancel: []
}>()

// 초기화 상태
const phase = ref<'requesting' | 'ready' | 'denied' | 'no-device'>('requesting')

// 장치 목록
const cameras = ref<MediaDeviceInfo[]>([])
const microphones = ref<MediaDeviceInfo[]>([])
const selectedCameraId = ref('')
const selectedMicId = ref('')

// 미디어 상태
const cameraOn = ref(true)
const micOn = ref(true)
const previewStream = ref<MediaStream | null>(null)
const videoEl = ref<HTMLVideoElement | null>(null)

// 마이크 레벨
const micLevel = ref(0)
let audioCtx: AudioContext | null = null
let analyser: AnalyserNode | null = null
let animFrameId: number | null = null

// 브라우저 감지
const browserName = ref('')

function detectBrowser(): string {
  if (!import.meta.client) return ''
  const ua = navigator.userAgent
  if (ua.includes('Edg/')) return 'Edge'
  if (ua.includes('Chrome/')) return 'Chrome'
  if (ua.includes('Firefox/')) return 'Firefox'
  if (ua.includes('Safari/') && !ua.includes('Chrome')) return 'Safari'
  return ''
}

const permissionGuide = computed(() => {
  const guides: Record<string, string> = {
    Chrome: '주소창 왼쪽 자물쇠(또는 설정) 아이콘 → 사이트 설정 → 카메라/마이크 → "허용"으로 변경 후 새로고침',
    Edge: '주소창 왼쪽 자물쇠(또는 설정) 아이콘 → 사이트 설정 → 카메라/마이크 → "허용"으로 변경 후 새로고침',
    Firefox: '주소창의 카메라/마이크 아이콘 클릭 → 차단 해제 후 새로고침',
    Safari: 'Safari → 환경설정 → 웹사이트 → 카메라/마이크 → 이 사이트 "허용" 후 새로고침',
  }
  return guides[browserName.value] || '브라우저 설정에서 이 사이트의 카메라/마이크 권한을 허용해 주세요.'
})

// ── 1단계: 권한 요청 (getUserMedia 호출 → 브라우저 권한 팝업) ──
async function requestPermissions() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true })
    // 권한 승인됨 → 스트림으로 바로 미리보기
    previewStream.value = stream
    if (videoEl.value) {
      videoEl.value.srcObject = stream
    }
    startMicLevel(stream)

    // 권한 획득 후 장치 목록 열거 (label 포함)
    await enumerateDevices()

    // 현재 스트림의 장치 ID를 선택값에 반영
    const videoTrack = stream.getVideoTracks()[0]
    const audioTrack = stream.getAudioTracks()[0]
    if (videoTrack) {
      const settings = videoTrack.getSettings()
      if (settings.deviceId) selectedCameraId.value = settings.deviceId
    }
    if (audioTrack) {
      const settings = audioTrack.getSettings()
      if (settings.deviceId) selectedMicId.value = settings.deviceId
    }

    phase.value = 'ready'
  } catch (err: any) {
    if (err.name === 'NotAllowedError') {
      phase.value = 'denied'
    } else {
      // 장치 없음 등 — 카메라/마이크 없이도 참여 가능하게
      phase.value = 'no-device'
      cameraOn.value = false
      micOn.value = false
    }
  }
}

// 장치 열거
async function enumerateDevices() {
  const devices = await navigator.mediaDevices.enumerateDevices()
  cameras.value = devices.filter(d => d.kind === 'videoinput')
  microphones.value = devices.filter(d => d.kind === 'audioinput')
  if (cameras.value.length && !selectedCameraId.value) {
    selectedCameraId.value = cameras.value[0].deviceId
  }
  if (microphones.value.length && !selectedMicId.value) {
    selectedMicId.value = microphones.value[0].deviceId
  }
}

// 장치 변경 시 스트림 교체
async function switchDevice() {
  stopPreview()

  const constraints: MediaStreamConstraints = {}
  if (cameraOn.value && selectedCameraId.value) {
    constraints.video = { deviceId: { exact: selectedCameraId.value } }
  } else if (cameraOn.value) {
    constraints.video = true
  }
  if (micOn.value && selectedMicId.value) {
    constraints.audio = { deviceId: { exact: selectedMicId.value } }
  } else if (micOn.value) {
    constraints.audio = true
  }

  if (!constraints.video && !constraints.audio) return

  try {
    const stream = await navigator.mediaDevices.getUserMedia(constraints)
    previewStream.value = stream
    if (videoEl.value && constraints.video) {
      videoEl.value.srcObject = stream
    }
    if (constraints.audio) {
      startMicLevel(stream)
    }
  } catch {
    // 특정 장치 실패 시 기본 장치로 재시도
    try {
      const fallback: MediaStreamConstraints = {}
      if (cameraOn.value) fallback.video = true
      if (micOn.value) fallback.audio = true
      if (!fallback.video && !fallback.audio) return
      const stream = await navigator.mediaDevices.getUserMedia(fallback)
      previewStream.value = stream
      if (videoEl.value && fallback.video) {
        videoEl.value.srcObject = stream
      }
      if (fallback.audio) {
        startMicLevel(stream)
      }
    } catch { /* 장치 접근 불가 */ }
  }
}

function stopPreview() {
  if (previewStream.value) {
    previewStream.value.getTracks().forEach(t => t.stop())
    previewStream.value = null
  }
  if (videoEl.value) {
    videoEl.value.srcObject = null
  }
  stopMicLevel()
}

// 마이크 레벨 미터
function startMicLevel(stream: MediaStream) {
  stopMicLevel()
  audioCtx = new AudioContext()
  analyser = audioCtx.createAnalyser()
  analyser.fftSize = 256
  const source = audioCtx.createMediaStreamSource(stream)
  source.connect(analyser)

  const dataArray = new Uint8Array(analyser.frequencyBinCount)

  function tick() {
    if (!analyser) return
    analyser.getByteTimeDomainData(dataArray)
    let sum = 0
    for (let i = 0; i < dataArray.length; i++) {
      const val = (dataArray[i] - 128) / 128
      sum += val * val
    }
    micLevel.value = Math.min(100, Math.sqrt(sum / dataArray.length) * 300)
    animFrameId = requestAnimationFrame(tick)
  }
  tick()
}

function stopMicLevel() {
  if (animFrameId !== null) {
    cancelAnimationFrame(animFrameId)
    animFrameId = null
  }
  if (audioCtx) {
    audioCtx.close()
    audioCtx = null
  }
  analyser = null
  micLevel.value = 0
}

// 스피커 테스트
function testSpeaker() {
  const ctx = new AudioContext()
  const osc = ctx.createOscillator()
  const gain = ctx.createGain()
  osc.frequency.value = 440
  gain.gain.value = 0.3
  osc.connect(gain)
  gain.connect(ctx.destination)
  osc.start()
  setTimeout(() => {
    osc.stop()
    ctx.close()
  }, 300)
}

// 장치 변경 시 스트림 교체
watch(selectedCameraId, () => { if (phase.value === 'ready' && cameraOn.value) switchDevice() })
watch(selectedMicId, () => { if (phase.value === 'ready' && micOn.value) switchDevice() })

watch(cameraOn, (on) => {
  if (phase.value !== 'ready') return
  if (on) {
    switchDevice()
  } else {
    if (previewStream.value) {
      previewStream.value.getVideoTracks().forEach(t => t.stop())
      if (videoEl.value) videoEl.value.srcObject = null
    }
  }
})

watch(micOn, (on) => {
  if (phase.value !== 'ready') return
  if (on) {
    switchDevice()
  } else {
    if (previewStream.value) {
      previewStream.value.getAudioTracks().forEach(t => t.stop())
    }
    stopMicLevel()
  }
})

function handleJoin() {
  stopPreview()
  emit('join', {
    cameraEnabled: cameraOn.value,
    micEnabled: micOn.value,
    selectedCameraId: selectedCameraId.value || undefined,
    selectedMicId: selectedMicId.value || undefined,
  })
}

onMounted(() => {
  browserName.value = detectBrowser()
  requestPermissions()
})

onBeforeUnmount(() => {
  stopPreview()
})
</script>

<template>
  <div class="flex items-center justify-center min-h-screen bg-background p-4">
    <div class="w-full max-w-2xl">
      <div class="text-center mb-6">
        <h1 class="text-xl font-bold">{{ roomName }}</h1>
        <p class="text-sm text-muted-foreground mt-1">회의 참여 전 장치를 확인하세요</p>
      </div>

      <!-- 권한 요청 중 -->
      <div v-if="phase === 'requesting'" class="text-center py-16">
        <div class="inline-block h-10 w-10 animate-spin rounded-full border-4 border-primary border-r-transparent mb-4" />
        <p class="text-muted-foreground">카메라/마이크 권한을 요청하고 있습니다...</p>
        <p class="text-xs text-muted-foreground mt-2">브라우저의 권한 팝업에서 "허용"을 눌러주세요</p>
      </div>

      <!-- 권한 거부됨 -->
      <div v-else-if="phase === 'denied'" class="max-w-md mx-auto">
        <div class="rounded-lg border bg-card p-6">
          <div class="flex gap-3">
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-6 w-6 text-amber-500 shrink-0 mt-0.5">
              <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
              <line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
            </svg>
            <div>
              <h3 class="font-semibold mb-1">카메라/마이크 권한이 필요합니다</h3>
              <p class="text-sm text-muted-foreground mb-3">{{ permissionGuide }}</p>
              <div class="flex gap-2">
                <button
                  @click="phase = 'requesting'; requestPermissions()"
                  class="px-4 py-2 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
                >
                  다시 시도
                </button>
                <button
                  @click="phase = 'no-device'; cameraOn = false; micOn = false"
                  class="px-4 py-2 text-sm rounded-md border hover:bg-accent transition-colors"
                >
                  권한 없이 참여
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 장치 없음 (권한 없이 참여 가능) -->
      <div v-else-if="phase === 'no-device'" class="max-w-md mx-auto">
        <div class="rounded-lg border bg-card p-6 text-center">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-10 w-10 mx-auto mb-3 text-muted-foreground opacity-50">
            <path d="M10.66 6H14a2 2 0 0 1 2 2v2.34l1 1L22 8v8" />
            <path d="M16 16a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h2l10 10Z" />
            <line x1="2" y1="2" x2="22" y2="22" />
          </svg>
          <h3 class="font-semibold mb-1">장치를 사용할 수 없습니다</h3>
          <p class="text-sm text-muted-foreground mb-4">카메라/마이크 없이 회의에 참여합니다</p>
          <div class="flex justify-center gap-2">
            <button
              @click="emit('cancel')"
              class="px-4 py-2 text-sm rounded-md border hover:bg-accent transition-colors"
            >
              취소
            </button>
            <button
              @click="handleJoin"
              class="px-6 py-2 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
            >
              그래도 참여
            </button>
          </div>
        </div>
      </div>

      <!-- 장치 테스트 (권한 승인 후) -->
      <template v-else-if="phase === 'ready'">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <!-- 카메라 미리보기 -->
          <div class="rounded-lg border bg-card overflow-hidden">
            <div class="aspect-video bg-muted relative">
              <video
                ref="videoEl"
                autoplay
                playsinline
                muted
                class="absolute inset-0 w-full h-full object-cover"
                :class="{ hidden: !cameraOn || !previewStream }"
                style="transform: scaleX(-1)"
              />
              <div
                v-if="!cameraOn || !previewStream"
                class="absolute inset-0 flex items-center justify-center"
              >
                <div class="text-center text-muted-foreground">
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-10 w-10 mx-auto mb-2 opacity-40">
                    <path d="M10.66 6H14a2 2 0 0 1 2 2v2.34l1 1L22 8v8" />
                    <path d="M16 16a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h2l10 10Z" />
                    <line x1="2" y1="2" x2="22" y2="22" />
                  </svg>
                  <p class="text-sm">카메라 꺼짐</p>
                </div>
              </div>
            </div>

            <!-- 카메라 토글 + 선택 -->
            <div class="p-3 space-y-2">
              <div class="flex items-center gap-2">
                <button
                  @click="cameraOn = !cameraOn"
                  class="inline-flex items-center justify-center h-9 w-9 rounded-full transition-colors shrink-0"
                  :class="cameraOn ? 'bg-primary text-primary-foreground' : 'bg-muted'"
                >
                  <svg v-if="cameraOn" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
                    <path d="m22 8-6 4 6 4V8Z" /><rect width="14" height="12" x="1" y="6" rx="2" ry="2" />
                  </svg>
                  <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
                    <path d="M10.66 6H14a2 2 0 0 1 2 2v2.34l1 1L22 8v8" />
                    <path d="M16 16a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h2l10 10Z" />
                    <line x1="2" y1="2" x2="22" y2="22" />
                  </svg>
                </button>
                <select
                  v-model="selectedCameraId"
                  class="flex-1 text-sm px-2 py-1.5 rounded-md border bg-background focus:outline-none focus:ring-2 focus:ring-ring truncate"
                  :disabled="cameras.length === 0"
                >
                  <option v-if="cameras.length === 0" value="">카메라 없음</option>
                  <option v-for="cam in cameras" :key="cam.deviceId" :value="cam.deviceId">
                    {{ cam.label || `카메라 ${cameras.indexOf(cam) + 1}` }}
                  </option>
                </select>
              </div>
            </div>
          </div>

          <!-- 마이크 + 스피커 -->
          <div class="rounded-lg border bg-card">
            <div class="p-4 space-y-4">
              <!-- 마이크 -->
              <div>
                <label class="text-sm font-medium mb-2 block">마이크</label>
                <div class="flex items-center gap-2">
                  <button
                    @click="micOn = !micOn"
                    class="inline-flex items-center justify-center h-9 w-9 rounded-full transition-colors shrink-0"
                    :class="micOn ? 'bg-primary text-primary-foreground' : 'bg-muted'"
                  >
                    <svg v-if="micOn" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
                      <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
                      <path d="M19 10v2a7 7 0 0 1-14 0v-2" /><line x1="12" y1="19" x2="12" y2="22" />
                    </svg>
                    <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
                      <line x1="2" y1="2" x2="22" y2="22" />
                      <path d="M18.89 13.23A7.12 7.12 0 0 0 19 12v-2" />
                      <path d="M5 10v2a7 7 0 0 0 12 5" />
                      <path d="M15 9.34V5a3 3 0 0 0-5.68-1.33" />
                      <path d="M9 9v3a3 3 0 0 0 5.12 2.12" />
                      <line x1="12" y1="19" x2="12" y2="22" />
                    </svg>
                  </button>
                  <select
                    v-model="selectedMicId"
                    class="flex-1 text-sm px-2 py-1.5 rounded-md border bg-background focus:outline-none focus:ring-2 focus:ring-ring truncate"
                    :disabled="microphones.length === 0"
                  >
                    <option v-if="microphones.length === 0" value="">마이크 없음</option>
                    <option v-for="mic in microphones" :key="mic.deviceId" :value="mic.deviceId">
                      {{ mic.label || `마이크 ${microphones.indexOf(mic) + 1}` }}
                    </option>
                  </select>
                </div>

                <!-- 마이크 레벨 미터 -->
                <div class="mt-2 h-2 rounded-full bg-muted overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all duration-75 bg-green-500"
                    :style="{ width: `${micLevel}%` }"
                  />
                </div>
                <p class="text-xs text-muted-foreground mt-1">
                  {{ micOn && micLevel > 5 ? '마이크가 작동 중입니다' : micOn ? '말해보세요...' : '마이크 꺼짐' }}
                </p>
              </div>

              <!-- 스피커 테스트 -->
              <div>
                <label class="text-sm font-medium mb-2 block">스피커</label>
                <button
                  @click="testSpeaker"
                  class="inline-flex items-center gap-2 px-3 py-1.5 text-sm rounded-md border hover:bg-accent transition-colors"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
                    <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
                    <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
                    <path d="M19.07 4.93a10 10 0 0 1 0 14.14" />
                  </svg>
                  테스트 사운드 재생
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 참여 / 취소 버튼 -->
        <div class="flex justify-center gap-3 mt-6">
          <button
            @click="emit('cancel')"
            class="px-5 py-2.5 text-sm font-medium rounded-md border hover:bg-accent transition-colors"
          >
            취소
          </button>
          <button
            @click="handleJoin"
            class="px-8 py-2.5 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            회의 참여
          </button>
        </div>
      </template>
    </div>
  </div>
</template>
