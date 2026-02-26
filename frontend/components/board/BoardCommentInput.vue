<script setup lang="ts">
const { t } = useI18n()

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
    alert(e?.data?.detail || t('board.comment.createError'))
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div>
    <textarea
      v-model="content"
      :placeholder="$t('board.comment.placeholder')"
      class="w-full rounded-md border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
      rows="3"
      @keydown.meta.enter="handleSubmit"
      @keydown.ctrl.enter="handleSubmit"
    />
    <div class="flex justify-end mt-1.5">
      <UiButton size="sm" @click="handleSubmit" :disabled="submitting || !content.trim()">
        {{ submitting ? $t('board.comment.submitting') : $t('board.comment.submit') }}
      </UiButton>
    </div>
  </div>
</template>
