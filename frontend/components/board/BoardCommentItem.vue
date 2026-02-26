<script setup lang="ts">
import type { CommentInfo } from '~/composables/useBoard'

const { t } = useI18n()

const props = defineProps<{
  comment: CommentInfo
  postId: string
  depth: number
}>()

const { user } = useAuth()
const { deleteComment, updateComment, createComment } = useBoard()

const showReply = ref(false)
const replyContent = ref('')
const editing = ref(false)
const editContent = ref('')
const submitting = ref(false)

const canEdit = computed(() => {
  if (!user.value || props.comment.is_deleted) return false
  return props.comment.author?.id === user.value.id || user.value.is_admin
})

function startEdit() {
  editContent.value = props.comment.content
  editing.value = true
}

async function saveEdit() {
  if (!editContent.value.trim()) return
  submitting.value = true
  try {
    await updateComment(props.comment.id, editContent.value)
    editing.value = false
  } catch (e: any) {
    console.error('Edit comment error:', e)
  } finally {
    submitting.value = false
  }
}

async function handleDelete() {
  if (!confirm(t('board.comment.deleteConfirm'))) return
  await deleteComment(props.comment.id)
}

async function submitReply() {
  if (!replyContent.value.trim()) return
  submitting.value = true
  try {
    await createComment(props.postId, replyContent.value, props.comment.id)
    replyContent.value = ''
    showReply.value = false
  } catch (e: any) {
    console.error('Reply error:', e)
    alert(e?.data?.detail || t('board.reply.createError'))
  } finally {
    submitting.value = false
  }
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('ko-KR', {
    month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}
</script>

<template>
  <div :class="depth > 0 ? 'ml-8 border-l pl-4' : 'border-b'" class="py-3">
    <!-- Deleted comment placeholder -->
    <div v-if="comment.is_deleted" class="text-sm text-muted-foreground italic">
      {{ comment.content }}
    </div>

    <template v-else>
      <!-- Author + date -->
      <div class="flex items-center gap-2 mb-1">
        <UiAvatar
          :src="comment.author?.avatar_url"
          :alt="comment.author?.display_name || comment.author?.username || ''"
          class="h-5 w-5"
        />
        <span class="text-sm font-medium">
          {{ comment.author?.display_name || comment.author?.username || $t('common.unknownUser') }}
        </span>
        <span class="text-xs text-muted-foreground">{{ formatDate(comment.created_at) }}</span>
        <span v-if="comment.is_edited" class="text-xs text-muted-foreground">{{ $t('board.comment.edited') }}</span>
      </div>

      <!-- Content -->
      <div v-if="editing" class="mb-2">
        <textarea
          v-model="editContent"
          class="w-full rounded-md border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
          rows="3"
        />
        <div class="flex gap-1 mt-1">
          <UiButton size="sm" @click="saveEdit" :disabled="submitting">{{ $t('common.save') }}</UiButton>
          <UiButton size="sm" variant="ghost" @click="editing = false">{{ $t('common.cancel') }}</UiButton>
        </div>
      </div>
      <p v-else class="text-sm whitespace-pre-wrap mb-1">{{ comment.content }}</p>

      <!-- Actions -->
      <div v-if="!editing" class="flex items-center gap-2 text-xs">
        <button
          v-if="depth === 0"
          @click="showReply = !showReply"
          class="text-muted-foreground hover:text-foreground transition-colors"
        >
          {{ $t('board.reply.label') }}
        </button>
        <template v-if="canEdit">
          <button @click="startEdit" class="text-muted-foreground hover:text-foreground transition-colors">{{ $t('common.edit') }}</button>
          <button @click="handleDelete" class="text-muted-foreground hover:text-destructive transition-colors">{{ $t('common.delete') }}</button>
        </template>
      </div>

      <!-- Reply input -->
      <div v-if="showReply" class="mt-2 ml-2">
        <textarea
          v-model="replyContent"
          :placeholder="$t('board.reply.placeholder')"
          class="w-full rounded-md border bg-background px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-ring"
          rows="2"
        />
        <div class="flex gap-1 mt-1">
          <UiButton size="sm" @click="submitReply" :disabled="submitting || !replyContent.trim()">
            {{ $t('board.reply.submit') }}
          </UiButton>
          <UiButton size="sm" variant="ghost" @click="showReply = false">{{ $t('common.cancel') }}</UiButton>
        </div>
      </div>
    </template>

    <!-- Nested replies -->
    <BoardCommentItem
      v-for="reply in comment.replies || []"
      :key="reply.id"
      :comment="reply"
      :post-id="postId"
      :depth="depth + 1"
    />
  </div>
</template>
