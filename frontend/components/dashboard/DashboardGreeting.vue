<script setup lang="ts">
const { t } = useI18n()
const { user } = useAuth()

const now = ref<Date | null>(null)
let timer: ReturnType<typeof setInterval>

onMounted(() => {
  now.value = new Date()
  timer = setInterval(() => { now.value = new Date() }, 60_000)
})
onUnmounted(() => clearInterval(timer))

const greeting = computed(() => {
  if (!now.value) return t('greeting.hello')
  const h = now.value.getHours()
  if (h < 6) return t('greeting.lateNight')
  if (h < 12) return t('greeting.goodMorning')
  if (h < 18) return t('greeting.goodAfternoon')
  return t('greeting.goodEvening')
})

const dateStr = computed(() => {
  if (!now.value) return ''
  return now.value.toLocaleDateString('ko-KR', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  })
})
</script>

<template>
  <div class="rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 dark:from-blue-500/20 dark:to-indigo-500/20 dark:border dark:border-blue-500/30 p-6 text-white dark:text-foreground shadow-md">
    <div class="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-1">
      <div>
        <h1 class="text-2xl font-bold tracking-tight">
          {{ $t('greeting.withName', { greeting, name: user?.display_name || user?.username }) }}
        </h1>
        <p class="text-blue-100 dark:text-muted-foreground text-sm mt-0.5">
          {{ $t('greeting.haveAGoodDay') }}
        </p>
      </div>
      <p v-if="dateStr" class="text-sm text-blue-200 dark:text-muted-foreground shrink-0">
        {{ dateStr }}
      </p>
    </div>
  </div>
</template>
