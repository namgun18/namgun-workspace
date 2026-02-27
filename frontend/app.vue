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

// hex → HSL conversion
function hexToHsl(hex: string): { h: number; s: number; l: number } | null {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  if (!m) return null
  const r = parseInt(m[1], 16) / 255
  const g = parseInt(m[2], 16) / 255
  const b = parseInt(m[3], 16) / 255
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
  return {
    h: Math.round(h * 360),
    s: Math.round(s * 100),
    l: Math.round(l * 100),
  }
}

// Inject brand color as full theme — hue propagates to all UI variables
function applyBrandTheme(hex: string) {
  const hsl = hexToHsl(hex)
  if (!hsl) return
  const { h, s, l } = hsl
  const darkL = Math.min(l + 7, 100)

  let style = document.getElementById('brand-theme') as HTMLStyleElement | null
  if (!style) {
    style = document.createElement('style')
    style.id = 'brand-theme'
    document.head.appendChild(style)
  }

  style.textContent = `
    :root {
      --foreground: ${h} 84% 4.9%;
      --card-foreground: ${h} 84% 4.9%;
      --primary: ${h} ${s}% ${l}%;
      --primary-foreground: 0 0% 100%;
      --secondary: ${h} 40% 96.1%;
      --secondary-foreground: ${h} 47.4% 11.2%;
      --muted: ${h} 40% 96.1%;
      --muted-foreground: ${h} 16.3% 46.9%;
      --accent: ${h} 95% 93%;
      --accent-foreground: ${h} 83% 40%;
      --border: ${h} 31.8% 91.4%;
      --input: ${h} 31.8% 91.4%;
      --ring: ${h} ${s}% ${l}%;
      --popover-foreground: ${h} 84% 4.9%;
    }
    .dark {
      --background: ${h} 84% 4.9%;
      --foreground: ${h} 40% 98%;
      --card: ${h} 84% 4.9%;
      --card-foreground: ${h} 40% 98%;
      --primary: ${h} ${Math.min(s + 8, 100)}% ${darkL}%;
      --primary-foreground: ${h} 84% 5%;
      --secondary: ${h} 32.6% 17.5%;
      --secondary-foreground: ${h} 40% 98%;
      --muted: ${h} 32.6% 17.5%;
      --muted-foreground: ${h} 20.2% 65.1%;
      --accent: ${h} 50% 20%;
      --accent-foreground: ${h} 95% 93%;
      --border: ${h} 32.6% 17.5%;
      --input: ${h} 32.6% 17.5%;
      --ring: ${h} ${Math.min(s + 8, 100)}% ${darkL}%;
      --popover: ${h} 84% 4.9%;
      --popover-foreground: ${h} 40% 98%;
    }
  `
}

watchEffect(() => {
  if (!import.meta.client) return
  applyBrandTheme(brandColor.value)
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
