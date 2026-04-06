import de from '~/locales/de.json'
import en from '~/locales/en.json'

// ---------------------------------------------------------------------------
// Locale registry — add a new language here + create locales/<code>.json
// ---------------------------------------------------------------------------

export const LOCALES = [
  { code: 'de' as const, label: '🇩🇪 DE', numLocale: 'de-DE' },
  { code: 'en' as const, label: '🇬🇧 EN', numLocale: 'en-US' },
] satisfies { code: string; label: string; numLocale: string }[]

export type LocaleCode = (typeof LOCALES)[number]['code']

const messages: Record<LocaleCode, Record<string, unknown>> = { de, en }

// Set of valid codes, derived from LOCALES so it stays in sync automatically.
const validCodes = new Set(LOCALES.map(l => l.code))

// ---------------------------------------------------------------------------
// Key lookup with dot-notation support
// ---------------------------------------------------------------------------

function lookup(obj: Record<string, unknown>, path: string): string {
  const keys = path.split('.')
  let current: unknown = obj
  for (const key of keys) {
    if (current == null || typeof current !== 'object') return path
    current = (current as Record<string, unknown>)[key]
  }
  return typeof current === 'string' ? current : path
}

// ---------------------------------------------------------------------------
// Composable
// ---------------------------------------------------------------------------

export function useLocale() {
  const config = useRuntimeConfig()

  // useState ensures the locale is shared reactively across all components.
  const locale = useState<LocaleCode>('cr_locale', () => {
    // Prefer the value the user explicitly saved in localStorage.
    if (import.meta.client) {
      const stored = localStorage.getItem('cr_locale')
      if (stored && validCodes.has(stored as LocaleCode)) return stored as LocaleCode
    }
    // Fall back to the build-time default configured via DEFAULT_LOCALE env var.
    const def = (config.public.defaultLocale as string) || 'de'
    return (validCodes.has(def as LocaleCode) ? def : 'de') as LocaleCode
  })

  // ------------------------------------------------------------------
  // t() — translate a dot-notation key with optional interpolation
  // ------------------------------------------------------------------

  function t(key: string, params?: Record<string, string | number>): string {
    let str = lookup(messages[locale.value] as Record<string, unknown>, key)
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        str = str.replaceAll(`{${k}}`, String(v))
      }
    }
    return str
  }

  // ------------------------------------------------------------------
  // setLocale() — switch language and persist the choice
  // ------------------------------------------------------------------

  function setLocale(lang: LocaleCode) {
    locale.value = lang
    if (import.meta.client) {
      localStorage.setItem('cr_locale', lang)
    }
  }

  // ------------------------------------------------------------------
  // numLocale — BCP-47 tag for number / date formatting
  // ------------------------------------------------------------------

  const numLocale = computed(() =>
    LOCALES.find(l => l.code === locale.value)?.numLocale ?? 'de-DE'
  )

  return { locale, t, setLocale, numLocale }
}
