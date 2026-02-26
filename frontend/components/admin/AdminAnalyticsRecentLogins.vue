<script setup lang="ts">
import type { RecentLogin } from '~/composables/useAdminAnalytics'

const { t } = useI18n()
defineProps<{ data: RecentLogin[] }>()

function timeAgo(iso: string) {
  if (!iso) return '-'
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return t('common.justNow')
  if (mins < 60) return t('common.minutesAgo', { n: mins })
  const hours = Math.floor(mins / 60)
  if (hours < 24) return t('common.hoursAgo', { n: hours })
  return t('common.daysAgo', { n: Math.floor(hours / 24) })
}

function maskIp(ip: string) {
  const parts = ip.split('.')
  if (parts.length === 4) return `${parts[0]}.${parts[1]}.x.x`
  return ip.length > 10 ? ip.slice(0, 10) + '...' : ip
}
</script>

<template>
  <div class="rounded-lg border bg-card p-4">
    <h3 class="text-sm font-medium text-muted-foreground mb-3">{{ $t('admin.analytics.recentLogins.title') }}</h3>
    <div v-if="data.length === 0" class="text-sm text-muted-foreground py-4 text-center">
      {{ $t('admin.analytics.recentLogins.empty') }}
    </div>
    <div v-else class="space-y-2">
      <div
        v-for="(l, i) in data.slice(0, 10)"
        :key="i"
        class="flex items-center justify-between text-sm py-1.5 border-b last:border-0"
      >
        <div class="flex items-center gap-2 min-w-0">
          <span class="font-medium truncate">{{ l.display_name || l.username }}</span>
          <span class="text-muted-foreground text-xs">{{ maskIp(l.ip_address) }}</span>
        </div>
        <span class="text-xs text-muted-foreground shrink-0 ml-2">{{ timeAgo(l.login_at) }}</span>
      </div>
    </div>
  </div>
</template>
