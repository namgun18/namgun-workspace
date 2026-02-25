<script setup lang="ts">
definePageMeta({ layout: 'default' })

const { init, cleanup, showMemberPanel } = useChat()

const showMobileSidebar = ref(false)
const showCreateModal = ref(false)

onMounted(() => {
  init()
})

onUnmounted(() => {
  cleanup()
})
</script>

<template>
  <div class="flex h-full overflow-hidden relative">
    <!-- Mobile sidebar overlay -->
    <div
      v-if="showMobileSidebar"
      class="md:hidden fixed inset-0 z-30 bg-black/40"
      @click="showMobileSidebar = false"
    />

    <!-- Sidebar -->
    <div
      class="shrink-0 h-full z-30 transition-transform duration-200
        fixed md:relative
        w-64 md:w-56
        bg-background md:bg-transparent
        shadow-xl md:shadow-none"
      :class="showMobileSidebar ? 'translate-x-0' : '-translate-x-full md:translate-x-0'"
    >
      <ChatSidebar
        @navigate="showMobileSidebar = false"
        @create-channel="showCreateModal = true"
      />
    </div>

    <!-- Main content -->
    <div class="flex-1 flex min-w-0 min-h-0">
      <div class="flex-1 flex flex-col min-w-0">
        <!-- Mobile sidebar toggle -->
        <div class="md:hidden flex items-center px-2 py-1.5 border-b bg-background">
          <button
            @click="showMobileSidebar = !showMobileSidebar"
            class="inline-flex items-center justify-center h-8 w-8 rounded-md hover:bg-accent transition-colors"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
              <line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        </div>

        <ChatConversation />
      </div>

      <!-- Member panel -->
      <ChatMemberPanel v-if="showMemberPanel" class="hidden md:flex" />
    </div>

    <!-- Create channel modal -->
    <ChatCreateModal v-if="showCreateModal" @close="showCreateModal = false" />
  </div>
</template>
