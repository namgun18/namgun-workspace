<script setup lang="ts">
import { timeAgo } from '~/lib/date'

interface NoticePost {
  id: string
  board_id: string
  title: string
  is_must_read: boolean
  created_at: string
  board_name: string
}

const notices = ref<NoticePost[]>([])
const loading = ref(true)

async function fetchNotices() {
  try {
    notices.value = await $fetch<NoticePost[]>('/api/board/notices', {
      params: { limit: 5 },
    })
  } catch {
    // silent
  } finally {
    loading.value = false
  }
}

onMounted(fetchNotices)
</script>

<template>
  <UiCard>
    <UiCardHeader class="pb-3">
      <div class="flex items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 text-red-500">
          <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" /><line x1="12" y1="9" x2="12" y2="13" /><line x1="12" y1="17" x2="12.01" y2="17" />
        </svg>
        <UiCardTitle class="text-base">공지사항</UiCardTitle>
      </div>
    </UiCardHeader>
    <UiCardContent>
      <div v-if="loading" class="space-y-2">
        <UiSkeleton v-for="i in 3" :key="i" class="h-4 w-full" />
      </div>

      <p v-else-if="notices.length === 0" class="text-sm text-muted-foreground">
        공지사항이 없습니다
      </p>

      <div v-else class="space-y-1">
        <NuxtLink
          v-for="n in notices"
          :key="n.id"
          :to="`/board/${n.board_id}/${n.id}`"
          class="flex items-start gap-2 rounded-md px-2 py-1.5 -mx-2 hover:bg-accent/50 transition-colors"
        >
          <UiBadge v-if="n.is_must_read" variant="destructive" class="text-[10px] py-0 shrink-0 mt-0.5">필독</UiBadge>
          <span v-else class="mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
          <div class="min-w-0 flex-1">
            <p class="text-sm truncate">{{ n.title }}</p>
            <span class="text-xs text-muted-foreground">{{ n.board_name }} &middot; {{ timeAgo(n.created_at) }}</span>
          </div>
        </NuxtLink>
      </div>
    </UiCardContent>
  </UiCard>
</template>
