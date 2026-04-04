<template>
  <div class="app">
    <header class="topbar">
      <div class="topbar__inner">
        <div class="topbar__title">
          OCPP Ladestation
        </div>
        <span class="topbar__refresh" :class="{ spinning: loading }" @click="refresh">↻</span>
      </div>
    </header>

    <!-- Aktive Ladung -->
    <section class="active-section">
      <div v-if="activeLoading" class="active-card active-card--loading">
        <div class="pulse">Lade aktive Session …</div>
      </div>

      <div v-else-if="activeSessions.length === 0" class="active-card active-card--idle">
        <div class="idle-text">Kein aktiver Ladevorgang</div>
      </div>

      <div v-else v-for="s in activeSessions" :key="s.session_id" class="active-card active-card--charging">
        <div class="active-card__header">
          <div>
            <div class="active-card__label">Aktuelle Ladung</div>
            <div class="active-card__cp">{{ s.model || s.charge_point_id }} <span class="badge">Connector {{ s.connector_id }}</span></div>
          </div>
          <div class="active-card__tag">
            <div class="active-card__label">Ausweis</div>
            <div class="active-card__value">{{ s.id_tag }}</div>
          </div>
        </div>

        <div class="active-card__metrics">
          <div class="metric">
            <div class="metric__label">Laufzeit</div>
            <div class="metric__value">{{ formatDuration(s.duration_seconds) }}</div>
          </div>
          <div class="metric" v-if="getMeter(s, 'Energy.Active.Import.Register')">
            <div class="metric__label">Energie</div>
            <div class="metric__value">{{ formatEnergy(getMeter(s, 'Energy.Active.Import.Register')) }}</div>
          </div>
          <div class="metric" v-if="getMeter(s, 'Power.Active.Import')">
            <div class="metric__label">Leistung</div>
            <div class="metric__value">{{ formatPower(getMeter(s, 'Power.Active.Import')) }} kW</div>
          </div>
          <div class="metric" v-if="getMeter(s, 'Current.Import')">
            <div class="metric__label">Strom</div>
            <div class="metric__value">{{ Number(getMeter(s, 'Current.Import')?.value).toFixed(1) }} A</div>
          </div>
          <div class="metric" v-if="getMeter(s, 'Voltage')">
            <div class="metric__label">Spannung</div>
            <div class="metric__value">{{ Number(getMeter(s, 'Voltage')?.value).toFixed(0) }} V</div>
          </div>
          <div class="metric" v-if="getMeter(s, 'SoC')">
            <div class="metric__label">Ladestand</div>
            <div class="metric__value">{{ Number(getMeter(s, 'SoC')?.value).toFixed(0) }} %</div>
          </div>
          <div class="metric">
            <div class="metric__label">Gestartet</div>
            <div class="metric__value metric__value--sm">{{ formatDate(s.start_time) }}</div>
          </div>
        </div>

        <div class="progress-bar-wrap" v-if="getMeter(s, 'SoC')">
          <div class="progress-bar" :style="{ width: Number(getMeter(s, 'SoC')?.value) + '%' }"></div>
        </div>
      </div>
    </section>

    <!-- Letzte Ladevorgänge -->
    <section class="history-section">
      <h2 class="history-title">Letzte Ladevorgänge</h2>

      <div v-if="historyLoading" class="pulse">Lade Verlauf …</div>

      <div v-else class="table-wrap">
        <table class="session-table">
          <thead>
            <tr>
              <th>Ladestation</th>
              <th>Ausweis</th>
              <th>Start</th>
              <th>Ende</th>
              <th>Energie</th>
              <th>Grund</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in sessions" :key="s.session_id" :class="{ 'row--active': !s.stop_time }">
              <td>
                <span class="cp-name">{{ s.model || s.charge_point_id }}</span>
                <span class="connector-badge">C{{ s.connector_id }}</span>
              </td>
              <td class="mono">{{ s.id_tag }}</td>
              <td class="mono">{{ formatDate(s.start_time) }}</td>
              <td class="mono">{{ s.stop_time ? formatDate(s.stop_time) : '–' }}</td>
              <td class="mono energy">{{ s.energy_kwh != null ? s.energy_kwh.toFixed(3) + ' kWh' : '–' }}</td>
              <td>{{ s.stop_reason || '–' }}</td>
              <td>
                <span v-if="!s.stop_time" class="status status--active">Aktiv</span>
                <span v-else class="status status--done">Fertig</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="pagination">
        <button :disabled="page <= 1" @click="changePage(page - 1)">‹ Zurück</button>
        <span>Seite {{ page }} / {{ totalPages }}</span>
        <button :disabled="page >= totalPages" @click="changePage(page + 1)">Weiter ›</button>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
const API = 'http://localhost:8000'

interface MeterValue { measurand: string; value: string; unit: string; timestamp: string }
interface ActiveSession {
  session_id: number; connector_id: number; transaction_id: number | null
  id_tag: string; start_time: string; start_meter_wh: number | null
  charge_point_id: string; model: string | null; vendor: string | null
  duration_seconds: number | null; latest_meter_values: MeterValue[]
}
interface Session {
  session_id: number; connector_id: number; transaction_id: number | null
  id_tag: string; start_time: string; stop_time: string | null
  start_meter_wh: number | null; stop_meter_wh: number | null
  energy_kwh: number | null; stop_reason: string | null
  charge_point_id: string; model: string | null; vendor: string | null
}

const activeSessions = ref<ActiveSession[]>([])
const activeLoading = ref(true)
const sessions = ref<Session[]>([])
const historyLoading = ref(true)
const loading = ref(false)
const page = ref(1)
const totalPages = ref(1)
const PAGE_SIZE = 20

async function fetchActive() {
  activeLoading.value = true
  try {
    const data = await $fetch<ActiveSession[]>(`${API}/api/active`)
    activeSessions.value = data
  } catch { activeSessions.value = [] }
  finally { activeLoading.value = false }
}

async function fetchSessions() {
  historyLoading.value = true
  try {
    const data = await $fetch<{ total: number; page: number; pages: number; sessions: Session[] }>(
      `${API}/api/sessions`, { query: { page: page.value, page_size: PAGE_SIZE } }
    )
    sessions.value = data.sessions
    totalPages.value = data.pages
  } catch { sessions.value = [] }
  finally { historyLoading.value = false }
}

async function refresh() {
  loading.value = true
  await Promise.all([fetchActive(), fetchSessions()])
  loading.value = false
}

async function changePage(p: number) {
  page.value = p
  await fetchSessions()
}

function getMeter(s: ActiveSession, measurand: string) {
  return s.latest_meter_values.find(m => m.measurand === measurand) ?? null
}

function formatDuration(secs: number | null) {
  if (secs == null) return '–'
  const h = Math.floor(secs / 3600)
  const m = Math.floor((secs % 3600) / 60)
  const s = secs % 60
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

function formatDate(iso: string | null) {
  if (!iso) return '–'
  return new Date(iso).toLocaleString('de-DE', { dateStyle: 'short', timeStyle: 'short' })
}

function formatEnergy(m: MeterValue | null) {
  if (!m) return '–'
  const v = Number(m.value)
  if (m.unit === 'Wh' || (!m.unit && v > 100)) return (v / 1000).toFixed(2) + ' kWh'
  return v.toFixed(2) + ' ' + (m.unit || 'kWh')
}

function formatPower(m: MeterValue | null) {
  if (!m) return '–'
  const v = Number(m.value)
  if (m.unit === 'W') return (v / 1000).toFixed(2)
  return v.toFixed(2)
}

onMounted(() => refresh())
// Auto-refresh alle 10 Sekunden
const interval = setInterval(refresh, 10_000)
onUnmounted(() => clearInterval(interval))
</script>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: 'Inter', system-ui, sans-serif;
  background: #f0f4f8;
  color: #1a202c;
  min-height: 100vh;
}

.app { min-height: 100vh; }

/* ── Topbar ─────────────────────────────────────────────── */
.topbar {
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  padding: 0 2rem;
  height: 56px;
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}
.topbar__inner { display: flex; align-items: center; justify-content: space-between; width: 100%; }
.topbar__title { font-size: 1.1rem; font-weight: 700; letter-spacing: 0.03em; color: #1a202c; }
.topbar__refresh {
  cursor: pointer; font-size: 1.4rem; color: #3182ce;
  transition: transform 0.4s ease;
  user-select: none;
}
.topbar__refresh:hover { color: #2b6cb0; }
.topbar__refresh.spinning { animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Active section ─────────────────────────────────────── */
.active-section { padding: 2rem 2rem 1rem; }

.active-card {
  border-radius: 16px;
  padding: 2rem 2.5rem;
  width: 100%;
}

.active-card--loading,
.active-card--idle {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  min-height: 140px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.idle-text { color: #718096; font-size: 1.1rem; }

.active-card--charging {
  background: linear-gradient(135deg, #ebf8ff 0%, #e6f0fd 50%, #f0f4ff 100%);
  border: 1px solid #bee3f8;
  box-shadow: 0 4px 24px rgba(49, 130, 206, 0.1), 0 1px 4px rgba(0,0,0,0.06);
}

.active-card__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}
.active-card__label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em; color: #3182ce; margin-bottom: 0.25rem; }
.active-card__cp { font-size: 1.5rem; font-weight: 700; color: #1a202c; display: flex; align-items: center; gap: 0.6rem; }
.active-card__tag .active-card__value { font-size: 1rem; font-family: monospace; color: #2d3748; }
.badge {
  font-size: 0.7rem; background: #bee3f8; color: #2b6cb0;
  padding: 2px 8px; border-radius: 99px; font-weight: 600;
}

.active-card__metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem 2.5rem;
  margin-bottom: 1.5rem;
}
.metric__label { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; color: #3182ce; margin-bottom: 0.2rem; }
.metric__value { font-size: 1.6rem; font-weight: 700; color: #1a202c; font-variant-numeric: tabular-nums; }
.metric__value--sm { font-size: 1rem; font-weight: 400; color: #4a5568; }

.progress-bar-wrap {
  background: #e2e8f0;
  border-radius: 99px;
  height: 8px;
  overflow: hidden;
}
.progress-bar {
  height: 100%;
  border-radius: 99px;
  background: linear-gradient(90deg, #3182ce, #63b3ed);
  transition: width 1s ease;
}

/* ── History section ────────────────────────────────────── */
.history-section { padding: 1rem 2rem 3rem; }
.history-title { font-size: 1.1rem; font-weight: 600; color: #4a5568; margin-bottom: 1rem; letter-spacing: 0.04em; }

.table-wrap {
  overflow-x: auto;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  box-shadow: 0 1px 4px rgba(0,0,0,0.06);
}

.session-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
}
.session-table thead {
  background: #f7fafc;
}
.session-table th {
  padding: 0.75rem 1rem;
  text-align: left;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #718096;
  border-bottom: 1px solid #e2e8f0;
  white-space: nowrap;
}
.session-table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid #f0f4f8;
  color: #2d3748;
  vertical-align: middle;
}
.session-table tbody tr:last-child td { border-bottom: none; }
.session-table tbody tr { background: #ffffff; transition: background 0.15s; }
.session-table tbody tr:hover { background: #f7fafc; }
.session-table tbody tr.row--active { background: #ebf8ff; }

.mono { font-family: 'JetBrains Mono', 'Fira Code', monospace; }
.energy { color: #276749; font-weight: 600; }

.cp-name { font-weight: 600; color: #1a202c; }
.connector-badge {
  display: inline-block; margin-left: 6px;
  font-size: 0.65rem; background: #edf2f7; color: #718096;
  padding: 1px 6px; border-radius: 99px;
}

.status {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 99px;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.05em;
}
.status--active { background: #c6f6d5; color: #276749; }
.status--done { background: #edf2f7; color: #718096; }

/* ── Pagination ─────────────────────────────────────────── */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1.5rem;
  color: #718096;
  font-size: 0.875rem;
}
.pagination button {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  color: #4a5568;
  padding: 6px 16px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.875rem;
  transition: background 0.15s, color 0.15s;
}
.pagination button:hover:not(:disabled) { background: #edf2f7; color: #1a202c; }
.pagination button:disabled { opacity: 0.35; cursor: not-allowed; }

/* ── Pulse ──────────────────────────────────────────────── */
.pulse {
  color: #3182ce;
  animation: pulse 1.2s ease-in-out infinite;
}
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }
</style>
