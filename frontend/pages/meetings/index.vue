<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { t } = useI18n()
const { appName, demoMode } = useAppConfig()
useHead({ title: computed(() => `${t('nav.meetings')} | ${appName.value}`) })

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
  if (!demoMode.value) fetchRooms()
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
    alert(e?.data?.detail || t('meetings.index.createFail'))
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
  if (!confirm(t('meetings.index.deleteConfirm', { name }))) return
  try {
    await deleteRoom(name)
  } catch (e: any) {
    alert(e?.data?.detail || t('meetings.index.deleteFail'))
  }
}
</script>

<template>
  <!-- Demo mode placeholder -->
  <div v-if="demoMode" class="h-full flex items-center justify-center px-4">
    <div class="text-center max-w-md space-y-4">
      <div class="mx-auto w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="h-8 w-8 text-primary">
          <polygon points="23 7 16 12 23 17 23 7" /><rect width="15" height="14" x="1" y="5" rx="2" ry="2" />
        </svg>
      </div>
      <h2 class="text-xl font-bold">{{ $t('nav.meetings') }}</h2>
      <p class="text-muted-foreground text-sm leading-relaxed">{{ $t('demo.meetingsDescription') }}</p>
      <div class="border rounded-lg p-4 text-left text-sm space-y-2 bg-card">
        <div class="flex items-center gap-2"><span class="text-primary">&#10003;</span> {{ $t('demo.meetingsFeature1') }}</div>
        <div class="flex items-center gap-2"><span class="text-primary">&#10003;</span> {{ $t('demo.meetingsFeature2') }}</div>
        <div class="flex items-center gap-2"><span class="text-primary">&#10003;</span> {{ $t('demo.meetingsFeature3') }}</div>
      </div>
    </div>
  </div>

  <ClientOnly v-else>
    <template #fallback>
      <div class="flex items-center justify-center h-full">
        <div class="text-muted-foreground">{{ $t('common.loading') }}</div>
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
