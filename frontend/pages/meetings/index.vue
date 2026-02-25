<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { user } = useAuth()
const {
  rooms,
  loading,
  error,
  fetchRooms,
  createRoom,
  deleteRoom,
} = useMeetings()

const showCreateModal = ref(false)
const newRoomName = ref('')
const creating = ref(false)

onMounted(() => {
  fetchRooms()
})

function openMeetingWindow(roomName: string, shareToken: string, isHost: boolean) {
  const params = new URLSearchParams({
    ...(shareToken ? { st: shareToken } : {}),
    ...(isHost ? { host: '1' } : {}),
  })
  const qs = params.toString()
  const url = `/meetings/room/${encodeURIComponent(roomName)}${qs ? '?' + qs : ''}`
  window.open(url, `meeting-${roomName}`, 'width=1280,height=800')
}

async function handleCreate() {
  if (!newRoomName.value.trim()) return
  creating.value = true
  try {
    const room = await createRoom(newRoomName.value.trim())
    showCreateModal.value = false
    newRoomName.value = ''
    // 생성 후 바로 새 창에서 참여 (동기적으로 window.open)
    openMeetingWindow(room.name, room.share_token, room.is_host)
  } catch (e: any) {
    alert(e?.data?.detail || '회의실 생성 실패')
  } finally {
    creating.value = false
  }
}

function handleJoin(name: string) {
  if (!user.value) return
  const roomInfo = rooms.value.find(r => r.name === name)
  openMeetingWindow(
    name,
    roomInfo?.share_token || '',
    roomInfo?.is_host ?? false,
  )
}

async function handleDelete(name: string) {
  if (!confirm(`"${name}" 회의실을 삭제하시겠습니까?`)) return
  try {
    await deleteRoom(name)
  } catch (e: any) {
    alert(e?.data?.detail || '삭제 실패')
  }
}
</script>

<template>
  <ClientOnly>
    <template #fallback>
      <div class="flex items-center justify-center h-full">
        <div class="text-muted-foreground">로딩 중...</div>
      </div>
    </template>

    <!-- 로비 -->
    <div class="max-w-4xl mx-auto px-4 py-6 sm:py-8">
      <div
        v-if="error"
        class="mb-4 p-3 rounded-lg bg-destructive/10 text-destructive text-sm"
      >
        {{ error }}
      </div>

      <MeetingsList
        :rooms="rooms"
        :loading="loading"
        @create="showCreateModal = true"
        @join="handleJoin"
        @delete="handleDelete"
      />

      <!-- 회의실 생성 모달 -->
      <Teleport to="body">
        <div
          v-if="showCreateModal"
          class="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          @click.self="showCreateModal = false"
        >
          <div class="bg-background rounded-lg border shadow-lg w-full max-w-sm mx-4 p-6">
            <h3 class="text-lg font-semibold mb-4">새 회의실</h3>
            <form @submit.prevent="handleCreate">
              <label class="block text-sm font-medium mb-1.5">회의실 이름</label>
              <input
                v-model="newRoomName"
                type="text"
                placeholder="예: 주간회의"
                class="w-full px-3 py-2 rounded-md border bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                autofocus
              />
              <p class="text-xs text-muted-foreground mt-2">최대 10명까지 참여할 수 있습니다</p>
              <div class="flex justify-end gap-2 mt-5">
                <button
                  type="button"
                  @click="showCreateModal = false"
                  class="px-4 py-2 text-sm rounded-md border hover:bg-accent transition-colors"
                >
                  취소
                </button>
                <button
                  type="submit"
                  :disabled="creating || !newRoomName.trim()"
                  class="px-4 py-2 text-sm rounded-md bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50"
                >
                  {{ creating ? '생성 중...' : '생성 및 참여' }}
                </button>
              </div>
            </form>
          </div>
        </div>
      </Teleport>
    </div>
  </ClientOnly>
</template>
