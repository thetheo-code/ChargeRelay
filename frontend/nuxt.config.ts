// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  compatibilityDate: '2025-07-15',
  devtools: { enabled: true },
  ssr: false,

  runtimeConfig: {
    public: {
      // Override at build time via DEFAULT_LOCALE env var (e.g. "en" or "de").
      // Falls back to "de" when not set.
      defaultLocale: process.env.DEFAULT_LOCALE || 'de',
    },
  },

  nitro: {
    devProxy: {
      '/api': { target: 'http://localhost:8000/api', changeOrigin: true },
    },
  },
})
