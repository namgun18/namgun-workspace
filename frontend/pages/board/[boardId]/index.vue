<script setup lang="ts">
definePageMeta({ layout: 'default' })

const route = useRoute()
const router = useRouter()
const boardId = route.params.boardId as string

const {
  init, cleanup, currentBoard, posts, pinnedPosts, pagination,
  selectedCategory, sortBy, loadingPosts,
  selectBoard, goToPage, setCategory, setSort,
} = useBoard()

const showMobileSidebar = ref(false)

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
</script>

<template>
  <div class="flex h-full overflow-hidden relative">
    <!-- Mobile sidebar overlay -->
    <div
      v-if="showMobileSidebar"
      class="md:hidden fixed inset-0 z-30 bg-black/40"
      @click="showMobileSidebar = false"
    />

    <!-- Sidebar -->
    <div
      class="shrink-0 h-full z-30 transition-transform duration-200
        fixed md:relative
        w-64 md:w-56
        bg-background md:bg-transparent
        shadow-xl md:shadow-none"
      :class="showMobileSidebar ? 'translate-x-0' : '-translate-x-full md:translate-x-0'"
    >
      <BoardSidebar @navigate="showMobileSidebar = false" />
    </div>

    <!-- Main content -->
    <div class="flex-1 flex flex-col min-w-0 min-h-0">
      <!-- Command bar -->
      <div class="flex items-center gap-1.5 sm:gap-2 px-2 sm:px-4 py-2 border-b bg-background">
        <button
          @click="showMobileSidebar = !showMobileSidebar"
          class="md:hidden inline-flex items-center justify-center h-8 w-8 rounded-md hover:bg-accent transition-colors shrink-0"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
            <line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>

        <div class="flex-1 min-w-0">
          <h2 class="text-sm font-semibold truncate">{{ currentBoard?.name || '게시판' }}</h2>
          <p v-if="currentBoard?.description" class="text-xs text-muted-foreground truncate hidden sm:block">{{ currentBoard.description }}</p>
        </div>

        <UiButton size="sm" @click="router.push(`/board/${boardId}/write`)">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4 sm:mr-1">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          <span class="hidden sm:inline">글쓰기</span>
        </UiButton>
      </div>

      <!-- Category tabs + sort -->
      <div class="flex items-center justify-between px-2 sm:px-4 py-1.5 border-b bg-background flex-wrap gap-1">
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
            class="px-2 py-0.5 rounded-md text-xs transition-colors"
            :class="sortBy === s.value ? 'bg-accent font-medium' : 'text-muted-foreground hover:bg-accent/50'"
          >
            {{ s.label }}
          </button>
        </div>
      </div>

      <!-- Post list -->
      <div class="flex-1 overflow-auto">
        <div class="p-2 sm:p-4">
          <div v-if="loadingPosts" class="space-y-2">
            <div v-for="i in 8" :key="i" class="h-12 bg-muted/50 rounded animate-pulse" />
          </div>

          <template v-else>
            <BoardPostTable :pinned="pinnedPosts" :posts="posts" :board-id="boardId" />

            <div v-if="totalPages > 1" class="flex justify-center mt-4">
              <BoardPagination
                :current="pagination.page"
                :total="totalPages"
                :pages="pageNumbers"
                @go="goToPage"
              />
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>
