<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { init, cleanup, boards, loadingBoards, mustReadPosts, fetchMustRead } = useBoard()
const { user } = useAuth()

const showCreateModal = ref(false)

onMounted(async () => {
  await init()
})

onUnmounted(() => {
  cleanup()
})
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-6">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-xl font-semibold">게시판</h1>
      <UiButton v-if="user?.is_admin" size="sm" @click="showCreateModal = true">
        게시판 만들기
      </UiButton>
    </div>

    <!-- Must-read banner -->
    <div
      v-if="mustReadPosts.length > 0"
      class="mb-6 rounded-lg border border-red-200 bg-red-50 dark:border-red-800 dark:bg-red-950 p-4"
    >
      <div class="flex items-center gap-2 mb-2">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-5 w-5 text-red-600">
          <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
        <span class="text-sm font-semibold text-red-800 dark:text-red-200">
          미확인 필독 게시글 {{ mustReadPosts.length }}건
        </span>
      </div>
      <div class="space-y-1">
        <NuxtLink
          v-for="p in mustReadPosts.slice(0, 5)"
          :key="p.id"
          :to="`/board/${p.board_id}/${p.id}`"
          class="block text-sm text-red-700 dark:text-red-300 hover:underline truncate"
        >
          {{ p.title }}
        </NuxtLink>
        <p v-if="mustReadPosts.length > 5" class="text-xs text-red-600">
          외 {{ mustReadPosts.length - 5 }}건
        </p>
      </div>
    </div>

    <!-- Board list -->
    <div v-if="loadingBoards" class="space-y-3">
      <div v-for="i in 3" :key="i" class="h-24 bg-muted/50 rounded-lg animate-pulse" />
    </div>

    <div v-else-if="boards.length === 0" class="text-center py-16 text-muted-foreground">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="h-12 w-12 mx-auto mb-3 opacity-50">
        <rect x="3" y="3" width="18" height="18" rx="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" />
      </svg>
      <p>게시판이 없습니다</p>
      <p v-if="user?.is_admin" class="text-sm mt-1">게시판을 만들어 보세요</p>
    </div>

    <div v-else class="grid gap-3 sm:grid-cols-2">
      <BoardCard v-for="board in boards" :key="board.id" :board="board" />
    </div>

    <!-- Create board modal -->
    <BoardCreateModal v-if="showCreateModal" @close="showCreateModal = false" />
  </div>
</template>
