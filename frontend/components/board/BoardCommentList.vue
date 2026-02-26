<script setup lang="ts">
import type { CommentInfo } from '~/composables/useBoard'

defineProps<{
  comments: CommentInfo[]
  postId: string
  loading: boolean
}>()
</script>

<template>
  <div>
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 3" :key="i" class="h-16 bg-muted/50 rounded animate-pulse" />
    </div>

    <div v-else-if="comments.length === 0" class="py-8 text-center text-sm text-muted-foreground">
      아직 댓글이 없습니다
    </div>

    <div v-else class="space-y-0">
      <BoardCommentItem
        v-for="comment in comments"
        :key="comment.id"
        :comment="comment"
        :post-id="postId"
        :depth="0"
      />
    </div>
  </div>
</template>
