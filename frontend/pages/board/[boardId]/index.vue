<script setup lang="ts">
definePageMeta({ layout: 'default' })

const route = useRoute()
const router = useRouter()
const boardId = route.params.boardId as string

const {
  init, cleanup, currentBoard, posts, pinnedPosts, pagination,
  selectedCategory, sortBy, loadingPosts,
  selectBoard, goToPage, setCategory, setSort,
  fetchBoards,
} = useBoard()
const { user } = useAuth()

onMounted(async () => {
  await init()
  await selectBoard(boardId)
})

onUnmounted(() => {
  cleanup()
})

const totalPages = computed(() =>
  Math.max(1, Math.ceil(pagination.value.total / pagination.value.page_size))
)

const pageNumbers = computed(() => {
  const total = totalPages.value
  const current = pagination.value.page
  const pages: (number | '...')[] = []

  if (total <= 7) {
    for (let i = 1; i <= total; i++) pages.push(i)
  } else {
    pages.push(1)
    if (current > 3) pages.push('...')
    const start = Math.max(2, current - 1)
    const end = Math.min(total - 1, current + 1)
    for (let i = start; i <= end; i++) pages.push(i)
    if (current < total - 2) pages.push('...')
    pages.push(total)
  }
  return pages
})

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  const isToday = d.toDateString() === now.toDateString()
  if (isToday) {
    return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' })
}
</script>

<template>
  <div class="max-w-5xl mx-auto px-4 py-6">
    <!-- Header -->
    <div class="flex items-center gap-3 mb-4">
      <NuxtLink to="/board" class="h-8 w-8 flex items-center justify-center rounded-md hover:bg-accent transition-colors">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </NuxtLink>
      <div class="flex-1">
        <h1 class="text-lg font-semibold">{{ currentBoard?.name || '게시판' }}</h1>
        <p v-if="currentBoard?.description" class="text-sm text-muted-foreground">{{ currentBoard.description }}</p>
      </div>
      <UiButton size="sm" @click="router.push(`/board/${boardId}/write`)">
        글쓰기
      </UiButton>
    </div>

    <!-- Category tabs + sort -->
    <div class="flex items-center justify-between mb-3 flex-wrap gap-2">
      <BoardCategoryTabs
        v-if="currentBoard?.categories && currentBoard.categories.length > 0"
        :categories="currentBoard.categories"
        :selected="selectedCategory"
        @select="setCategory"
      />
      <div v-else />

      <div class="flex items-center gap-1 text-sm">
        <button
          v-for="s in [{ value: 'latest', label: '최신' }, { value: 'views', label: '조회' }, { value: 'comments', label: '댓글' }] as const"
          :key="s.value"
          @click="setSort(s.value)"
          class="px-2 py-1 rounded-md transition-colors"
          :class="sortBy === s.value ? 'bg-accent font-medium' : 'text-muted-foreground hover:bg-accent/50'"
        >
          {{ s.label }}
        </button>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loadingPosts" class="space-y-2">
      <div v-for="i in 5" :key="i" class="h-12 bg-muted/50 rounded animate-pulse" />
    </div>

    <template v-else>
      <!-- Post table -->
      <BoardPostTable :pinned="pinnedPosts" :posts="posts" :board-id="boardId" />

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="flex justify-center mt-6">
        <BoardPagination
          :current="pagination.page"
          :total="totalPages"
          :pages="pageNumbers"
          @go="goToPage"
        />
      </div>
    </template>
  </div>
</template>
