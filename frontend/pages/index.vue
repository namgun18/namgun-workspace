<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { t } = useI18n()
const { appName } = useAppConfig()
useHead({ title: computed(() => `${t('nav.dashboard')} | ${appName.value}`) })
</script>

<template>
  <div class="h-full overflow-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
    <!-- Greeting -->
    <DashboardGreeting />

    <!-- Service status bar -->
    <DashboardServiceStatus />

    <!-- Main grid: 3 columns on lg -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <!-- Left 2 cols: recent mail -->
      <DashboardRecentMail />

      <!-- Right col: notices + shortcuts -->
      <div class="space-y-4">
        <DashboardNotices />
        <DashboardShortcuts />
      </div>

      <!-- Left 2 cols: recent board posts -->
      <DashboardRecentBoard />

      <!-- Right col: storage -->
      <div class="space-y-4">
        <DashboardStorage />
      </div>

      <!-- Left 2 cols: recent git -->
      <DashboardRecentGit />

    </div>
  </div>
</template>
