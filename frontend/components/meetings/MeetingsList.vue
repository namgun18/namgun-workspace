<script setup lang="ts">
const props = defineProps<{
  rooms: Array<{
    name: string
    num_participants: number
    max_participants: number
    creation_time: number
    share_token: string
    is_host: boolean
    pending_count: number
  }>
  loading: boolean
}>()

const emit = defineEmits<{
  join: [name: string]
  delete: [name: string]
  create: []
}>()

const copiedToken = ref<string | null>(null)

function formatTime(epoch: number) {
  if (!epoch) return ''
  return new Date(epoch * 1000).toLocaleString('ko-KR')
}

function getShareUrl(token: string) {
  return `${window.location.origin}/meetings/join/${token}`
}

async function copyLink(token: string) {
  try {
    await navigator.clipboard.writeText(getShareUrl(token))
    copiedToken.value = token
    setTimeout(() => { copiedToken.value = null }, 2000)
  } catch { /* fallback 불필요 */ }
}
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h2 class="text-xl font-semibold">회의실 목록</h2>
      <button
        @click="emit('create')"
        class="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
          <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
        </svg>
        새 회의실
      </button>
    </div>

    <div v-if="loading" class="text-center py-12 text-muted-foreground">
      불러오는 중...
    </div>

    <div v-else-if="rooms.length === 0" class="text-center py-12">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="h-12 w-12 mx-auto text-muted-foreground/50 mb-3">
        <path d="m22 8-6 4 6 4V8Z" /><rect width="14" height="12" x="1" y="6" rx="2" ry="2" />
      </svg>
      <p class="text-muted-foreground">활성 회의실이 없습니다</p>
      <p class="text-sm text-muted-foreground/70 mt-1">새 회의실을 만들어 시작하세요</p>
    </div>

    <div v-else class="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
      <div
        v-for="room in rooms"
        :key="room.name"
        class="rounded-lg border bg-card p-4 hover:shadow-md transition-shadow"
      >
        <div class="flex items-start justify-between mb-3">
          <div>
            <div class="flex items-center gap-2">
              <h3 class="font-semibold text-base">{{ room.name }}</h3>
              <span v-if="room.is_host" class="text-[10px] font-medium px-1.5 py-0.5 rounded bg-primary/10 text-primary">호스트</span>
            </div>
            <p class="text-xs text-muted-foreground mt-0.5">{{ formatTime(room.creation_time) }}</p>
          </div>
          <div class="flex flex-col items-end gap-1">
            <span class="inline-flex items-center gap-1 text-xs font-medium px-2 py-1 rounded-full"
              :class="room.num_participants > 0 ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400' : 'bg-muted text-muted-foreground'"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-3 w-3">
                <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" />
              </svg>
              {{ room.num_participants }}/{{ room.max_participants }}
            </span>
            <span v-if="room.pending_count > 0" class="text-[10px] px-1.5 py-0.5 rounded-full bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">
              대기 {{ room.pending_count }}명
            </span>
          </div>
        </div>

        <div class="flex gap-2">
          <button
            @click="emit('join', room.name)"
            class="flex-1 px-3 py-1.5 text-sm font-medium rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors"
          >
            참여
          </button>
          <button
            v-if="room.share_token"
            @click="copyLink(room.share_token)"
            class="px-3 py-1.5 text-sm font-medium rounded-md border hover:bg-accent transition-colors"
            :title="getShareUrl(room.share_token)"
          >
            {{ copiedToken === room.share_token ? '복사됨' : '링크 복사' }}
          </button>
          <button
            @click="emit('delete', room.name)"
            class="px-3 py-1.5 text-sm font-medium rounded-md border text-destructive hover:bg-destructive/10 transition-colors"
          >
            삭제
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
