<template>
  <div class="app">

    <AppTopbar
      :activeTab="activeTab"
      :loading="loading"
      @update:activeTab="activeTab = $event"
      @refresh="refresh"
      @toSessions="switchToSessions"
      @toVehicles="switchToVehicles"
      @toReports="switchToReports"
    />

    <!-- ── Übersicht ───────────────────────────────────────────────────── -->
    <template v-if="activeTab === 'overview'">
      <ActiveSection
        :loading="activeLoading"
        :sessions="activeSessions"
        :vehicles="vehicles"
        :sessionVehicleSelection="sessionVehicleSelection"
        @updateSelection="sessionVehicleSelection[$event.sessionId] = $event.vehicleId"
        @assignVehicle="assignVehicle"
      />
      <OverviewCharts :loading="statsLoading" :stats="stats" :error="statsError" />
    </template>

    <!-- ── Ladevorgänge ───────────────────────────────────────────────── -->
    <template v-if="activeTab === 'sessions'">
      <SessionHistory
        :loading="historyLoading"
        :sessions="sessions"
        :page="page"
        :totalPages="totalPages"
        @changePage="changePage"
        @editSession="openSessionEdit"
      />
    </template>

    <!-- ── Fahrzeuge ───────────────────────────────────────────────────── -->
    <template v-if="activeTab === 'vehicles'">
      <VehiclesSection
        :loading="vehiclesLoading"
        :vehicles="vehicles"
        @openNew="openNewVehicleForm"
        @openEdit="openEditVehicleForm"
        @confirmDelete="confirmDeleteVehicle"
      />
    </template>

    <!-- ── Reports ───────────────────────────────────────────────────── -->
    <template v-if="activeTab === 'reports'">
      <ReportsSection
        :loading="reportsLoading"
        :reports="reports"
        @openNew="openNewReportForm"
        @openEdit="openEditReportForm"
        @confirmDelete="confirmDeleteReport"
      />
    </template>

    <!-- ── Fahrzeug-Formular (Modal) ───────────────────────────────────── -->
    <VehicleFormModal
      v-if="showVehicleForm"
      :editingVehicle="editingVehicle"
      :saving="savingVehicle"
      @close="showVehicleForm = false"
      @save="saveVehicle"
    />

    <!-- ── Report-Formular (Modal) ───────────────────────────────────── -->
    <ReportFormModal
      v-if="showReportForm"
      :editingReport="editingReport"
      :vehicles="vehicles"
      :saving="savingReport"
      @close="showReportForm = false"
      @save="saveReport"
    />

    <!-- ── Ladung bearbeiten (Modal) ──────────────────────────────────── -->
    <SessionEditModal
      v-if="showSessionEdit && editingSession"
      :session="editingSession"
      :vehicles="vehicles"
      :saving="savingSession"
      @close="showSessionEdit = false"
      @save="saveSessionEdit"
      @delete="deleteSession"
    />

  </div>
</template>

<script setup lang="ts">
import type { Vehicle, ActiveSession, Session, Report, Stats } from '~/types'

const API = ''

// ── State ──────────────────────────────────────────────────────────────────

const activeTab = ref<'overview' | 'sessions' | 'vehicles' | 'reports'>('overview')

const activeSessions = ref<ActiveSession[]>([])
const activeLoading = ref(true)
const sessions = ref<Session[]>([])
const historyLoading = ref(true)
const loading = ref(false)
const page = ref(1)
const totalPages = ref(1)
const PAGE_SIZE = 20

const vehicles = ref<Vehicle[]>([])
const vehiclesLoading = ref(false)
const showVehicleForm = ref(false)
const savingVehicle = ref(false)
const editingVehicle = ref<Vehicle | null>(null)

const reports = ref<Report[]>([])
const reportsLoading = ref(false)
const showReportForm = ref(false)
const savingReport = ref(false)
const editingReport = ref<Report | null>(null)

const stats = ref<Stats | null>(null)
const statsLoading = ref(true)   // true = zeigt Loading-Zustand beim ersten Rendern
const statsError = ref(false)

const showSessionEdit = ref(false)
const editingSession = ref<Session | null>(null)
const savingSession = ref(false)

const sessionVehicleSelection = ref<Record<number, number | null>>({})

// ── Hilfsfunktionen ────────────────────────────────────────────────────────

function initSessionSelections() {
  for (const s of activeSessions.value) {
    if (s.vehicle_id === null && !(s.session_id in sessionVehicleSelection.value)) {
      sessionVehicleSelection.value[s.session_id] = vehicles.value[0]?.id ?? null
    }
  }
}

// ── Datenabruf ─────────────────────────────────────────────────────────────

async function fetchReports() {
  reportsLoading.value = true
  try {
    reports.value = await $fetch<Report[]>(`${API}/api/reports`)
  } catch { reports.value = [] }
  finally { reportsLoading.value = false }
}

async function fetchStats() {
  statsLoading.value = true
  statsError.value = false
  try {
    stats.value = await $fetch<Stats>(`${API}/api/stats`)
  } catch (e) {
    console.error('fetchStats failed:', e)
    statsError.value = true
    stats.value = null
  } finally {
    statsLoading.value = false
  }
}

async function fetchVehicles() {
  vehiclesLoading.value = true
  try {
    vehicles.value = await $fetch<Vehicle[]>(`${API}/api/vehicles`)
    initSessionSelections()
  } catch { vehicles.value = [] }
  finally { vehiclesLoading.value = false }
}

async function fetchActive() {
  activeLoading.value = true
  try {
    activeSessions.value = await $fetch<ActiveSession[]>(`${API}/api/active`)
    initSessionSelections()
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
  await Promise.all([fetchActive(), fetchSessions(), fetchStats()])
  loading.value = false
}

async function changePage(p: number) {
  page.value = p
  await fetchSessions()
}

async function switchToSessions() {
  activeTab.value = 'sessions'
  await fetchSessions()
}

async function switchToVehicles() {
  activeTab.value = 'vehicles'
  await fetchVehicles()
}

async function switchToReports() {
  activeTab.value = 'reports'
  await Promise.all([fetchReports(), fetchVehicles()])
}

// ── Fahrzeug-CRUD ──────────────────────────────────────────────────────────

function openNewVehicleForm() {
  editingVehicle.value = null
  showVehicleForm.value = true
}

function openEditVehicleForm(v: Vehicle) {
  editingVehicle.value = v
  showVehicleForm.value = true
}

async function saveVehicle(body: { name: string; id_tag: string | null; image_data: string | null }) {
  savingVehicle.value = true
  try {
    if (editingVehicle.value) {
      await $fetch(`${API}/api/vehicles/${editingVehicle.value.id}`, { method: 'PUT', body })
    } else {
      await $fetch(`${API}/api/vehicles`, { method: 'POST', body })
    }
    showVehicleForm.value = false
    await fetchVehicles()
  } catch {
    alert('Fehler beim Speichern. Bitte prüfe die Eingaben.')
  } finally {
    savingVehicle.value = false
  }
}

async function confirmDeleteVehicle(v: Vehicle) {
  if (!confirm(`Fahrzeug "${v.name}" wirklich löschen?`)) return
  try {
    await $fetch(`${API}/api/vehicles/${v.id}`, { method: 'DELETE' })
    await fetchVehicles()
  } catch {
    alert('Fehler beim Löschen.')
  }
}

// ── Report-CRUD ────────────────────────────────────────────────────────────

function openNewReportForm() {
  editingReport.value = null
  showReportForm.value = true
}

function openEditReportForm(r: Report) {
  editingReport.value = r
  showReportForm.value = true
}

async function saveReport(body: {
  name: string
  vehicle_ids: number[]
  deliveries: { type: string; email: string | null; interval: string | null; address: string | null; port: number | null }[]
}) {
  savingReport.value = true
  try {
    if (editingReport.value) {
      await $fetch(`${API}/api/reports/${editingReport.value.id}`, { method: 'PUT', body })
    } else {
      await $fetch(`${API}/api/reports`, { method: 'POST', body })
    }
    showReportForm.value = false
    await fetchReports()
  } catch {
    alert('Fehler beim Speichern.')
  } finally {
    savingReport.value = false
  }
}

async function confirmDeleteReport(r: Report) {
  if (!confirm(`Report „${r.name}" wirklich löschen?`)) return
  try {
    await $fetch(`${API}/api/reports/${r.id}`, { method: 'DELETE' })
    await fetchReports()
  } catch {
    alert('Fehler beim Löschen.')
  }
}

// ── Session bearbeiten (Fahrzeug ändern / entfernen) ──────────────────────

function openSessionEdit(s: Session) {
  editingSession.value = s
  showSessionEdit.value = true
}

async function saveSessionEdit({ vehicleId }: { vehicleId: number | null }) {
  if (!editingSession.value) return
  savingSession.value = true
  try {
    await $fetch(`${API}/api/sessions/${editingSession.value.session_id}/vehicle`, {
      method: 'PUT',
      body: { vehicle_id: vehicleId },
    })
    showSessionEdit.value = false
    await fetchSessions()
  } catch {
    alert('Fehler beim Speichern.')
  } finally {
    savingSession.value = false
  }
}

async function deleteSession() {
  if (!editingSession.value) return
  savingSession.value = true
  try {
    await $fetch(`${API}/api/sessions/${editingSession.value.session_id}`, {
      method: 'DELETE',
    })
    showSessionEdit.value = false
    await fetchSessions()
  } catch {
    alert('Fehler beim Löschen.')
  } finally {
    savingSession.value = false
  }
}

// ── Fahrzeug einer Session zuweisen ────────────────────────────────────────

async function assignVehicle(session_id: number) {
  const vehicle_id = sessionVehicleSelection.value[session_id]
  if (!vehicle_id) return
  try {
    await $fetch(`${API}/api/sessions/${session_id}/vehicle`, {
      method: 'PUT',
      body: { vehicle_id },
    })
    await fetchActive()
  } catch {
    alert('Fehler beim Zuweisen des Fahrzeugs.')
  }
}

// ── Lifecycle ──────────────────────────────────────────────────────────────

onMounted(async () => {
  await fetchVehicles()
  await refresh()
})
const interval = setInterval(refresh, 90_000)
onUnmounted(() => clearInterval(interval))
</script>

<style>
/* ── Reset & Base ───────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:           #f0f4f8;
  --bg-card:      #ffffff;
  --bg-card-2:    #f7fafc;
  --bg-hover:     #f0f4f8;
  --border:       #e2e8f0;
  --border-soft:  #f0f4f8;
  --text:         #1a202c;
  --text-muted:   #718096;
  --text-dim:     #a0aec0;
  --accent:       #16a34a;
  --accent-dim:   rgba(22,163,74,0.1);
  --accent-glow:  rgba(22,163,74,0.2);
  --accent-dark:  #15803d;
  --danger:       #c53030;
  --danger-dim:   #fff5f5;
  --radius:       14px;
  --radius-sm:    8px;
  --shadow:       0 1px 3px rgba(0,0,0,0.06), 0 4px 16px rgba(0,0,0,0.06);
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
  background: var(--bg);
  color: var(--text);
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

.app { min-height: 100vh; }

/* ── Topbar ─────────────────────────────────────────────────────────── */
.topbar {
  background: rgba(255,255,255,0.9);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  padding: 0 1.25rem;
  height: 54px;
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
}
.topbar__inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  max-width: 1100px;
  margin: 0 auto;
}
.topbar__brand { display: flex; align-items: center; gap: 0.5rem; }
.topbar__bolt {
  font-size: 1.2rem;
  filter: drop-shadow(0 0 6px var(--accent));
}
.topbar__title {
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--text);
}
.topbar__refresh {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.35rem;
  color: var(--accent);
  transition: transform 0.4s ease, color 0.2s;
  user-select: none;
  padding: 6px;
  border-radius: var(--radius-sm);
  line-height: 1;
}
.topbar__refresh:hover { color: #4ade80; background: var(--accent-dim); }
.topbar__refresh.spinning { animation: spin 0.7s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Topbar Nav ─────────────────────────────────────────────────────── */
.topbar__nav {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  margin: 0 auto 0 2rem;
}
.tab-btn {
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  padding: 6px 14px;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-muted);
  cursor: pointer;
  transition: color 0.15s, background 0.15s;
  white-space: nowrap;
}
.tab-btn:hover { color: var(--text); background: var(--bg-hover); }
.tab-btn--active {
  color: var(--accent);
  background: var(--accent-dim);
  font-weight: 600;
}

/* ── Page wrapper ───────────────────────────────────────────────────── */
.active-section,
.history-section,
.vehicles-section {
  padding: 1.25rem;
  width: 100%;
}
.active-section,
.history-section,
.vehicles-section {
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
}
@media (min-width: 640px) {
  .active-section,
  .history-section,
  .vehicles-section { padding: 1.75rem 2rem; }
}

/* ── State cards (loading / idle) ──────────────────────────────────── */
.state-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 3rem 2rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  text-align: center;
}
.state-card__icon { font-size: 2.5rem; }
.state-card__text { font-size: 1.1rem; font-weight: 500; color: var(--text); }
.state-card__sub { font-size: 0.875rem; color: var(--text-muted); }

/* Spinner */
.spinner {
  width: 28px; height: 28px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.75s linear infinite;
}

/* ── Charge card ────────────────────────────────────────────────────── */
.charge-card {
  background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 50%, #f0fdf4 100%);
  border: 1px solid #86efac;
  border-radius: var(--radius);
  padding: 1.25rem;
  box-shadow: 0 4px 24px rgba(22,163,74,0.1), var(--shadow);
  margin-bottom: 1rem;
  position: relative;
  overflow: hidden;
}
.charge-card::before {
  content: none;
}
@media (min-width: 640px) {
  .charge-card { padding: 1.75rem; }
}

/* Card head */
.charge-card__head {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
}
.live-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--accent);
  box-shadow: 0 0 6px var(--accent-glow);
  animation: pulse-dot 1.4s ease-in-out infinite;
  flex-shrink: 0;
}
@keyframes pulse-dot {
  0%, 100% { opacity: 1; transform: scale(1); box-shadow: 0 0 6px var(--accent-glow); }
  50%       { opacity: 0.7; transform: scale(0.85); box-shadow: 0 0 2px var(--accent-glow); }
}
.charge-card__live-label {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--accent);
}
.charge-card__sep { color: var(--text-dim); }
.charge-card__cp { font-size: 0.95rem; font-weight: 600; color: var(--text); }
.badge {
  font-size: 0.68rem;
  background: var(--accent-dim);
  color: var(--accent);
  padding: 2px 8px;
  border-radius: 99px;
  font-weight: 700;
  border: 1px solid rgba(34,197,94,0.2);
}

/* Card body */
.charge-card__body {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
@media (min-width: 600px) {
  .charge-card__body--with-vehicle {
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 1.5rem;
    align-items: center;
  }
}

/* Metrics grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem 0.75rem;
}
@media (min-width: 480px) {
  .metrics-grid { grid-template-columns: repeat(4, 1fr); gap: 1.25rem 1rem; }
}
@media (min-width: 768px) {
  .metrics-grid { grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); }
}

.metric {}
.metric__label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: var(--accent);
  margin-bottom: 0.3rem;
  opacity: 0.8;
}
.metric__value {
  font-size: 1.6rem;
  font-weight: 500;
  color: var(--text);
  font-variant-numeric: tabular-nums;
  line-height: 1.1;
}
.metric__value--accent { color: var(--accent); }
.metric__value--date {
  font-size: 0.875rem;
  font-weight: 400;
  color: var(--text-muted);
}
.metric__unit {
  font-size: 0.8rem;
  font-weight: 400;
  color: var(--text-muted);
  margin-left: 2px;
}
@media (min-width: 640px) {
  .metric__value { font-size: 2rem; }
}

/* Vehicle hero */
.vehicle-hero {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}
@media (min-width: 600px) {
  .vehicle-hero {
    align-items: flex-end;
    min-width: 160px;
    max-width: 220px;
  }
}
.vehicle-hero__img-wrap {
  width: 160px;
  aspect-ratio: 16 / 9;
  display: flex;
  align-items: center;
  justify-content: center;
}
.vehicle-hero__img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  border-radius: 10px;
  filter: drop-shadow(0 4px 16px rgba(0,0,0,0.5));
}
.vehicle-hero__placeholder { font-size: 4rem; line-height: 1; }
.vehicle-hero__name {
  font-size: 1rem;
  font-weight: 700;
  color: var(--text);
  display: flex;
  align-items: center;
  gap: 0.35rem;
}
.rfid-check {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1rem; height: 1rem;
  border-radius: 50%;
  background: var(--accent);
  color: #000;
  font-size: 0.55rem;
  font-weight: 900;
}

/* Assign block */
.assign-block { }
.assign-block__label {
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}
.vehicle-assign { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; }
.sel {
  background: var(--bg-card-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 6px 10px;
  font-size: 0.875rem;
  color: var(--text);
  cursor: pointer;
  outline: none;
  transition: border-color 0.15s;
}
.sel:focus { border-color: var(--accent); }
.sel:disabled { opacity: 0.4; cursor: not-allowed; }

/* SoC bar */
.soc-wrap {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 1.25rem;
}
.soc-track {
  flex: 1;
  background: rgba(255,255,255,0.06);
  border-radius: 99px;
  height: 8px;
  overflow: hidden;
}
.soc-fill {
  height: 100%;
  border-radius: 99px;
  background: linear-gradient(90deg, var(--accent-dark), var(--accent), #4ade80);
  transition: width 1s ease;
  box-shadow: 0 0 8px var(--accent-glow);
}
.soc-label {
  font-size: 0.78rem;
  font-weight: 700;
  color: var(--accent);
  white-space: nowrap;
  min-width: 38px;
  text-align: right;
}

/* Animated charging bar */
.charge-anim {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-top: 1rem;
}
.charge-anim__track {
  flex: 1;
  background: rgba(255,255,255,0.05);
  border-radius: 99px;
  height: 6px;
  overflow: hidden;
  border: 1px solid rgba(34,197,94,0.15);
}
.charge-anim__fill {
  height: 100%;
  border-radius: 99px;
  background: linear-gradient(90deg, transparent 0%, var(--accent-dark) 20%, var(--accent) 50%, var(--accent-dark) 80%, transparent 100%);
  background-size: 200% 100%;
  animation: chargeFlow 2s linear infinite;
  box-shadow: 0 0 6px var(--accent-glow);
}
@keyframes chargeFlow {
  0%   { background-position: 100% 0; }
  100% { background-position: -100% 0; }
}
.charge-anim__label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--accent);
  font-weight: 700;
  white-space: nowrap;
}

/* ── Section header ─────────────────────────────────────────────────── */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}
.section-title {
  font-size: 0.78rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-muted);
}

.loading-hint {
  color: var(--accent);
  animation: fadePulse 1.2s ease-in-out infinite;
  padding: 1rem 0;
  font-size: 0.875rem;
}
@keyframes fadePulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.4; } }

/* ── History table (desktop) ────────────────────────────────────────── */
.table-wrap {
  display: none;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  overflow: hidden;
  box-shadow: var(--shadow);
}
@media (min-width: 640px) {
  .table-wrap { display: block; }
}

.session-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.session-table thead { background: var(--bg-card-2); }
.session-table th {
  padding: 0.75rem 1rem;
  text-align: left;
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.session-table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border-soft);
  color: var(--text);
  vertical-align: middle;
}
.session-table tbody tr:last-child td { border-bottom: none; }
.session-table tbody tr { background: var(--bg-card); transition: background 0.12s; }
.session-table tbody tr:hover { background: var(--bg-hover); }
.session-table tbody tr.row--active { background: rgba(34,197,94,0.05); }

/* ── History cards (mobile) ─────────────────────────────────────────── */
.session-cards {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
@media (min-width: 640px) {
  .session-cards { display: none; }
}

.scard {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}
.scard--active { border-color: rgba(34,197,94,0.3); background: rgba(34,197,94,0.04); }

.scard__head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--border-soft);
  flex-wrap: wrap;
  gap: 0.5rem;
}
.scard__head-right { display: flex; align-items: center; gap: 0.5rem; }
.scard__rows { padding: 0.75rem 1rem; display: flex; flex-direction: column; gap: 0.5rem; }
.scard__row { display: flex; justify-content: space-between; align-items: baseline; gap: 1rem; }
.scard__key {
  font-size: 0.75rem;
  color: var(--text-muted);
  white-space: nowrap;
  flex-shrink: 0;
}
.scard__val { font-size: 0.875rem; color: var(--text); text-align: right; }

/* ── Cell helpers ───────────────────────────────────────────────────── */
.cell-vehicle { display: flex; flex-direction: column; gap: 1px; }
.cell-vehicle__name { font-weight: 600; }
.cell-vehicle__tag { font-size: 0.75rem; color: var(--text-muted); }

.mono { font-family: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', monospace; font-size: 0.875em; }
.muted { color: var(--text-muted); }
.energy { color: var(--accent); font-weight: 600; }
.cp-name { font-weight: 600; }
.connector-badge {
  display: inline-block;
  margin-left: 6px;
  font-size: 0.65rem;
  background: var(--bg-card-2);
  color: var(--text-muted);
  padding: 1px 6px;
  border-radius: 99px;
  border: 1px solid var(--border);
}

.status { display: inline-block; padding: 3px 10px; border-radius: 99px; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.05em; }
.status--active { background: var(--accent-dim); color: var(--accent); border: 1px solid rgba(34,197,94,0.2); }
.status--done { background: var(--bg-card-2); color: var(--text-muted); border: 1px solid var(--border); }


/* ── Pagination ─────────────────────────────────────────────────────── */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  margin-top: 1.25rem;
}
.pagination button {
  background: var(--bg-card);
  border: 1px solid var(--border);
  color: var(--text-muted);
  padding: 6px 16px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.875rem;
  transition: background 0.15s, color 0.15s, border-color 0.15s;
}
.pagination button:hover:not(:disabled) { background: var(--bg-hover); color: var(--text); border-color: rgba(255,255,255,0.15); }
.pagination button:disabled { opacity: 0.3; cursor: not-allowed; }
.pagination__info { font-size: 0.8rem; color: var(--text-muted); }

/* ── Vehicles section ───────────────────────────────────────────────── */
.empty-state {
  text-align: center;
  padding: 3rem 2rem;
  color: var(--text-muted);
  background: var(--bg-card);
  border-radius: var(--radius);
  border: 1px dashed var(--border);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1rem;
}
.empty-state__icon { font-size: 2.5rem; }
.empty-state__text { font-size: 0.95rem; }

.vehicles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1rem;
}

.vehicle-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: border-color 0.15s, transform 0.15s, box-shadow 0.15s;
}
.vehicle-card:hover {
  border-color: rgba(255,255,255,0.15);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}
.vehicle-card__img-wrap {
  width: 100%;
  height: 140px;
  background: var(--bg-card-2);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.vehicle-card__img { width: 100%; height: 100%; object-fit: cover; }
.vehicle-card__no-img { font-size: 3rem; }
.vehicle-card__body { padding: 0.875rem 1rem; flex: 1; }
.vehicle-card__name { font-weight: 700; font-size: 0.95rem; color: var(--text); margin-bottom: 0.35rem; }
.vehicle-card__rfid { font-size: 0.78rem; }
.vehicle-card__rfid--none { color: var(--text-dim); }
.badge-rfid {
  display: inline-block;
  background: var(--accent-dim);
  color: var(--accent);
  padding: 2px 8px;
  border-radius: 99px;
  font-size: 0.7rem;
  font-weight: 600;
  font-family: monospace;
  border: 1px solid rgba(34,197,94,0.2);
}
.vehicle-card__actions {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--border-soft);
}

/* ── Buttons ────────────────────────────────────────────────────────── */
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 0.875rem;
  font-weight: 500;
  padding: 8px 16px;
  transition: background 0.15s, color 0.15s, opacity 0.15s, transform 0.1s;
  white-space: nowrap;
}
.btn:active:not(:disabled) { transform: scale(0.97); }
.btn:disabled { opacity: 0.4; cursor: not-allowed; }
.btn--sm { padding: 5px 12px; font-size: 0.8rem; }
.btn--primary { background: var(--accent); color: #fff; font-weight: 700; }
.btn--primary:hover:not(:disabled) { background: #4ade80; }
.btn--ghost {
  background: var(--bg-card-2);
  color: var(--text-muted);
  border: 1px solid var(--border);
}
.btn--ghost:hover:not(:disabled) { background: var(--bg-hover); color: var(--text); border-color: rgba(255,255,255,0.15); }
.btn--danger {
  background: var(--danger-dim);
  color: var(--danger);
  border: 1px solid rgba(248,81,73,0.2);
}
.btn--danger:hover:not(:disabled) { background: rgba(248,81,73,0.2); }

/* ── Modal ──────────────────────────────────────────────────────────── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.7);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 500;
  padding: 1rem;
}
.modal {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  width: 100%;
  max-width: 460px;
  box-shadow: 0 24px 64px rgba(0,0,0,0.6);
  display: flex;
  flex-direction: column;
  max-height: 90vh;
  overflow: hidden;
}
.modal__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid var(--border);
}
.modal__title { font-size: 1rem; font-weight: 700; color: var(--text); }
.modal__close {
  background: none;
  border: none;
  font-size: 1rem;
  cursor: pointer;
  color: var(--text-muted);
  padding: 4px 6px;
  border-radius: 6px;
  transition: background 0.15s, color 0.15s;
}
.modal__close:hover { color: var(--text); background: var(--bg-hover); }
.modal__body {
  padding: 1.5rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
.modal__footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  padding: 1rem 1.5rem;
  border-top: 1px solid var(--border);
}

/* ── Form ───────────────────────────────────────────────────────────── */
.form-group { display: flex; flex-direction: column; gap: 0.4rem; }
.form-label { font-size: 0.8rem; font-weight: 600; color: var(--text-muted); }
.required { color: var(--danger); }
.form-input {
  background: var(--bg-card-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 8px 12px;
  font-size: 0.9rem;
  color: var(--text);
  outline: none;
  transition: border-color 0.15s;
  width: 100%;
}
.form-input:focus { border-color: var(--accent); }
.form-hint { font-size: 0.75rem; color: var(--text-muted); }

.image-upload { display: flex; flex-direction: column; gap: 0.75rem; }
.image-preview {
  width: 100%;
  max-height: 180px;
  object-fit: contain;
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-card-2);
}
.image-placeholder {
  height: 110px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-card-2);
  border: 1px dashed var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-dim);
  font-size: 0.875rem;
}
.image-upload__btns { display: flex; gap: 0.5rem; }
.sr-only { position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px; overflow: hidden; clip: rect(0,0,0,0); white-space: nowrap; border: 0; }
</style>
