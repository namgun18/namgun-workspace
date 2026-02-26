<script setup lang="ts">
import GitMarkdownRenderer from './GitMarkdownRenderer.vue'

const { t } = useI18n()
const { selectedPull } = useGit()

function timeAgo(dateStr: string) {
  if (!dateStr) return ''
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 60) return t('common.minutesAgo', { n: mins })
  const hours = Math.floor(mins / 60)
  if (hours < 24) return t('common.hoursAgo', { n: hours })
  const days = Math.floor(hours / 24)
  if (days < 30) return t('common.daysAgo', { n: days })
  return new Date(dateStr).toLocaleDateString('ko-KR')
}
</script>

<template>
  <div v-if="selectedPull" class="flex-1 overflow-y-auto">
    <!-- PR header -->
    <div class="px-4 pt-4 pb-3 border-b">
      <h2 class="text-lg font-semibold">
        {{ selectedPull.title }}
        <span class="text-muted-foreground font-normal">#{{ selectedPull.number }}</span>
      </h2>
      <div class="flex items-center gap-2 mt-2 flex-wrap">
        <span
          v-if="selectedPull.merged"
          class="px-2 py-0.5 text-xs font-medium rounded-full bg-purple-500/10 text-purple-600"
        >
          Merged
        </span>
        <span
          v-else
          class="px-2 py-0.5 text-xs font-medium rounded-full"
          :class="selectedPull.state === 'open' ? 'bg-green-500/10 text-green-600' : 'bg-red-500/10 text-red-600'"
        >
          {{ selectedPull.state === 'open' ? 'Open' : 'Closed' }}
        </span>
        <span class="text-xs text-muted-foreground">
          {{ selectedPull.user?.login }} · {{ timeAgo(selectedPull.created_at) }}
        </span>
      </div>
      <div v-if="selectedPull.head_branch && selectedPull.base_branch" class="mt-2 text-xs text-muted-foreground">
        <code class="bg-muted px-1.5 py-0.5 rounded">{{ selectedPull.head_branch }}</code>
        →
        <code class="bg-muted px-1.5 py-0.5 rounded">{{ selectedPull.base_branch }}</code>
      </div>
    </div>

    <!-- Body -->
    <div v-if="selectedPull.body" class="px-4 py-4">
      <GitMarkdownRenderer :content="selectedPull.body" />
    </div>
    <div v-else class="px-4 py-8 text-center text-sm text-muted-foreground">
      {{ $t('git.pull.noDescription') }}
    </div>
  </div>
</template>
