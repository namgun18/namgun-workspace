export default defineNuxtConfig({
  compatibilityDate: '2025-01-01',

  app: {
    head: {
      htmlAttrs: { lang: 'ko' },
      title: process.env.APP_NAME || 'Workspace',
      titleTemplate: `%s | ${process.env.APP_NAME || 'Workspace'}`,
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'theme-color', content: process.env.BRAND_COLOR || '#3B82F6' },
      ],
    },
  },

  modules: [
    '@nuxtjs/tailwindcss',
    '@nuxtjs/color-mode',
    '@nuxtjs/i18n',
  ],

  i18n: {
    locales: [
      { code: 'ko', language: 'ko-KR', name: '한국어', file: 'ko.json' },
      { code: 'en', language: 'en-US', name: 'English', file: 'en.json' },
    ],
    defaultLocale: 'ko',
    strategy: 'no_prefix',
    langDir: 'locales',
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'i18n_locale',
      fallbackLocale: 'ko',
    },
  },

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
