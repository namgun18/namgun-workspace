<script setup lang="ts">
import { Track } from 'livekit-client'

const props = defineProps<{
  identity: string
  name: string
  videoTrack: any | null
  audioTrack: any | null
  screenTrack: any | null
  isMuted: boolean
  isLocal: boolean
}>()

const videoEl = ref<HTMLVideoElement | null>(null)
const screenEl = ref<HTMLVideoElement | null>(null)
const audioEl = ref<HTMLAudioElement | null>(null)

function attachTrack(track: any, el: HTMLMediaElement | null) {
  if (track && el) {
    track.attach(el)
  }
}

function detachTrack(track: any, el: HTMLMediaElement | null) {
  if (track && el) {
    track.detach(el)
  }
}

watch(() => props.videoTrack, (newT, oldT) => {
  if (oldT) detachTrack(oldT, videoEl.value)
  if (newT) attachTrack(newT, videoEl.value)
}, { immediate: true })

watch(() => props.screenTrack, (newT, oldT) => {
  if (oldT) detachTrack(oldT, screenEl.value)
  if (newT) attachTrack(newT, screenEl.value)
}, { immediate: true })

watch(() => props.audioTrack, (newT, oldT) => {
  if (oldT && !props.isLocal) detachTrack(oldT, audioEl.value)
  if (newT && !props.isLocal) attachTrack(newT, audioEl.value)
}, { immediate: true })

onMounted(() => {
  if (props.videoTrack) attachTrack(props.videoTrack, videoEl.value)
  if (props.screenTrack) attachTrack(props.screenTrack, screenEl.value)
  if (props.audioTrack && !props.isLocal) attachTrack(props.audioTrack, audioEl.value)
})

onBeforeUnmount(() => {
  if (props.videoTrack) detachTrack(props.videoTrack, videoEl.value)
  if (props.screenTrack) detachTrack(props.screenTrack, screenEl.value)
  if (props.audioTrack) detachTrack(props.audioTrack, audioEl.value)
})
</script>

<template>
  <div class="relative rounded-lg overflow-hidden bg-muted" :class="screenTrack ? 'aspect-auto h-full' : 'aspect-video'">
    <!-- 카메라 비디오 -->
    <video
      ref="videoEl"
      autoplay
      playsinline
      :muted="isLocal"
      class="absolute inset-0 w-full h-full object-cover"
      :class="{ hidden: !videoTrack }"
    />

    <!-- 비디오 없을 때 아바타 -->
    <div
      v-if="!videoTrack"
      class="absolute inset-0 flex items-center justify-center"
    >
      <div class="h-16 w-16 rounded-full bg-primary/20 flex items-center justify-center text-2xl font-bold text-primary">
        {{ name.charAt(0).toUpperCase() }}
      </div>
    </div>

    <!-- 이름 + 상태 표시 -->
    <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2">
      <div class="flex items-center gap-1.5">
        <span class="text-white text-sm font-medium truncate">
          {{ name }}{{ isLocal ? ` ${$t('meetings.participant.me')}` : '' }}
        </span>
        <svg
          v-if="isMuted"
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
          class="h-3.5 w-3.5 text-red-400 shrink-0"
        >
          <line x1="1" y1="1" x2="23" y2="23" />
          <path d="M9 9v3a3 3 0 0 0 5.12 2.12M15 9.34V4a3 3 0 0 0-5.94-.6" />
          <path d="M17 16.95A7 7 0 0 1 5 12v-2m14 0v2c0 .76-.12 1.5-.34 2.18" />
          <line x1="12" y1="19" x2="12" y2="23" /><line x1="8" y1="23" x2="16" y2="23" />
        </svg>
      </div>
    </div>

    <!-- 화면공유 (별도 오버레이) -->
    <video
      v-if="screenTrack"
      ref="screenEl"
      autoplay
      playsinline
      muted
      class="absolute inset-0 w-full h-full object-contain bg-black/90"
    />

    <!-- 오디오 (리모트만) -->
    <audio ref="audioEl" autoplay :muted="isLocal" class="hidden" />
  </div>
</template>
