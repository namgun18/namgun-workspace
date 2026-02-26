<script setup lang="ts">
import { timeAgo } from '~/lib/date'

interface RecentPost {
  id: string
  board_id: string
  title: string
  author: { display_name: string | null; username: string } | null
  comment_count: number
  is_pinned: boolean
  is_must_read: boolean
  created_at: string
  board_name: string
}

const posts = ref<RecentPost[]>([])
const loading = ref(true)

async function fetchRecentPosts() {
  try {
    posts.value = await $fetch<RecentPost[]>('/api/board/recent-posts', {
      params: { limit: 5 },
    })
  } catch {
    // silent
  } finally {
    loading.value = false
  }
}

onMounted(fetchRecentPosts)
</script>

<template>
  <UiCard class="col-span-1 lg:col-span-2">
    <UiCardHeader class="pb-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4 text-orange-500" aria-hidden="true">
            <rect x="3" y="3" width="18" height="18" rx="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" />
          </svg>
          <UiCardTitle class="text-base">{{ $t('dashboard.recentBoard.title') }}</UiCardTitle>
        </div>
        <NuxtLink to="/board" class="text-xs text-primary hover:underline">{{ $t('common.viewAll') }}</NuxtLink>
      </div>
    </UiCardHeader>
    <UiCardContent>
      <div v-if="loading" class="space-y-3">
        <div v-for="i in 3" :key="i" class="flex gap-3">
          <UiSkeleton class="h-4 w-20 shrink-0" />
          <UiSkeleton class="h-4 flex-1" />
        </div>
      </div>

      <p v-else-if="posts.length === 0" class="text-sm text-muted-foreground">
        {{ $t('dashboard.recentBoard.empty') }}
      </p>

      <div v-else class="space-y-1">
        <NuxtLink
          v-for="p in posts"
          :key="p.id"
          :to="`/board/${p.board_id}/${p.id}`"
          class="flex items-start gap-3 rounded-md px-2 py-2 -mx-2 hover:bg-accent/50 transition-colors"
        >
          <div class="min-w-0 flex-1">
            <div class="flex items-center gap-1.5">
              <UiBadge v-if="p.is_pinned" variant="secondary" class="text-[10px] py-0 shrink-0">{{ $t('common.notice') }}</UiBadge>
              <UiBadge v-if="p.is_must_read" variant="destructive" class="text-[10px] py-0 shrink-0">{{ $t('common.mustRead') }}</UiBadge>
              <span class="text-sm truncate">{{ p.title }}</span>
              <span v-if="p.comment_count > 0" class="text-xs text-primary shrink-0">[{{ p.comment_count }}]</span>
            </div>
            <div class="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
              <span>{{ p.board_name }}</span>
              <span>&middot;</span>
              <span>{{ p.author?.display_name || p.author?.username }}</span>
              <span>&middot;</span>
              <span>{{ timeAgo(p.created_at) }}</span>
            </div>
          </div>
        </NuxtLink>
      </div>
    </UiCardContent>
  </UiCard>
</template>
