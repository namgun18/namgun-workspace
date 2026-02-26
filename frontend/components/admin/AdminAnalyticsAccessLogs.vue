<script setup lang="ts">
import type { AccessLogPage } from '~/composables/useAdminAnalytics'

const { t } = useI18n()

const props = defineProps<{
  data: AccessLogPage | null
}>()

const emit = defineEmits<{
  (e: 'page', page: number): void
  (e: 'filter', service: string | undefined): void
}>()

const serviceFilter = ref<string>('')

const services = ['', 'mail', 'calendar', 'contacts', 'files', 'meetings', 'git', 'lab', 'admin', 'auth']
const serviceLabels = computed<Record<string, string>>(() => ({
  '': t('admin.analytics.services.all'), mail: t('admin.analytics.services.mail'), calendar: t('admin.analytics.services.calendar'), contacts: t('admin.analytics.services.contacts'), files: t('admin.analytics.services.files'),
  meetings: t('admin.analytics.services.meetings'), git: 'Git', lab: 'Lab', admin: t('admin.analytics.services.admin'), auth: t('admin.analytics.services.auth'),
}))

function onFilterChange() {
  emit('filter', serviceFilter.value || undefined)
}

function formatTime(iso: string) {
  if (!iso) return '-'
  return new Date(iso).toLocaleString('ko-KR', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

function statusColor(code: number) {
  if (code < 300) return 'text-green-600 dark:text-green-400'
  if (code < 400) return 'text-yellow-600 dark:text-yellow-400'
  return 'text-red-600 dark:text-red-400'
}

const totalPages = computed(() => {
  if (!props.data) return 0
  return Math.ceil(props.data.total / props.data.limit)
})
</script>

<template>
  <div class="rounded-lg border bg-card p-4">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-sm font-medium text-muted-foreground">{{ $t('admin.analytics.accessLogs.title') }}</h3>
      <select
        v-model="serviceFilter"
        @change="onFilterChange"
        class="text-xs border rounded px-2 py-1 bg-background"
      >
        <option v-for="s in services" :key="s" :value="s">{{ serviceLabels[s] || s }}</option>
      </select>
    </div>

    <div v-if="!data || data.logs.length === 0" class="text-sm text-muted-foreground py-4 text-center">
      {{ $t('admin.analytics.accessLogs.empty') }}
    </div>
    <div v-else class="overflow-x-auto">
      <table class="w-full text-xs">
        <thead>
          <tr class="border-b">
            <th class="text-left py-2 px-2 font-medium text-muted-foreground">{{ $t('admin.analytics.accessLogs.col.time') }}</th>
            <th class="text-left py-2 px-2 font-medium text-muted-foreground">{{ $t('admin.analytics.accessLogs.col.ip') }}</th>
            <th class="text-left py-2 px-2 font-medium text-muted-foreground">{{ $t('admin.analytics.accessLogs.col.path') }}</th>
            <th class="text-left py-2 px-2 font-medium text-muted-foreground">{{ $t('admin.analytics.accessLogs.col.status') }}</th>
            <th class="text-left py-2 px-2 font-medium text-muted-foreground">{{ $t('admin.analytics.accessLogs.col.response') }}</th>
            <th class="text-left py-2 px-2 font-medium text-muted-foreground">{{ $t('admin.analytics.accessLogs.col.browser') }}</th>
            <th class="text-left py-2 px-2 font-medium text-muted-foreground">{{ $t('admin.analytics.accessLogs.col.user') }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="log in data.logs" :key="log.id" class="border-b last:border-0 hover:bg-accent/30">
            <td class="py-1.5 px-2 text-muted-foreground whitespace-nowrap">{{ formatTime(log.created_at) }}</td>
            <td class="py-1.5 px-2 font-mono">{{ log.ip_address }}</td>
            <td class="py-1.5 px-2 max-w-[200px] truncate" :title="log.path">{{ log.method }} {{ log.path }}</td>
            <td class="py-1.5 px-2 font-mono" :class="statusColor(log.status_code)">{{ log.status_code }}</td>
            <td class="py-1.5 px-2 text-muted-foreground">{{ log.response_time_ms }}ms</td>
            <td class="py-1.5 px-2 text-muted-foreground">{{ log.browser || '-' }}</td>
            <td class="py-1.5 px-2">{{ log.username || '-' }}</td>
          </tr>
        </tbody>
      </table>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="flex items-center justify-between mt-3 pt-3 border-t">
        <span class="text-xs text-muted-foreground">
          {{ $t('admin.analytics.accessLogs.pagination', { total: data.total.toLocaleString(), from: ((data.page - 1) * data.limit) + 1, to: Math.min(data.page * data.limit, data.total) }) }}
        </span>
        <div class="flex gap-1">
          <button
            :disabled="data.page <= 1"
            @click="emit('page', data.page - 1)"
            class="px-2 py-1 text-xs rounded border hover:bg-accent disabled:opacity-50"
          >
            {{ $t('common.pagination.prev') }}
          </button>
          <button
            :disabled="data.page >= totalPages"
            @click="emit('page', data.page + 1)"
            class="px-2 py-1 text-xs rounded border hover:bg-accent disabled:opacity-50"
          >
            {{ $t('common.pagination.next') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
