<script setup lang="ts">
const { fetchModules, loaded } = usePlatform()

onMounted(async () => {
  if (!loaded.value) {
    await fetchModules()
  }
})
</script>

<template>
  <div class="h-screen flex flex-col overflow-hidden">
    <LayoutAppHeader />
    <main class="flex-1 min-h-0">
      <slot />
    </main>
  </div>
</template>
