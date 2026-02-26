<script setup lang="ts">
import type { ToastType } from '~/composables/useToast'

const { toasts, removeToast } = useToast()

const iconMap: Record<ToastType, string> = {
  success: 'M9 12l2 2 4-4',
  error: 'M18 6 6 18M6 6l12 12',
  warning: 'M12 9v4m0 4h.01',
  info: 'M12 16v-4m0-4h.01',
}

const colorMap: Record<ToastType, string> = {
  success: 'bg-green-500',
  error: 'bg-red-500',
  warning: 'bg-yellow-500',
  info: 'bg-blue-500',
}

const borderColorMap: Record<ToastType, string> = {
  success: 'border-green-500/30',
  error: 'border-red-500/30',
  warning: 'border-yellow-500/30',
  info: 'border-blue-500/30',
}
</script>

<template>
  <Teleport to="body">
    <div class="fixed bottom-4 right-4 z-[9999] flex flex-col gap-2 max-w-sm w-full pointer-events-none">
      <TransitionGroup
        enter-active-class="transition-all duration-300 ease-out"
        enter-from-class="opacity-0 translate-y-4 scale-95"
        enter-to-class="opacity-100 translate-y-0 scale-100"
        leave-active-class="transition-all duration-200 ease-in"
        leave-from-class="opacity-100 translate-y-0 scale-100"
        leave-to-class="opacity-0 translate-y-2 scale-95"
      >
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="pointer-events-auto flex items-start gap-3 rounded-lg border bg-card p-4 shadow-lg"
          :class="borderColorMap[toast.type]"
        >
          <!-- Icon -->
          <div
            class="flex-shrink-0 flex items-center justify-center w-6 h-6 rounded-full text-white"
            :class="colorMap[toast.type]"
          >
            <svg
              v-if="toast.type === 'success'"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="w-3.5 h-3.5"
            >
              <path d="M20 6 9 17l-5-5" />
            </svg>
            <svg
              v-else-if="toast.type === 'error'"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="w-3.5 h-3.5"
            >
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
            <svg
              v-else-if="toast.type === 'warning'"
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="w-3.5 h-3.5"
            >
              <path d="M12 9v4" />
              <path d="M12 17h.01" />
            </svg>
            <svg
              v-else
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2.5"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="w-3.5 h-3.5"
            >
              <path d="M12 16v-4" />
              <path d="M12 8h.01" />
            </svg>
          </div>

          <!-- Message -->
          <p class="flex-1 text-sm text-card-foreground leading-snug">
            {{ toast.message }}
          </p>

          <!-- Close button -->
          <button
            class="flex-shrink-0 text-muted-foreground hover:text-foreground transition-colors"
            @click="removeToast(toast.id)"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
              stroke-linejoin="round"
              class="w-4 h-4"
            >
              <path d="M18 6 6 18" />
              <path d="m6 6 12 12" />
            </svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
