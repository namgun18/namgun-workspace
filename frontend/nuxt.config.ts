export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',

  app: {
    head: {
      htmlAttrs: { lang: 'ko' },
      title: 'Workspace',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      ],
    },
  },

  modules: [
    '@nuxtjs/tailwindcss',
    '@nuxtjs/color-mode',
  ],

  colorMode: {
    classSuffix: '',
  },

  css: ['~/assets/css/main.css'],

  // /api/**, /oauth/** → FastAPI 백엔드 프록시
  nitro: {
    devProxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/oauth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },

  routeRules: {
    '/api/**': { proxy: 'http://backend:8000/api/**' },
  },
})
