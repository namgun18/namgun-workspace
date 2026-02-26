<script setup lang="ts">
const emit = defineEmits<{
  navigate: []
}>()

const { boards, loadingBoards, mustReadPosts } = useBoard()
const { user } = useAuth()
const route = useRoute()

const currentBoardId = computed(() => route.params.boardId as string | undefined)
</script>

<template>
  <aside class="flex flex-col h-full border-r bg-muted/30">
    <div class="flex items-center justify-between px-3 py-3 border-b">
      <NuxtLink to="/board" class="text-sm font-semibold text-foreground hover:text-primary transition-colors" @click="emit('navigate')">
        {{ $t('nav.board') }}
      </NuxtLink>
      <NuxtLink
        v-if="user?.is_admin"
        to="/board?create=1"
        class="h-6 w-6 flex items-center justify-center rounded hover:bg-accent text-muted-foreground hover:text-foreground transition-colors"
        :title="$t('board.sidebar.addBoard')"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-4 w-4">
          <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
        </svg>
      </NuxtLink>
    </div>

    <!-- Must-read badge -->
    <NuxtLink
      v-if="mustReadPosts.length > 0"
      to="/board?view=must-read"
      class="flex items-center gap-2 mx-3 mt-2 px-3 py-2 text-sm rounded-md bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 border border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900 transition-colors"
      @click="emit('navigate')"
    >
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4 shrink-0">
        <circle cx="12" cy="12" r="10" /><line x1="12" y1="8" x2="12" y2="12" /><line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>
      <span class="flex-1">{{ $t('board.sidebar.unreadMustRead') }}</span>
      <span class="text-xs font-semibold px-1.5 py-0.5 rounded-full bg-red-500 text-white">
        {{ mustReadPosts.length }}
      </span>
    </NuxtLink>

    <nav class="flex-1 p-3 space-y-0.5 overflow-auto">
      <div v-if="loadingBoards" class="space-y-2">
        <div v-for="i in 4" :key="i" class="h-8 bg-muted/50 rounded animate-pulse" />
      </div>

      <template v-else>
        <NuxtLink
          v-for="board in boards"
          :key="board.id"
          :to="`/board/${board.id}`"
          class="w-full flex items-center gap-3 px-3 py-2 text-sm rounded-md transition-colors"
          :class="currentBoardId === board.id
            ? 'bg-accent text-accent-foreground font-medium'
            : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'"
          @click="emit('navigate')"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4 shrink-0">
            <rect x="3" y="3" width="18" height="18" rx="2" /><line x1="3" y1="9" x2="21" y2="9" /><line x1="9" y1="21" x2="9" y2="9" />
          </svg>
          <span class="flex-1 text-left truncate">{{ board.name }}</span>
        </NuxtLink>

        <p v-if="boards.length === 0" class="text-xs text-muted-foreground px-3 py-4 text-center">
          {{ $t('board.sidebar.empty') }}
        </p>
      </template>
    </nav>

    <!-- Bookmarks / Search links -->
    <div class="border-t p-3 space-y-0.5">
      <NuxtLink
        to="/board?view=bookmarks"
        class="w-full flex items-center gap-3 px-3 py-2 text-sm rounded-md text-muted-foreground hover:bg-accent/50 hover:text-foreground transition-colors"
        @click="emit('navigate')"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4 shrink-0">
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
        </svg>
        <span class="flex-1 text-left">{{ $t('board.sidebar.myBookmarks') }}</span>
      </NuxtLink>
      <NuxtLink
        to="/board?view=search"
        class="w-full flex items-center gap-3 px-3 py-2 text-sm rounded-md text-muted-foreground hover:bg-accent/50 hover:text-foreground transition-colors"
        @click="emit('navigate')"
      >
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="h-4 w-4 shrink-0">
          <circle cx="11" cy="11" r="8" /><line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
        <span class="flex-1 text-left">{{ $t('common.search') }}</span>
      </NuxtLink>
    </div>
  </aside>
</template>
