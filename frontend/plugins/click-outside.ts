export default defineNuxtPlugin((nuxtApp) => {
  nuxtApp.vueApp.directive('click-outside', {
    mounted(el, binding) {
      el._clickOutside = (e: Event) => {
        if (!el.contains(e.target as Node)) {
          binding.value(e)
        }
      }
      // Delay to avoid catching the same click that triggered mount
      requestAnimationFrame(() => {
        document.addEventListener('click', el._clickOutside)
      })
    },
    unmounted(el) {
      document.removeEventListener('click', el._clickOutside)
    },
  })
})
