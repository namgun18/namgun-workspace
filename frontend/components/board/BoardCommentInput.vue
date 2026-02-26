<script setup lang="ts">
const props = defineProps<{
  postId: string
}>()

const { createComment } = useBoard()

const content = ref('')
const submitting = ref(false)

async function handleSubmit() {
  if (!content.value.trim()) return
  submitting.value = true
  try {
    await createComment(props.postId, content.value)
    content.value = ''
  } catch (e: any) {
    console.error('Comment error:', e)
    alert(e?.data?.detail || '댓글 작성에 실패했습니다')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div>
    <textarea
      v-model="content"
      placeholder="댓글을 입력하세요"
      class="w-full rounded-md border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
      rows="3"
      @keydown.meta.enter="handleSubmit"
      @keydown.ctrl.enter="handleSubmit"
    />
    <div class="flex justify-end mt-1.5">
      <UiButton size="sm" @click="handleSubmit" :disabled="submitting || !content.trim()">
        {{ submitting ? '등록 중...' : '댓글 등록' }}
      </UiButton>
    </div>
  </div>
</template>
