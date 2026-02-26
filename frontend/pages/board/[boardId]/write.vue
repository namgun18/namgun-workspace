<script setup lang="ts">
definePageMeta({ layout: 'default' })

const route = useRoute()
const router = useRouter()
const boardId = route.params.boardId as string
const editPostId = route.query.edit as string | undefined

const { init, cleanup, currentBoard, fetchPost, currentPost, createPost, updatePost, selectBoard } = useBoard()
const { user } = useAuth()

const title = ref('')
const category = ref<string | null>(null)
const isPinned = ref(false)
const isMustRead = ref(false)
const editorHtml = ref<string | null>(null)
const editorText = ref('')
const attachments = ref<Array<{ name: string; url: string; size?: number }>>([])
const submitting = ref(false)
const isEditMode = ref(false)
const initialContent = ref('')

onMounted(async () => {
  await init()
  await selectBoard(boardId)

  // Edit mode: load existing post
  if (editPostId) {
    await fetchPost(editPostId)
    if (currentPost.value) {
      isEditMode.value = true
      title.value = currentPost.value.title
      category.value = currentPost.value.category
      isPinned.value = currentPost.value.is_pinned
      isMustRead.value = currentPost.value.is_must_read
      initialContent.value = currentPost.value.content
      attachments.value = currentPost.value.attachments || []
    }
  }
})

onUnmounted(() => {
  cleanup()
})

const canSetNotice = computed(() => {
  if (!currentBoard.value || !user.value) return false
  return currentBoard.value.notice_permission === 'all' || user.value.is_admin
})

async function handleFileUpload(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files?.length) return
  for (const file of input.files) {
    const formData = new FormData()
    formData.append('file', file)
    try {
      const result = await $fetch<{ url: string; filename: string; size: number }>('/api/files/upload', {
        method: 'POST',
        body: formData,
      })
      attachments.value = [...attachments.value, { name: result.filename, url: result.url, size: result.size }]
    } catch (e: any) {
      console.error('File upload error:', e)
      alert('파일 업로드에 실패했습니다')
    }
  }
  input.value = ''
}

function removeAttachment(index: number) {
  attachments.value = attachments.value.filter((_, i) => i !== index)
}

async function handleSubmit() {
  if (!title.value.trim()) {
    alert('제목을 입력해주세요')
    return
  }
  const content = editorHtml.value || editorText.value
  if (!content.trim()) {
    alert('내용을 입력해주세요')
    return
  }

  submitting.value = true
  try {
    if (isEditMode.value && editPostId) {
      await updatePost(editPostId, {
        title: title.value,
        content,
        category: category.value,
        is_pinned: isPinned.value,
        is_must_read: isMustRead.value,
        attachments: attachments.value.length > 0 ? attachments.value : null,
      })
      router.push(`/board/${boardId}/${editPostId}`)
    } else {
      const result = await createPost(boardId, {
        title: title.value,
        content,
        category: category.value,
        is_pinned: isPinned.value,
        is_must_read: isMustRead.value,
        attachments: attachments.value.length > 0 ? attachments.value : null,
      })
      router.push(`/board/${boardId}/${result.id}`)
    }
  } catch (e: any) {
    console.error('Submit error:', e)
    const detail = e?.data?.detail
    const msg = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map((d: any) => d.msg).join(', ') : '게시글 저장에 실패했습니다'
    alert(msg)
  } finally {
    submitting.value = false
  }
}

function formatSize(bytes: number): string {
  if (!bytes) return ''
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + units[i]
}
</script>

<template>
  <div class="max-w-4xl mx-auto px-4 py-6">
    <div class="flex items-center gap-3 mb-6">
      <button @click="router.back()" class="h-8 w-8 flex items-center justify-center rounded-md hover:bg-accent transition-colors">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
          <polyline points="15 18 9 12 15 6" />
        </svg>
      </button>
      <h1 class="text-lg font-semibold">
        {{ isEditMode ? '게시글 수정' : '게시글 작성' }}
      </h1>
    </div>

    <div class="space-y-4">
      <!-- Category + options row -->
      <div class="flex items-center gap-3 flex-wrap">
        <select
          v-if="currentBoard?.categories && currentBoard.categories.length > 0"
          v-model="category"
          class="h-9 rounded-md border bg-background px-3 text-sm"
        >
          <option :value="null">말머리 선택</option>
          <option v-for="cat in currentBoard.categories" :key="cat" :value="cat">{{ cat }}</option>
        </select>

        <template v-if="canSetNotice">
          <label class="flex items-center gap-1.5 text-sm cursor-pointer">
            <input type="checkbox" v-model="isPinned" class="rounded" />
            공지
          </label>
          <label class="flex items-center gap-1.5 text-sm cursor-pointer">
            <input type="checkbox" v-model="isMustRead" class="rounded" />
            필독
          </label>
        </template>
      </div>

      <!-- Title -->
      <input
        v-model="title"
        type="text"
        placeholder="제목을 입력하세요"
        class="w-full h-11 rounded-md border bg-background px-3 text-base font-medium focus:outline-none focus:ring-2 focus:ring-ring"
      />

      <!-- Editor -->
      <MailEditor
        v-model:html="editorHtml"
        v-model:text="editorText"
        :initial-content="initialContent"
      />

      <!-- Attachments -->
      <div>
        <label class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border text-sm cursor-pointer hover:bg-accent transition-colors">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4">
            <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />
          </svg>
          파일 첨부
          <input type="file" multiple class="hidden" @change="handleFileUpload" />
        </label>

        <div v-if="attachments.length > 0" class="mt-2 space-y-1">
          <div
            v-for="(att, i) in attachments"
            :key="i"
            class="flex items-center gap-2 text-sm px-2 py-1 bg-muted/30 rounded"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-3.5 w-3.5 shrink-0 text-muted-foreground">
              <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />
            </svg>
            <span class="truncate">{{ att.name }}</span>
            <span v-if="att.size" class="text-xs text-muted-foreground shrink-0">{{ formatSize(att.size) }}</span>
            <button @click="removeAttachment(i)" class="ml-auto text-muted-foreground hover:text-destructive shrink-0">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-3.5 w-3.5">
                <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      <!-- Submit -->
      <div class="flex justify-end gap-2 pt-2">
        <UiButton variant="outline" @click="router.back()">취소</UiButton>
        <UiButton @click="handleSubmit" :disabled="submitting">
          {{ submitting ? '저장 중...' : (isEditMode ? '수정' : '등록') }}
        </UiButton>
      </div>
    </div>
  </div>
</template>
