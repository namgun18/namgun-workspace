<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { t } = useI18n()
const { appName } = useAppConfig()
useHead({ title: computed(() => `${t('nav.board')} | ${appName.value}`) })

const route = useRoute()
const router = useRouter()
const boardId = route.params.boardId as string
const postId = route.params.postId as string

const {
  init, cleanup, currentPost, comments, loadingPost, loadingComments,
  fetchPost, fetchComments, deletePost, toggleReaction, toggleBookmark,
} = useBoard()
const { user } = useAuth()

const showMobileSidebar = ref(false)

let DOMPurify: any = null
const purifyReady = ref(false)
if (import.meta.client) {
  import('dompurify').then(m => { DOMPurify = m.default; purifyReady.value = true })
}

onMounted(async () => {
  await init()
  await Promise.all([fetchPost(postId), fetchComments(postId)])
})

onUnmounted(() => {
  cleanup()
})

const sanitizedContent = computed(() => {
  if (!currentPost.value?.content) return ''
  if (!DOMPurify || !purifyReady.value) return ''
  return DOMPurify.sanitize(currentPost.value.content, {
    ALLOW_TAGS: [
      'a', 'b', 'i', 'u', 'em', 'strong', 'p', 'br', 'div', 'span',
      'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
      'table', 'thead', 'tbody', 'tr', 'td', 'th',
      'blockquote', 'pre', 'code', 'hr', 'img', 'sub', 'sup',
    ],
    ALLOW_ATTR: ['href', 'src', 'alt', 'style', 'class', 'target', 'width', 'height'],
    FORBID_TAGS: ['script', 'style', 'meta', 'head', 'link', 'object', 'embed', 'form', 'input'],
  })
})

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('ko-KR', {
    year: 'numeric', month: 'long', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function formatSize(bytes: number): string {
  if (!bytes) return ''
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + units[i]
}

const canEdit = computed(() => {
  if (!currentPost.value || !user.value) return false
  return currentPost.value.author?.id === user.value.id || user.value.is_admin
})

async function handleDelete() {
  if (!confirm(t('board.post.deleteConfirm'))) return
  await deletePost(postId)
  router.push(`/board/${boardId}`)
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

        <NuxtLink :to="`/board/${boardId}`" class="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          <span class="hidden sm:inline">{{ $t('board.post.listLink') }}</span>
        </NuxtLink>

        <div class="flex-1" />

        <template v-if="currentPost && canEdit">
          <NuxtLink
            :to="`/board/${boardId}/write?edit=${postId}`"
            class="inline-flex items-center gap-1 px-2 py-1.5 text-sm rounded-md hover:bg-accent transition-colors text-muted-foreground"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
            <span class="hidden sm:inline">{{ $t('common.edit') }}</span>
          </NuxtLink>
          <button
            @click="handleDelete"
            class="inline-flex items-center gap-1 px-2 py-1.5 text-sm rounded-md hover:bg-destructive/10 text-destructive transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
              <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
            <span class="hidden sm:inline">{{ $t('common.delete') }}</span>
          </button>
        </template>
      </div>

      <!-- Post content -->
      <div class="flex-1 overflow-auto">
        <!-- Loading -->
        <div v-if="loadingPost" class="p-4 sm:p-6 space-y-4">
          <div class="h-8 w-2/3 bg-muted/50 rounded animate-pulse" />
          <div class="h-4 w-1/3 bg-muted/50 rounded animate-pulse" />
          <div class="h-64 bg-muted/50 rounded animate-pulse mt-4" />
        </div>

        <!-- Not found -->
        <div v-else-if="!currentPost" class="text-center py-16 text-muted-foreground">
          <p>{{ $t('board.post.notFound') }}</p>
          <NuxtLink :to="`/board/${boardId}`" class="text-sm text-primary hover:underline mt-2 block">
            {{ $t('board.post.backToList') }}
          </NuxtLink>
        </div>

        <div v-else class="p-4 sm:p-6 max-w-4xl">
          <!-- Header -->
          <div class="mb-6">
            <div class="flex items-center gap-1.5 mb-2 flex-wrap">
              <UiBadge v-if="currentPost.is_pinned" variant="secondary" class="text-xs">{{ $t('board.post.noticeBadge') }}</UiBadge>
              <UiBadge v-if="currentPost.is_must_read" variant="destructive" class="text-xs">{{ $t('board.post.mustReadBadge') }}</UiBadge>
              <UiBadge v-if="currentPost.category" variant="outline" class="text-xs">{{ currentPost.category }}</UiBadge>
            </div>

            <h1 class="text-xl font-semibold mb-3">{{ currentPost.title }}</h1>

            <div class="flex items-center gap-3 text-sm text-muted-foreground flex-wrap">
              <div class="flex items-center gap-2">
                <UiAvatar :src="currentPost.author?.avatar_url" :alt="currentPost.author?.display_name || currentPost.author?.username || ''" class="h-6 w-6" />
                <span>{{ currentPost.author?.display_name || currentPost.author?.username || $t('common.unknownUser') }}</span>
              </div>
              <span>{{ formatDate(currentPost.created_at) }}</span>
              <span>{{ $t('board.post.viewCount', { n: currentPost.view_count }) }}</span>
              <span v-if="currentPost.is_edited" class="text-xs">{{ $t('board.post.edited') }}</span>
            </div>
          </div>

          <!-- Bookmark -->
          <div class="flex items-center gap-1 mb-4 border-b pb-3">
            <button
              @click="toggleBookmark(postId)"
              class="h-8 px-2 flex items-center gap-1 rounded-md text-sm hover:bg-accent transition-colors"
              :class="currentPost.is_bookmarked ? 'text-yellow-500' : 'text-muted-foreground'"
            >
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" :fill="currentPost.is_bookmarked ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" class="h-4 w-4">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
              </svg>
              <span>{{ currentPost.is_bookmarked ? $t('board.post.bookmarked') : $t('board.post.bookmark') }}</span>
            </button>
          </div>

          <!-- Content -->
          <div
            class="prose prose-sm dark:prose-invert max-w-none mb-6 min-h-[100px]"
            v-html="sanitizedContent"
          />

          <!-- Attachments -->
          <BoardAttachments v-if="currentPost.attachments.length > 0" :attachments="currentPost.attachments" />

          <!-- Reactions -->
          <BoardReactions
            v-if="currentPost.reactions"
            :reactions="currentPost.reactions"
            :post-id="postId"
          />

          <!-- Comments -->
          <div class="mt-8 border-t pt-6">
            <h3 class="text-sm font-semibold mb-4">{{ $t('board.comment.heading', { n: currentPost.comment_count }) }}</h3>
            <BoardCommentInput :post-id="postId" class="mb-6" />
            <BoardCommentList
              :comments="comments"
              :post-id="postId"
              :loading="loadingComments"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>
