<script setup lang="ts">
import { timeAgo } from '~/lib/date'

definePageMeta({ layout: 'default' })

const { t } = useI18n()
const { appName } = useAppConfig()
useHead({ title: computed(() => `${t('nav.board')} | ${appName.value}`) })

const { init, cleanup, boards, loadingBoards, mustReadPosts, fetchBookmarks, searchPosts } = useBoard()
const { user } = useAuth()
const route = useRoute()

const showCreateModal = ref(false)
const showMobileSidebar = ref(false)

// Board index content: recent posts per board
interface BoardWithPosts {
  id: string
  name: string
  slug: string
  description: string | null
  recent_posts: Array<{
    id: string
    board_id: string
    title: string
    author: { display_name: string | null; username: string } | null
    comment_count: number
    is_pinned: boolean
    is_must_read: boolean
    has_attachments: boolean
    created_at: string
  }>
}

const boardsWithPosts = ref<BoardWithPosts[]>([])
const loadingContent = ref(true)

// Special views
const currentView = computed(() => route.query.view as string | undefined)

// Bookmarks
const bookmarks = ref<any[]>([])
const bookmarksPagination = ref({ total: 0, page: 1 })
const loadingBookmarks = ref(false)

// Search
const searchQuery = ref('')
const searchResults = ref<any[]>([])
const searchTotal = ref(0)
const searchLoading = ref(false)

async function fetchBoardsWithPosts() {
  loadingContent.value = true
  try {
    boardsWithPosts.value = await $fetch<BoardWithPosts[]>('/api/board/boards-with-posts', {
      params: { limit_per_board: 5 },
    })
  } catch (e: any) {
    console.error('fetchBoardsWithPosts error:', e)
  } finally {
    loadingContent.value = false
  }
}

async function loadBookmarks() {
  loadingBookmarks.value = true
  try {
    const data = await fetchBookmarks(bookmarksPagination.value.page)
    bookmarks.value = data.posts
    bookmarksPagination.value.total = data.total
  } catch { /* silent */ }
  loadingBookmarks.value = false
}

async function doSearch() {
  if (!searchQuery.value.trim()) return
  searchLoading.value = true
  try {
    const data = await searchPosts(searchQuery.value)
    searchResults.value = data.posts
    searchTotal.value = data.total
  } catch { /* silent */ }
  searchLoading.value = false
}

onMounted(async () => {
  await init()
  if (route.query.create === '1' && user.value?.is_admin) {
    showCreateModal.value = true
  }
  if (currentView.value === 'bookmarks') {
    await loadBookmarks()
  } else if (currentView.value === 'search') {
    // show search UI
  } else {
    await fetchBoardsWithPosts()
  }
})

watch(currentView, async (view) => {
  if (view === 'bookmarks') {
    await loadBookmarks()
  } else if (!view || view === 'must-read') {
    await fetchBoardsWithPosts()
  }
})

onUnmounted(() => {
  cleanup()
})

function formatDate(dateStr: string): string {
  const d = new Date(dateStr)
  const now = new Date()
  if (d.toDateString() === now.toDateString()) {
    return d.toLocaleTimeString('ko-KR', { hour: '2-digit', minute: '2-digit' })
  }
  return d.toLocaleDateString('ko-KR', { month: '2-digit', day: '2-digit' })
}
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
          class="md:hidden inline-flex items-center justify-center h-8 w-8 rounded-md hover:bg-accent transition-colors shrink-0" :aria-label="$t('common.menu')"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
            <line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>

        <h2 class="text-sm font-semibold">
          {{ currentView === 'bookmarks' ? $t('board.sidebar.myBookmarks') : currentView === 'search' ? $t('common.search') : currentView === 'must-read' ? $t('board.sidebar.unreadMustRead') : $t('board.index.allBoards') }}
        </h2>

        <div class="flex-1" />

        <UiButton v-if="user?.is_admin && !currentView" size="sm" @click="showCreateModal = true">
          <span class="hidden sm:inline">{{ $t('board.create.buttonLabel') }}</span>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4 sm:hidden">
            <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        </UiButton>
      </div>

      <!-- Content area -->
      <div class="flex-1 overflow-auto">
        <!-- Must-read view -->
        <template v-if="currentView === 'must-read'">
          <div class="p-4 sm:p-6 space-y-2">
            <div v-if="mustReadPosts.length === 0" class="text-center py-12 text-sm text-muted-foreground">
              {{ $t('board.mustRead.empty') }}
            </div>
            <NuxtLink
              v-for="p in mustReadPosts"
              :key="p.id"
              :to="`/board/${p.board_id}/${p.id}`"
              class="block rounded-md border px-4 py-3 hover:bg-accent/50 transition-colors"
            >
              <div class="flex items-center gap-1.5">
                <UiBadge variant="destructive" class="text-[10px] py-0">{{ $t('board.post.mustReadBadge') }}</UiBadge>
                <span class="text-sm font-medium truncate">{{ p.title }}</span>
              </div>
              <div class="text-xs text-muted-foreground mt-1">
                {{ p.author?.display_name || p.author?.username }} &middot; {{ timeAgo(p.created_at) }}
              </div>
            </NuxtLink>
          </div>
        </template>

        <!-- Bookmarks view -->
        <template v-else-if="currentView === 'bookmarks'">
          <div class="p-4 sm:p-6 space-y-2">
            <div v-if="loadingBookmarks" class="space-y-2">
              <div v-for="i in 5" :key="i" class="h-12 bg-muted/50 rounded animate-pulse" />
            </div>
            <div v-else-if="bookmarks.length === 0" class="text-center py-12 text-sm text-muted-foreground">
              {{ $t('board.bookmarks.empty') }}
            </div>
            <NuxtLink
              v-for="p in bookmarks"
              :key="p.id"
              :to="`/board/${p.board_id}/${p.id}`"
              class="block rounded-md border px-4 py-3 hover:bg-accent/50 transition-colors"
            >
              <span class="text-sm truncate">{{ p.title }}</span>
              <div class="text-xs text-muted-foreground mt-1">
                {{ p.author?.display_name || p.author?.username }} &middot; {{ timeAgo(p.created_at) }}
              </div>
            </NuxtLink>
          </div>
        </template>

        <!-- Search view -->
        <template v-else-if="currentView === 'search'">
          <div class="p-4 sm:p-6">
            <form @submit.prevent="doSearch" class="flex gap-2 mb-4">
              <input
                v-model="searchQuery"
                type="text"
                :placeholder="$t('board.search.placeholder')"
                class="flex-1 h-9 rounded-md border bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
              />
              <UiButton size="sm" type="submit" :disabled="searchLoading">{{ $t('common.search') }}</UiButton>
            </form>
            <div v-if="searchLoading" class="space-y-2">
              <div v-for="i in 3" :key="i" class="h-12 bg-muted/50 rounded animate-pulse" />
            </div>
            <div v-else-if="searchResults.length > 0" class="space-y-2">
              <p class="text-xs text-muted-foreground mb-2">{{ searchTotal }}{{ $t('board.search.resultCount') }}</p>
              <NuxtLink
                v-for="p in searchResults"
                :key="p.id"
                :to="`/board/${p.board_id}/${p.id}`"
                class="block rounded-md border px-4 py-3 hover:bg-accent/50 transition-colors"
              >
                <div class="flex items-center gap-1.5">
                  <span v-if="p.board_name" class="text-xs text-muted-foreground shrink-0">[{{ p.board_name }}]</span>
                  <span class="text-sm truncate">{{ p.title }}</span>
                </div>
                <div class="text-xs text-muted-foreground mt-1">
                  {{ p.author?.display_name || p.author?.username }} &middot; {{ timeAgo(p.created_at) }}
                </div>
              </NuxtLink>
            </div>
            <div v-else-if="searchQuery && !searchLoading" class="text-center py-12 text-sm text-muted-foreground">
              {{ $t('board.search.noResults') }}
            </div>
          </div>
        </template>

        <!-- Default: Recent posts by board -->
        <template v-else>
          <div class="p-4 sm:p-6">
            <div v-if="loadingContent" class="space-y-6">
              <div v-for="i in 3" :key="i">
                <div class="h-6 w-24 bg-muted/50 rounded animate-pulse mb-3" />
                <div v-for="j in 3" :key="j" class="h-10 bg-muted/50 rounded animate-pulse mb-1" />
              </div>
            </div>

            <div v-else-if="boardsWithPosts.length === 0" class="text-center py-16 text-muted-foreground">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" class="h-12 w-12 mx-auto mb-3 opacity-50">
                <rect x="3" y="3" width="18" height="18" rx="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" />
              </svg>
              <p>{{ $t('board.index.empty') }}</p>
              <p v-if="user?.is_admin" class="text-sm mt-1">{{ $t('board.index.emptyAdmin') }}</p>
            </div>

            <div v-else class="space-y-6">
              <div v-for="bwp in boardsWithPosts" :key="bwp.id">
                <div class="flex items-center justify-between mb-2">
                  <NuxtLink :to="`/board/${bwp.id}`" class="text-sm font-semibold hover:text-primary transition-colors">
                    {{ bwp.name }}
                  </NuxtLink>
                  <NuxtLink :to="`/board/${bwp.id}`" class="text-xs text-primary hover:underline">
                    {{ $t('common.more') }}
                  </NuxtLink>
                </div>

                <div v-if="bwp.recent_posts.length === 0" class="text-sm text-muted-foreground py-3 border rounded-md px-3">
                  {{ $t('board.post.empty') }}
                </div>

                <div v-else class="border rounded-md overflow-hidden">
                  <NuxtLink
                    v-for="(post, idx) in bwp.recent_posts"
                    :key="post.id"
                    :to="`/board/${bwp.id}/${post.id}`"
                    class="flex items-center gap-2 px-3 py-2 text-sm hover:bg-accent/50 transition-colors"
                    :class="idx < bwp.recent_posts.length - 1 ? 'border-b' : ''"
                  >
                    <UiBadge v-if="post.is_pinned" variant="secondary" class="text-[10px] py-0 shrink-0">{{ $t('board.post.noticeBadge') }}</UiBadge>
                    <UiBadge v-if="post.is_must_read" variant="destructive" class="text-[10px] py-0 shrink-0">{{ $t('board.post.mustReadBadge') }}</UiBadge>
                    <span class="flex-1 truncate">{{ post.title }}</span>
                    <span v-if="post.comment_count > 0" class="text-xs text-primary shrink-0">[{{ post.comment_count }}]</span>
                    <span v-if="post.has_attachments" class="text-muted-foreground shrink-0">
                      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-3 w-3 inline">
                        <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                      </svg>
                    </span>
                    <span class="text-xs text-muted-foreground shrink-0 hidden sm:inline">{{ formatDate(post.created_at) }}</span>
                  </NuxtLink>
                </div>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <!-- Create board modal -->
    <BoardCreateModal v-if="showCreateModal" @close="showCreateModal = false" />
  </div>
</template>
