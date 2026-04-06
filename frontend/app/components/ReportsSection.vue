<template>
  <section class="reports-section">
    <div class="section-header">
      <h2 class="section-title">{{ t('reports.title') }}</h2>
      <button class="btn btn--primary" @click="$emit('openNew')">{{ t('reports.new') }}</button>
    </div>

    <div v-if="loading" class="loading-hint">{{ t('reports.loading') }}</div>

    <!-- Empty state -->
    <div v-else-if="reports.length === 0" class="empty-state">
      <div class="empty-state__icon">—</div>
      <div class="empty-state__text">{{ t('reports.empty') }}</div>
      <button class="btn btn--primary" @click="$emit('openNew')">{{ t('reports.create') }}</button>
    </div>

    <!-- Report list -->
    <div v-else class="reports-list">
      <div v-for="r in reports" :key="r.id" class="report-card">

        <!-- Header: name + actions -->
        <div class="report-card__head">
          <span class="report-card__name">{{ r.name }}</span>
          <div class="report-card__actions">
            <button
              class="btn btn--sm btn--ghost btn--csv"
              :class="{ 'btn--csv-open': csvOpen[r.id] }"
              @click="toggleCsv(r)"
              :title="t('reports.csvDownload')"
            >
              <svg width="13" height="13" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M8 1v9M4 7l4 4 4-4M2 13h12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              CSV
            </button>
            <button class="btn btn--sm btn--ghost" @click="$emit('openEdit', r)">{{ t('reports.edit') }}</button>
            <button class="btn btn--sm btn--danger" @click="$emit('confirmDelete', r)">{{ t('reports.delete') }}</button>
          </div>
        </div>

        <!-- Vehicles -->
        <div class="report-card__section">
          <span class="report-card__label">{{ t('reports.vehicles') }}</span>
          <div class="report-card__tags">
            <span v-for="v in r.vehicles" :key="v.id" class="tag tag--vehicle">{{ v.name }}</span>
            <span v-if="r.vehicles.length === 0" class="tag tag--empty">{{ t('reports.none') }}</span>
          </div>
        </div>

        <!-- Deliveries -->
        <div class="report-card__section">
          <span class="report-card__label">{{ t('reports.deliveries') }}</span>
          <div class="report-card__deliveries">
            <div v-for="d in r.deliveries" :key="d.id" class="delivery-badge">
              <span class="delivery-badge__type">{{ d.type === 'mail' ? 'Mail' : 'OCPP' }}</span>
              <span v-if="d.type === 'mail'" class="delivery-badge__text">
                {{ d.email }} · {{ intervalLabel(d.interval) }}
              </span>
              <span v-else class="delivery-badge__text">
                {{ d.address }}:{{ d.port }}
              </span>
            </div>
            <span v-if="r.deliveries.length === 0" class="tag tag--empty">{{ t('reports.none') }}</span>
          </div>
        </div>

        <!-- CSV Download panel -->
        <Transition name="csv-panel">
          <div v-if="csvOpen[r.id] && csvState[r.id]" class="csv-panel">
            <div class="csv-panel__grid">

              <!-- Date range -->
              <div class="csv-field">
                <label class="csv-field__label">{{ t('reports.csvFrom') }}</label>
                <input type="date" class="csv-input" v-model="csvState[r.id].from" />
              </div>
              <div class="csv-field">
                <label class="csv-field__label">{{ t('reports.csvTo') }}</label>
                <input type="date" class="csv-input" v-model="csvState[r.id].to" />
              </div>

              <!-- Vehicle selection -->
              <div class="csv-field csv-field--vehicles">
                <label class="csv-field__label">{{ t('reports.csvVehicles') }}</label>
                <div class="csv-vehicles">
                  <label
                    v-for="v in r.vehicles"
                    :key="v.id"
                    class="csv-checkbox"
                  >
                    <input
                      type="checkbox"
                      :value="v.id"
                      v-model="csvState[r.id].selectedVehicles"
                    />
                    <span>{{ v.name }}</span>
                  </label>
                </div>
              </div>

            </div>

            <!-- Download button -->
            <div class="csv-panel__footer">
              <button
                class="btn btn--primary btn--sm"
                :disabled="csvState[r.id].downloading || csvState[r.id].selectedVehicles.length === 0"
                @click="downloadCsv(r)"
              >
                <svg v-if="!csvState[r.id].downloading" width="12" height="12" viewBox="0 0 16 16" fill="none">
                  <path d="M8 1v9M4 7l4 4 4-4M2 13h12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
                </svg>
                {{ csvState[r.id].downloading ? t('reports.csvDownloading') : t('reports.csvDownloadBtn') }}
              </button>
              <span v-if="csvState[r.id].selectedVehicles.length === 0" class="csv-warn">
                {{ t('reports.csvNoVehicle') }}
              </span>
            </div>
          </div>
        </Transition>

      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { Report } from '~/types'

defineProps<{
  loading: boolean
  reports: Report[]
}>()

defineEmits<{
  openNew: []
  openEdit: [report: Report]
  confirmDelete: [report: Report]
}>()

const { t, locale } = useLocale()

// ── CSV panel state ──────────────────────────────────────────────────────────

interface CsvState {
  from: string
  to: string
  selectedVehicles: number[]
  downloading: boolean
}

const csvOpen  = ref<Record<number, boolean>>({})
const csvState = ref<Record<number, CsvState>>({})

function todayStr(): string {
  return new Date().toISOString().slice(0, 10)
}
function firstOfMonthStr(): string {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
}

function toggleCsv(r: Report) {
  if (!csvOpen.value[r.id]) {
    // Initialise state the first time the panel is opened.
    if (!csvState.value[r.id]) {
      csvState.value[r.id] = {
        from: firstOfMonthStr(),
        to:   todayStr(),
        selectedVehicles: r.vehicles.map(v => v.id),
        downloading: false,
      }
    }
    csvOpen.value[r.id] = true
  } else {
    csvOpen.value[r.id] = false
  }
}

async function downloadCsv(r: Report) {
  const state = csvState.value[r.id]
  if (!state || state.selectedVehicles.length === 0) return

  state.downloading = true
  try {
    const params = new URLSearchParams({
      from_date:   state.from,
      to_date:     state.to,
      vehicle_ids: state.selectedVehicles.join(','),
      lang:        locale.value,
    })
    const url = `/api/reports/${r.id}/download?${params}`

    const res  = await fetch(url)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const blob = await res.blob()

    // Derive filename from Content-Disposition header or build a fallback.
    const cd       = res.headers.get('Content-Disposition') ?? ''
    const match    = cd.match(/filename="?([^"]+)"?/)
    const filename = match ? match[1] : `${r.name}_${state.from}_${state.to}.csv`

    const link  = document.createElement('a')
    link.href   = URL.createObjectURL(blob)
    link.download = filename
    link.click()
    URL.revokeObjectURL(link.href)
  } finally {
    state.downloading = false
  }
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function intervalLabel(v: string | null): string {
  if (!v) return '–'
  const key = `reports.${v}` as const
  return t(key) || v
}
</script>

<style scoped>
.reports-section {
  padding: 1.25rem;
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
}
@media (min-width: 640px) {
  .reports-section { padding: 1.75rem 2rem; }
}

.reports-list {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.report-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.125rem 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
  box-shadow: var(--shadow);
}

.report-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}
.report-card__name {
  font-weight: 700;
  font-size: 1rem;
  color: var(--text);
}
.report-card__actions {
  display: flex;
  gap: 0.5rem;
}

.report-card__section {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.report-card__label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: var(--text-muted);
  font-weight: 600;
}

.report-card__tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.375rem;
}

.tag {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 99px;
  font-size: 0.75rem;
  font-weight: 500;
}
.tag--vehicle {
  background: var(--accent-dim);
  color: var(--accent);
  border: 1px solid rgba(22,163,74,0.2);
}
.tag--empty {
  background: var(--bg-card-2);
  color: var(--text-dim);
  border: 1px solid var(--border);
}

.report-card__deliveries {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}
.delivery-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: var(--bg-card-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 4px 10px;
  width: fit-content;
}
.delivery-badge__type {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
}
.delivery-badge__text {
  font-size: 0.8rem;
  color: var(--text-muted);
  font-family: 'JetBrains Mono', 'Fira Code', monospace;
}

/* ── CSV button ──────────────────────────────────────────────────────────── */
.btn--csv {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  color: var(--text-muted);
}
.btn--csv-open {
  color: var(--accent);
  background: var(--accent-dim);
  border-color: rgba(22,163,74,0.25);
}

/* ── CSV panel ───────────────────────────────────────────────────────────── */
.csv-panel {
  border-top: 1px solid var(--border);
  padding-top: 0.875rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.csv-panel__grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem 1.25rem;
  align-items: flex-start;
}

.csv-field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  min-width: 130px;
}
.csv-field--vehicles {
  min-width: 200px;
}
.csv-field__label {
  font-size: 0.68rem;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: var(--text-muted);
  font-weight: 600;
}

.csv-input {
  background: var(--bg-card-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text);
  font-size: 0.82rem;
  padding: 0.3rem 0.5rem;
  outline: none;
  transition: border-color 0.15s;
  width: 100%;
}
.csv-input:focus {
  border-color: var(--accent);
}

.csv-vehicles {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.75rem;
}
.csv-checkbox {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.82rem;
  color: var(--text);
  cursor: pointer;
  user-select: none;
}
.csv-checkbox input[type="checkbox"] {
  accent-color: var(--accent);
  width: 14px;
  height: 14px;
  cursor: pointer;
}

.csv-panel__footer {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.csv-warn {
  font-size: 0.78rem;
  color: var(--text-dim);
}

/* ── Transition ──────────────────────────────────────────────────────────── */
.csv-panel-enter-active,
.csv-panel-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}
.csv-panel-enter-from,
.csv-panel-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
