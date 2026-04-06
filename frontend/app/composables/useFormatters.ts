import type { ActiveSession, MeterValue } from '~/types'

export function useFormatters() {
  const { numLocale } = useLocale()

  function getMeter(s: ActiveSession, measurand: string): MeterValue | null {
    return s.latest_meter_values.find(m => m.measurand === measurand) ?? null
  }

  function formatDuration(secs: number | null): string {
    if (secs == null) return '–'
    const h = Math.floor(secs / 3600)
    const m = Math.floor((secs % 3600) / 60)
    const s = secs % 60
    if (h > 0) return `${h}h ${m}m`
    if (m > 0) return `${m}m ${s}s`
    return `${s}s`
  }

  function formatDate(iso: string | null): string {
    if (!iso) return '–'
    return new Date(iso).toLocaleString(numLocale.value, { dateStyle: 'short', timeStyle: 'short' })
  }

  function formatTime(iso: string | null): string {
    if (!iso) return '–'
    return new Date(iso).toLocaleString(numLocale.value, { timeStyle: 'short' })
  }

  function formatEnergy(m: MeterValue | null): string {
    if (!m) return '–'
    const v = Number(m.value)
    const kwh = m.unit === 'Wh' ? v / 1000 : v
    return kwh.toLocaleString(numLocale.value, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  function formatPower(m: MeterValue | null): string {
    if (!m) return '–'
    const v = Number(m.value)
    const kw = m.unit === 'W' ? v / 1000 : v
    return kw.toLocaleString(numLocale.value, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  }

  return { getMeter, formatDuration, formatDate, formatTime, formatEnergy, formatPower }
}
