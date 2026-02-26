<script setup lang="ts">
import type { PostSummary } from '~/composables/useBoard'

defineProps<{
  pinned: PostSummary[]
  posts: PostSummary[]
  boardId: string
}>()

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
  <div class="border rounded-lg overflow-hidden">
    <!-- Empty state -->
    <div v-if="pinned.length === 0 && posts.length === 0" class="py-12 text-center text-sm text-muted-foreground">
      {{ $t('board.post.empty') }}
    </div>

    <table v-else class="w-full text-sm">
      <thead class="bg-muted/30">
        <tr class="border-b">
          <th class="text-left px-4 py-2.5 font-medium w-full">{{ $t('board.table.title') }}</th>
          <th class="text-left px-3 py-2.5 font-medium whitespace-nowrap hidden sm:table-cell">{{ $t('board.table.author') }}</th>
          <th class="text-center px-3 py-2.5 font-medium whitespace-nowrap hidden md:table-cell">{{ $t('board.table.views') }}</th>
          <th class="text-center px-3 py-2.5 font-medium whitespace-nowrap hidden md:table-cell">{{ $t('board.table.comments') }}</th>
          <th class="text-right px-4 py-2.5 font-medium whitespace-nowrap hidden sm:table-cell">{{ $t('board.table.date') }}</th>
        </tr>
      </thead>
      <tbody>
        <!-- Pinned posts -->
        <tr
          v-for="post in pinned"
          :key="post.id"
          class="border-b bg-primary/[0.02] hover:bg-accent/50 transition-colors cursor-pointer"
          @click="$router.push(`/board/${boardId}/${post.id}`)"
        >
          <td class="px-4 py-2.5">
            <div class="flex items-center gap-1.5">
              <UiBadge variant="secondary" class="text-[10px] shrink-0 py-0">{{ $t('board.post.noticeBadge') }}</UiBadge>
              <UiBadge v-if="post.is_must_read" variant="destructive" class="text-[10px] shrink-0 py-0">{{ $t('board.post.mustReadBadge') }}</UiBadge>
              <span v-if="post.category" class="text-xs text-muted-foreground shrink-0">[{{ post.category }}]</span>
              <span class="font-medium truncate">{{ post.title }}</span>
              <span v-if="post.has_attachments" class="text-muted-foreground shrink-0" :title="$t('board.post.hasAttachments')">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-3.5 w-3.5 inline">
                  <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                </svg>
              </span>
            </div>
          </td>
          <td class="px-3 py-2.5 text-muted-foreground whitespace-nowrap hidden sm:table-cell">
            {{ post.author?.display_name || post.author?.username || '-' }}
          </td>
          <td class="px-3 py-2.5 text-center text-muted-foreground hidden md:table-cell">{{ post.view_count }}</td>
          <td class="px-3 py-2.5 text-center text-muted-foreground hidden md:table-cell">{{ post.comment_count }}</td>
          <td class="px-4 py-2.5 text-right text-muted-foreground whitespace-nowrap hidden sm:table-cell">
            {{ formatDate(post.created_at) }}
          </td>
        </tr>

        <!-- Normal posts -->
        <tr
          v-for="post in posts"
          :key="post.id"
          class="border-b last:border-b-0 hover:bg-accent/50 transition-colors cursor-pointer"
          @click="$router.push(`/board/${boardId}/${post.id}`)"
        >
          <td class="px-4 py-2.5">
            <div class="flex items-center gap-1.5">
              <span v-if="post.category" class="text-xs text-muted-foreground shrink-0">[{{ post.category }}]</span>
              <span class="truncate">{{ post.title }}</span>
              <span v-if="post.has_attachments" class="text-muted-foreground shrink-0">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-3.5 w-3.5 inline">
                  <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />
                </svg>
              </span>
              <span v-if="post.comment_count > 0" class="text-xs text-primary shrink-0 sm:hidden">[{{ post.comment_count }}]</span>
            </div>
            <!-- Mobile meta -->
            <div class="sm:hidden flex items-center gap-2 mt-0.5 text-xs text-muted-foreground">
              <span>{{ post.author?.display_name || post.author?.username }}</span>
              <span>{{ formatDate(post.created_at) }}</span>
              <span>{{ $t('board.post.viewCount', { n: post.view_count }) }}</span>
            </div>
          </td>
          <td class="px-3 py-2.5 text-muted-foreground whitespace-nowrap hidden sm:table-cell">
            {{ post.author?.display_name || post.author?.username || '-' }}
          </td>
          <td class="px-3 py-2.5 text-center text-muted-foreground hidden md:table-cell">{{ post.view_count }}</td>
          <td class="px-3 py-2.5 text-center text-muted-foreground hidden md:table-cell">{{ post.comment_count }}</td>
          <td class="px-4 py-2.5 text-right text-muted-foreground whitespace-nowrap hidden sm:table-cell">
            {{ formatDate(post.created_at) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
