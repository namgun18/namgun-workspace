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

async function handleCreate(payload: {
  name: string
  invitees: Array<{ type: string; user_id?: string; username?: string; display_name?: string; email?: string }>
  scheduled_at: string | null
  duration_minutes: number
}) {
  try {
    const room = await createRoom(payload.name, {
      invitees: payload.invitees,
      scheduled_at: payload.scheduled_at,
      duration_minutes: payload.duration_minutes,
    })
    showCreateModal.value = false
    openMeetingWindow(room.name, room.share_token, room.is_host)
  } catch (e: any) {
    alert(e?.data?.detail || '회의실 생성 실패')
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

      <!-- 회의실 생성/초대 모달 -->
      <MeetingsInviteModal
        v-if="showCreateModal"
        @close="showCreateModal = false"
        @create="handleCreate"
      />
    </div>
  </ClientOnly>
</template>
