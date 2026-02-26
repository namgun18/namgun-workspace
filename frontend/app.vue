<script setup lang="ts">
const { fetchAppConfig } = useAppConfig()
fetchAppConfig()
</script>

<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
</template>
