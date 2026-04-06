<template>
  <section class="history-section">
    <div class="section-header">
      <h2 class="section-title">{{ t('sessions.title') }}</h2>
      <button
        class="btn btn--sm btn--ghost btn--csv"
        :class="{ 'btn--csv-open': csvOpen }"
        @click="csvOpen = !csvOpen"
      >
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none">
          <path d="M8 1v9M4 7l4 4 4-4M2 13h12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        CSV
      </button>
    </div>

    <!-- CSV export panel -->
    <Transition name="csv-panel">
      <div v-if="csvOpen" class="csv-panel">
        <div class="csv-panel__grid">
          <div class="csv-field">
            <label class="csv-field__label">{{ t('sessions.csvFrom') }}</label>
            <input type="date" class="csv-input" v-model="csvFrom" />
          </div>
          <div class="csv-field">
            <label class="csv-field__label">{{ t('sessions.csvTo') }}</label>
            <input type="date" class="csv-input" v-model="csvTo" />
          </div>
          <div v-if="vehicles.length > 0" class="csv-field csv-field--vehicles">
            <label class="csv-field__label">{{ t('sessions.csvVehicles') }}</label>
            <div class="csv-vehicles">
              <label class="csv-checkbox csv-checkbox--all">
                <input type="checkbox" v-model="csvAllVehicles" @change="onToggleAll" />
                <span>{{ t('sessions.csvAllVehicles') }}</span>
              </label>
              <label v-for="v in vehicles" :key="v.id" class="csv-checkbox">
                <input type="checkbox" :value="v.id" v-model="csvSelectedVehicles" />
                <span>{{ v.name }}</span>
              </label>
            </div>
          </div>
        </div>
        <div class="csv-panel__footer">
          <button
            class="btn btn--primary btn--sm"
            :disabled="csvDownloading"
            @click="downloadCsv"
          >
            <svg v-if="!csvDownloading" width="12" height="12" viewBox="0 0 16 16" fill="none">
              <path d="M8 1v9M4 7l4 4 4-4M2 13h12" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            {{ csvDownloading ? t('sessions.csvDownloading') : t('sessions.csvDownloadBtn') }}
          </button>
        </div>
      </div>
    </Transition>

    <div v-if="loading" class="loading-hint">{{ t('sessions.loading') }}</div>

    <template v-else>

      <!-- Desktop table -->
      <div class="table-wrap">
        <table class="session-table">
          <thead>
            <tr>
              <th>{{ t('sessions.chargePoint') }}</th>
              <th>{{ t('sessions.vehicle') }}</th>
              <th>{{ t('sessions.start') }}</th>
              <th>{{ t('sessions.end') }}</th>
              <th>{{ t('sessions.energy') }}</th>
              <th>{{ t('sessions.status') }}</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in sessions" :key="s.session_id" :class="{ 'row--active': !s.stop_time }">
              <td>
                <span class="cp-name">{{ s.model || s.charge_point_id }}</span>
                <span class="connector-badge">C{{ s.connector_id }}</span>
              </td>
              <td>
                <div v-if="s.vehicle_name" class="cell-vehicle">
                  <span class="cell-vehicle__name">{{ s.vehicle_name }}</span>
                  <span class="cell-vehicle__tag mono">{{ s.authorized_id_tag || s.id_tag }}</span>
                </div>
                <span v-else class="mono muted">{{ s.authorized_id_tag || s.id_tag || '–' }}</span>
              </td>
              <td class="mono">{{ formatDate(s.start_time) }}</td>
              <td class="mono muted">{{ s.stop_time ? formatDate(s.stop_time) : '–' }}</td>
              <td class="mono energy">
                {{ s.energy_kwh != null
                  ? s.energy_kwh.toLocaleString(numLocale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' kWh'
                  : '–' }}
              </td>
              <td>
                <span v-if="!s.stop_time" class="status status--active">{{ t('sessions.active') }}</span>
                <span v-else class="status status--done">{{ t('sessions.done') }}</span>
              </td>
              <td class="td-edit">
                <button class="edit-btn" @click="$emit('editSession', s)" :title="t('sessions.edit')">
                  <svg width="13" height="13" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M11.06 1.06a1.5 1.5 0 0 1 2.12 0l1.76 1.76a1.5 1.5 0 0 1 0 2.12L5.5 14.38l-4.38.62.62-4.38L11.06 1.06Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
                  </svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Mobile cards -->
      <div class="session-cards">
        <div v-for="s in sessions" :key="s.session_id" class="scard" :class="{ 'scard--active': !s.stop_time }">
          <div class="scard__head">
            <div>
              <span class="cp-name">{{ s.model || s.charge_point_id }}</span>
              <span class="connector-badge">C{{ s.connector_id }}</span>
            </div>
            <div class="scard__head-right">
              <span v-if="!s.stop_time" class="status status--active">{{ t('sessions.active') }}</span>
              <span v-else class="status status--done">{{ t('sessions.done') }}</span>
              <button class="edit-btn" @click="$emit('editSession', s)" :title="t('sessions.edit')">
                <svg width="13" height="13" viewBox="0 0 16 16" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <path d="M11.06 1.06a1.5 1.5 0 0 1 2.12 0l1.76 1.76a1.5 1.5 0 0 1 0 2.12L5.5 14.38l-4.38.62.62-4.38L11.06 1.06Z" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round"/>
                </svg>
              </button>
            </div>
          </div>
          <div class="scard__rows">
            <div class="scard__row">
              <span class="scard__key">{{ t('sessions.vehicle') }}</span>
              <span v-if="s.vehicle_name" class="scard__val">{{ s.vehicle_name }}</span>
              <span v-else class="scard__val mono muted">{{ s.authorized_id_tag || s.id_tag || '–' }}</span>
            </div>
            <div class="scard__row">
              <span class="scard__key">{{ t('sessions.start') }}</span>
              <span class="scard__val mono">{{ formatDate(s.start_time) }}</span>
            </div>
            <div class="scard__row" v-if="s.stop_time">
              <span class="scard__key">{{ t('sessions.end') }}</span>
              <span class="scard__val mono">{{ formatDate(s.stop_time) }}</span>
            </div>
            <div class="scard__row" v-if="s.energy_kwh != null">
              <span class="scard__key">{{ t('sessions.energy') }}</span>
              <span class="scard__val energy mono">
                {{ s.energy_kwh.toLocaleString(numLocale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }} kWh
              </span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Pagination -->
    <div class="pagination">
      <button :disabled="page <= 1" @click="$emit('changePage', page - 1)">{{ t('sessions.prev') }}</button>
      <span class="pagination__info">{{ t('sessions.page', { page, total: totalPages }) }}</span>
      <button :disabled="page >= totalPages" @click="$emit('changePage', page + 1)">{{ t('sessions.next') }}</button>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { Session, Vehicle } from '~/types'

const props = defineProps<{
  loading: boolean
  sessions: Session[]
  page: number
  totalPages: number
  vehicles: Vehicle[]
}>()

defineEmits<{
  changePage: [page: number]
  editSession: [session: Session]
}>()

const { t, numLocale, locale } = useLocale()
const { formatDate } = useFormatters()

function todayStr()        { return new Date().toISOString().slice(0, 10) }
function firstOfMonthStr() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-01`
}

const csvOpen             = ref(false)
const csvFrom             = ref(firstOfMonthStr())
const csvTo               = ref(todayStr())
const csvAllVehicles      = ref(true)
const csvSelectedVehicles = ref<number[]>([])
const csvDownloading      = ref(false)

watch(csvOpen, (open) => {
  if (open) csvSelectedVehicles.value = props.vehicles.map(v => v.id)
})

watch(csvSelectedVehicles, (sel) => {
  csvAllVehicles.value = sel.length === props.vehicles.length
})

function onToggleAll() {
  csvSelectedVehicles.value = csvAllVehicles.value ? props.vehicles.map(v => v.id) : []
}

async function downloadCsv() {
  csvDownloading.value = true
  try {
    const params = new URLSearchParams({ from_date: csvFrom.value, to_date: csvTo.value, lang: locale.value })
    if (!csvAllVehicles.value && csvSelectedVehicles.value.length > 0) {
      params.set('vehicle_ids', csvSelectedVehicles.value.join(','))
    }
    const res  = await fetch(`/api/sessions/download?${params}`)
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const blob = await res.blob()
    const cd   = res.headers.get('Content-Disposition') ?? ''
    const match = cd.match(/filename="?([^"]+)"?/)
    const filename = match ? match[1] : `ladevorgaenge_${csvFrom.value}_${csvTo.value}.csv`
    const link = document.createElement('a')
    link.href  = URL.createObjectURL(blob)
    link.download = filename
    link.click()
    URL.revokeObjectURL(link.href)
  } finally {
    csvDownloading.value = false
  }
}
</script>

<style scoped>
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
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.25rem;
  margin-bottom: 1rem;
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
.csv-field--vehicles { min-width: 220px; }
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
}
.csv-input:focus { border-color: var(--accent); }
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
.csv-checkbox--all { font-weight: 600; }
.csv-checkbox input[type="checkbox"] {
  accent-color: var(--accent);
  width: 14px;
  height: 14px;
  cursor: pointer;
}
.csv-panel__footer { display: flex; align-items: center; gap: 0.75rem; }

.csv-panel-enter-active,
.csv-panel-leave-active { transition: opacity 0.18s ease, transform 0.18s ease; }
.csv-panel-enter-from,
.csv-panel-leave-to { opacity: 0; transform: translateY(-4px); }

/* ── Edit button ─────────────────────────────────────────────────────────── */
.td-edit {
  width: 36px;
  text-align: right;
  padding-right: 0.75rem !important;
}

.edit-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--text-dim);
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  flex-shrink: 0;
}
.edit-btn:hover {
  background: var(--bg-hover);
  color: var(--text-muted);
}
</style>
