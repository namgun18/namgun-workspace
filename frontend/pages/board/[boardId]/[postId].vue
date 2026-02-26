<script setup lang="ts">
definePageMeta({ layout: 'default' })

const route = useRoute()
const router = useRouter()
const boardId = route.params.boardId as string
const postId = route.params.postId as string

const {
  init, cleanup, currentPost, comments, loadingPost, loadingComments,
  fetchPost, fetchComments, deletePost, toggleReaction, toggleBookmark,
} = useBoard()
const { user } = useAuth()

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
  if (!confirm('이 게시글을 삭제하시겠습니까?')) return
  await deletePost(postId)
  router.push(`/board/${boardId}`)
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-6">
    <!-- Loading -->
    <div v-if="loadingPost" class="space-y-4">
      <div class="h-8 w-2/3 bg-muted/50 rounded animate-pulse" />
      <div class="h-4 w-1/3 bg-muted/50 rounded animate-pulse" />
      <div class="h-64 bg-muted/50 rounded animate-pulse mt-4" />
    </div>

    <!-- Not found -->
    <div v-else-if="!currentPost" class="text-center py-16 text-muted-foreground">
      <p>게시글을 찾을 수 없습니다</p>
      <NuxtLink :to="`/board/${boardId}`" class="text-sm text-primary hover:underline mt-2 block">
        목록으로 돌아가기
      </NuxtLink>
    </div>

    <template v-else>
      <!-- Header -->
      <div class="mb-6">
        <div class="flex items-center gap-2 mb-2">
          <NuxtLink :to="`/board/${boardId}`" class="text-sm text-muted-foreground hover:text-foreground transition-colors">
            &larr; 목록
          </NuxtLink>
          <UiBadge v-if="currentPost.is_pinned" variant="secondary" class="text-xs">공지</UiBadge>
          <UiBadge v-if="currentPost.is_must_read" variant="destructive" class="text-xs">필독</UiBadge>
          <UiBadge v-if="currentPost.category" variant="outline" class="text-xs">{{ currentPost.category }}</UiBadge>
        </div>

        <h1 class="text-xl font-semibold mb-3">{{ currentPost.title }}</h1>

        <div class="flex items-center gap-3 text-sm text-muted-foreground">
          <div class="flex items-center gap-2">
            <UiAvatar :src="currentPost.author?.avatar_url" :alt="currentPost.author?.display_name || currentPost.author?.username || ''" class="h-6 w-6" />
            <span>{{ currentPost.author?.display_name || currentPost.author?.username || '알 수 없음' }}</span>
          </div>
          <span>{{ formatDate(currentPost.created_at) }}</span>
          <span>조회 {{ currentPost.view_count }}</span>
          <span v-if="currentPost.is_edited" class="text-xs">(수정됨)</span>
        </div>
      </div>

      <!-- Action buttons -->
      <div class="flex items-center gap-1 mb-4 border-b pb-3">
        <button
          @click="toggleBookmark(postId)"
          class="h-8 px-2 flex items-center gap-1 rounded-md text-sm hover:bg-accent transition-colors"
          :class="currentPost.is_bookmarked ? 'text-yellow-500' : 'text-muted-foreground'"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" :fill="currentPost.is_bookmarked ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="2" class="h-4 w-4">
            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
          </svg>
          <span>{{ currentPost.is_bookmarked ? '저장됨' : '저장' }}</span>
        </button>
        <div class="flex-1" />
        <template v-if="canEdit">
          <NuxtLink
            :to="`/board/${boardId}/write?edit=${postId}`"
            class="h-8 px-2 flex items-center gap-1 rounded-md text-sm text-muted-foreground hover:bg-accent transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" /><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
            수정
          </NuxtLink>
          <button
            @click="handleDelete"
            class="h-8 px-2 flex items-center gap-1 rounded-md text-sm text-destructive hover:bg-destructive/10 transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
              <polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
            삭제
          </button>
        </template>
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
        <h3 class="text-sm font-semibold mb-4">댓글 {{ currentPost.comment_count }}</h3>
        <BoardCommentInput :post-id="postId" class="mb-6" />
        <BoardCommentList
          :comments="comments"
          :post-id="postId"
          :loading="loadingComments"
        />
      </div>
    </template>
  </div>
</template>
