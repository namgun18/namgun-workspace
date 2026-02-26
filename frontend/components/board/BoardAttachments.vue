<script setup lang="ts">
defineProps<{
  attachments: Array<{ name: string; url: string; size?: number }>
}>()

function formatSize(bytes: number): string {
  if (!bytes) return ''
  const units = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(1024))
  return (bytes / Math.pow(1024, i)).toFixed(i > 0 ? 1 : 0) + ' ' + units[i]
}
</script>

<template>
  <div class="border rounded-lg p-3 mb-4">
    <h4 class="text-xs font-medium text-muted-foreground mb-2">
      첨부파일 ({{ attachments.length }})
    </h4>
    <div class="space-y-1">
      <a
        v-for="(att, i) in attachments"
        :key="i"
        :href="att.url"
        target="_blank"
        class="flex items-center gap-2 px-3 py-2 text-sm rounded-md hover:bg-accent transition-colors"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4 shrink-0 text-muted-foreground">
          <path d="m21.44 11.05-9.19 9.19a6 6 0 0 1-8.49-8.49l8.57-8.57A4 4 0 1 1 18 8.84l-8.59 8.57a2 2 0 0 1-2.83-2.83l8.49-8.48" />
        </svg>
        <span class="truncate">{{ att.name }}</span>
        <span v-if="att.size" class="text-xs text-muted-foreground shrink-0 ml-auto">{{ formatSize(att.size) }}</span>
      </a>
    </div>
  </div>
</template>
