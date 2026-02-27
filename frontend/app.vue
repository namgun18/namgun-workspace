<script setup lang="ts">
const { fetchAppConfig, brandColor, defaultTheme, favicon } = useAppConfig()
const { addToast } = useToast()
const { t } = useI18n()

fetchAppConfig()

onErrorCaptured((err: Error) => {
  console.error('[Global Error Boundary]', err)
  addToast('error', err.message || t('error.unexpectedError'))
  return false
})

// hex → HSL conversion (returns "H S% L%" string without hsl() wrapper)
function hexToHsl(hex: string): string | null {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  if (!m) return null
  let r = parseInt(m[1], 16) / 255
  let g = parseInt(m[2], 16) / 255
  let b = parseInt(m[3], 16) / 255
  const max = Math.max(r, g, b), min = Math.min(r, g, b)
  let h = 0, s = 0
  const l = (max + min) / 2
  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break
      case g: h = ((b - r) / d + 2) / 6; break
      case b: h = ((r - g) / d + 4) / 6; break
    }
  }
  return `${Math.round(h * 360)} ${Math.round(s * 100)}% ${Math.round(l * 100)}%`
}

// Inject brand color as --primary CSS variable (overrides main.css default)
watchEffect(() => {
  if (!import.meta.client) return
  const hsl = hexToHsl(brandColor.value)
  if (hsl) {
    document.documentElement.style.setProperty('--primary', hsl)
    document.documentElement.style.setProperty('--ring', hsl)
  }
})

// Apply default theme on first load (if user hasn't manually toggled)
watchEffect(() => {
  if (!import.meta.client) return
  const userPref = localStorage.getItem('color-theme')
  if (userPref) return // user has manually set theme, don't override

  const theme = defaultTheme.value
  if (theme === 'dark') {
    document.documentElement.classList.add('dark')
  } else if (theme === 'light') {
    document.documentElement.classList.remove('dark')
  }
  // 'system' — leave as-is (handled by Nuxt color-mode or browser default)
})

// Dynamic favicon
useHead({
  link: computed(() => {
    const href = favicon.value
    if (!href) return []
    return [{ rel: 'icon', href, key: 'dynamic-favicon' }]
  }),
})
</script>

<template>
  <NuxtLayout>
    <NuxtPage />
  </NuxtLayout>
  <UiToast />
</template>
