<script setup lang="ts">
const { user, logout } = useAuth()
const colorMode = useColorMode()
const route = useRoute()
const mobileMenuOpen = ref(false)

const { notifications, unreadCount, showDropdown, markAsRead, markAllAsRead } = useNotifications()

const bellRef = ref<HTMLElement | null>(null)

function toggleNotifications() {
  showDropdown.value = !showDropdown.value
}

function onClickOutsideNotifications(e: Event) {
  if (bellRef.value && !bellRef.value.contains(e.target as Node)) {
    showDropdown.value = false
  }
}

function formatNotifTime(iso: string) {
  const d = new Date(iso)
  const now = new Date()
  const diffMs = now.getTime() - d.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 1) return '방금'
  if (diffMin < 60) return `${diffMin}분 전`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}시간 전`
  const diffDay = Math.floor(diffHr / 24)
  return `${diffDay}일 전`
}

async function onNotificationClick(notif: any) {
  if (!notif.is_read) {
    await markAsRead([notif.id])
  }
  showDropdown.value = false
  if (notif.link) {
    navigateTo(notif.link)
  }
}

onMounted(() => {
  if (import.meta.client) {
    document.addEventListener('click', onClickOutsideNotifications)
  }
})

onUnmounted(() => {
  if (import.meta.client) {
    document.removeEventListener('click', onClickOutsideNotifications)
  }
})

function toggleDark() {
  colorMode.preference = colorMode.value === 'dark' ? 'light' : 'dark'
}
</script>

<template>
  <header class="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
    <div class="flex h-14 items-center justify-between px-3 sm:px-4 lg:px-6">
      <!-- Logo + Nav -->
      <div class="flex items-center gap-2 sm:gap-6">
        <NuxtLink to="/" class="flex items-center gap-2 font-bold text-lg shrink-0">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-6 w-6">
            <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
            <polyline points="9 22 9 12 15 12 15 22" />
          </svg>
          <span class="hidden sm:inline">namgun.or.kr</span>
        </NuxtLink>

        <!-- Desktop nav -->
        <nav v-if="user" class="hidden sm:flex items-center gap-1">
          <NuxtLink
            to="/"
            class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors"
            :class="route.path === '/' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'"
          >
            대시보드
          </NuxtLink>
          <NuxtLink
            to="/files"
            class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors"
            :class="route.path.startsWith('/files') ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'"
          >
            파일
          </NuxtLink>
          <NuxtLink
            to="/mail"
            class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors"
            :class="route.path === '/mail' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'"
          >
            메일
          </NuxtLink>
          <NuxtLink
            to="/chat"
            class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors"
            :class="route.path === '/chat' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'"
          >
            채팅
          </NuxtLink>
          <NuxtLink
            to="/calendar"
            class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors"
            :class="route.path === '/calendar' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'"
          >
            캘린더
          </NuxtLink>
          <NuxtLink
            to="/contacts"
            class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors"
            :class="route.path === '/contacts' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'"
          >
            연락처
          </NuxtLink>
          <NuxtLink
            to="/meetings"
            class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors"
            :class="route.path === '/meetings' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'"
          >
            회의
          </NuxtLink>
          <NuxtLink
            to="/git"
            class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors"
            :class="route.path === '/git' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'"
          >
            Git
          </NuxtLink>
          <NuxtLink
            v-if="user.is_admin"
            to="/admin/dashboard"
            class="px-3 py-1.5 text-sm font-medium rounded-md transition-colors"
            :class="route.path.startsWith('/admin') ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:text-foreground hover:bg-accent/50'"
          >
            관리
          </NuxtLink>
        </nav>
      </div>

      <!-- Right side -->
      <div class="flex items-center gap-1 sm:gap-3">
        <!-- Mobile nav toggle -->
        <button
          v-if="user"
          @click="mobileMenuOpen = !mobileMenuOpen"
          class="sm:hidden inline-flex items-center justify-center h-9 w-9 rounded-md hover:bg-accent transition-colors"
        >
          <svg v-if="!mobileMenuOpen" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5">
            <line x1="3" y1="12" x2="21" y2="12" /><line x1="3" y1="6" x2="21" y2="6" /><line x1="3" y1="18" x2="21" y2="18" />
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5">
            <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>

        <!-- Notification bell -->
        <div v-if="user" ref="bellRef" class="relative">
          <button
            @click="toggleNotifications"
            class="inline-flex items-center justify-center h-9 w-9 rounded-md hover:bg-accent transition-colors relative"
            title="알림"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5">
              <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" /><path d="M13.73 21a2 2 0 0 1-3.46 0" />
            </svg>
            <span
              v-if="unreadCount > 0"
              class="absolute -top-0.5 -right-0.5 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-bold text-white bg-red-500 rounded-full"
            >
              {{ unreadCount > 99 ? '99+' : unreadCount }}
            </span>
          </button>

          <!-- Notification dropdown -->
          <div
            v-if="showDropdown"
            class="absolute right-0 top-full mt-1 w-80 bg-popover border rounded-lg shadow-lg z-50 overflow-hidden"
          >
            <div class="flex items-center justify-between px-3 py-2 border-b">
              <span class="text-sm font-semibold">알림</span>
              <button
                v-if="unreadCount > 0"
                @click="markAllAsRead"
                class="text-xs text-primary hover:underline"
              >
                모두 읽음
              </button>
            </div>
            <div class="max-h-80 overflow-y-auto">
              <div v-if="notifications.length === 0" class="px-3 py-6 text-center text-sm text-muted-foreground">
                알림이 없습니다
              </div>
              <div
                v-for="notif in notifications"
                :key="notif.id"
                @click="onNotificationClick(notif)"
                class="px-3 py-2.5 cursor-pointer hover:bg-accent/50 transition-colors border-b last:border-b-0"
                :class="notif.is_read ? 'opacity-60' : ''"
              >
                <div class="flex items-start gap-2">
                  <div v-if="!notif.is_read" class="mt-1.5 w-2 h-2 rounded-full bg-primary shrink-0" />
                  <div v-else class="mt-1.5 w-2 h-2 shrink-0" />
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium truncate">{{ notif.title }}</p>
                    <p class="text-xs text-muted-foreground truncate mt-0.5">{{ notif.body }}</p>
                    <p class="text-[10px] text-muted-foreground mt-1">{{ formatNotifTime(notif.created_at) }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Dark mode toggle (ClientOnly: SSR은 colorMode 감지 불가 → v-if 불일치 방지) -->
        <button
          @click="toggleDark"
          class="inline-flex items-center justify-center h-9 w-9 rounded-md hover:bg-accent transition-colors"
        >
          <ClientOnly>
            <svg v-if="colorMode.value === 'dark'" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5">
              <circle cx="12" cy="12" r="5" /><line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" /><line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" /><line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" /><line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="h-5 w-5">
              <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
            </svg>
            <template #fallback>
              <div class="h-5 w-5" />
            </template>
          </ClientOnly>
        </button>

        <!-- User dropdown -->
        <UiDropdownMenu v-if="user">
          <template #trigger>
            <button class="flex items-center gap-2 rounded-md px-1.5 sm:px-2 py-1 hover:bg-accent transition-colors">
              <UiAvatar
                :src="user.avatar_url"
                :alt="user.display_name ?? user.username"
                :fallback="(user.display_name ?? user.username).charAt(0).toUpperCase()"
                class="h-8 w-8"
              />
              <span class="hidden sm:inline text-sm font-medium max-w-[120px] truncate">
                {{ user.display_name ?? user.username }}
              </span>
            </button>
          </template>
          <template #content>
            <div class="px-3 py-2 text-sm text-muted-foreground border-b">
              {{ user.email }}
            </div>
            <NuxtLink
              to="/profile"
              class="block w-full px-3 py-2 text-sm text-left hover:bg-accent transition-colors"
            >
              프로필
            </NuxtLink>
            <NuxtLink
              v-if="user.is_admin"
              to="/admin/dashboard"
              class="block w-full px-3 py-2 text-sm text-left hover:bg-accent transition-colors"
            >
              관리 대시보드
            </NuxtLink>
            <button
              @click="logout"
              class="w-full px-3 py-2 text-sm text-left hover:bg-accent transition-colors text-destructive border-t"
            >
              로그아웃
            </button>
          </template>
        </UiDropdownMenu>
      </div>
    </div>

    <!-- Mobile navigation dropdown -->
    <div
      v-if="mobileMenuOpen && user"
      class="sm:hidden border-t bg-background px-3 py-2 space-y-1"
    >
      <NuxtLink
        to="/"
        @click="mobileMenuOpen = false"
        class="block px-3 py-2 text-sm font-medium rounded-md transition-colors"
        :class="route.path === '/' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent/50'"
      >
        대시보드
      </NuxtLink>
      <NuxtLink
        to="/files"
        @click="mobileMenuOpen = false"
        class="block px-3 py-2 text-sm font-medium rounded-md transition-colors"
        :class="route.path.startsWith('/files') ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent/50'"
      >
        파일
      </NuxtLink>
      <NuxtLink
        to="/mail"
        @click="mobileMenuOpen = false"
        class="block px-3 py-2 text-sm font-medium rounded-md transition-colors"
        :class="route.path === '/mail' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent/50'"
      >
        메일
      </NuxtLink>
      <NuxtLink
        to="/chat"
        @click="mobileMenuOpen = false"
        class="block px-3 py-2 text-sm font-medium rounded-md transition-colors"
        :class="route.path === '/chat' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent/50'"
      >
        채팅
      </NuxtLink>
      <NuxtLink
        to="/calendar"
        @click="mobileMenuOpen = false"
        class="block px-3 py-2 text-sm font-medium rounded-md transition-colors"
        :class="route.path === '/calendar' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent/50'"
      >
        캘린더
      </NuxtLink>
      <NuxtLink
        to="/contacts"
        @click="mobileMenuOpen = false"
        class="block px-3 py-2 text-sm font-medium rounded-md transition-colors"
        :class="route.path === '/contacts' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent/50'"
      >
        연락처
      </NuxtLink>
      <NuxtLink
        to="/meetings"
        @click="mobileMenuOpen = false"
        class="block px-3 py-2 text-sm font-medium rounded-md transition-colors"
        :class="route.path === '/meetings' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent/50'"
      >
        회의
      </NuxtLink>
      <NuxtLink
        to="/git"
        @click="mobileMenuOpen = false"
        class="block px-3 py-2 text-sm font-medium rounded-md transition-colors"
        :class="route.path === '/git' ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent/50'"
      >
        Git
      </NuxtLink>
      <NuxtLink
        v-if="user.is_admin"
        to="/admin/users"
        @click="mobileMenuOpen = false"
        class="block px-3 py-2 text-sm font-medium rounded-md transition-colors"
        :class="route.path.startsWith('/admin') ? 'bg-accent text-accent-foreground' : 'text-muted-foreground hover:bg-accent/50'"
      >
        관리
      </NuxtLink>
    </div>
    <div class="h-0.5 bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-500 opacity-80" />
  </header>
</template>
