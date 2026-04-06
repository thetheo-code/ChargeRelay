<template>
  <section class="charts-section">

    <div v-if="loading" class="loading-hint">{{ t('overview.loading') }}</div>

    <div v-else-if="error || !stats" class="stats-error">
      {{ t('overview.error') }}
      <span class="stats-error__hint">{{ t('overview.errorHint') }}</span>
    </div>

    <template v-else>

      <!-- Stat tiles -->
      <div class="stat-row">
        <div class="stat-tile">
          <div class="stat-tile__label">{{ t('overview.sessions') }}</div>
          <div class="stat-tile__value">{{ stats.total_sessions }}</div>
          <div class="stat-tile__sub">{{ t('overview.last30Days') }}</div>
        </div>
        <div class="stat-tile">
          <div class="stat-tile__label">{{ t('overview.energy') }}</div>
          <div class="stat-tile__value">
            {{ fmtKwh(stats.total_kwh) }}<span class="stat-tile__unit">kWh</span>
          </div>
          <div class="stat-tile__sub">{{ t('overview.last30Days') }}</div>
        </div>
        <div class="stat-tile" v-if="stats.total_sessions > 0">
          <div class="stat-tile__label">{{ t('overview.avgPerCharge') }}</div>
          <div class="stat-tile__value">
            {{ fmtKwh(stats.total_kwh / stats.total_sessions) }}<span class="stat-tile__unit">kWh</span>
          </div>
          <div class="stat-tile__sub">{{ t('overview.last30Days') }}</div>
        </div>
      </div>

      <!-- Chart 1: Energy per day -->
      <div class="chart-card">
        <div class="chart-card__header">
          <h3 class="chart-card__title">{{ t('overview.energyPerDay') }}</h3>
          <span class="chart-card__sub">{{ t('overview.perDaySub', { days: stats.days }) }}</span>
        </div>

        <div class="bar-chart-wrap">
          <!-- Y-Achse -->
          <div class="y-axis">
            <span v-for="n in [4,3,2,1,0]" :key="n" class="y-label">
              {{ n === 0 ? '0' : fmtKwh(maxDay * n / 4) }}
            </span>
          </div>

          <!-- Hauptbereich -->
          <div class="bar-chart-inner">
            <!-- Grid-Linien -->
            <div class="grid-lines">
              <div v-for="n in 4" :key="n" class="grid-line" :style="{ bottom: (n * 25) + '%' }"></div>
            </div>

            <!-- Balken -->
            <div class="bars">
              <div
                v-for="d in stats.energy_per_day"
                :key="d.date"
                class="bar-col"
                :class="{ 'bar-col--today': isToday(d.date), 'bar-col--empty': d.kwh === 0 }"
              >
                <span v-if="d.kwh > 0" class="bar-tip">{{ fmtKwh(d.kwh) }}</span>
                <div class="bar" :style="{ height: barPct(d.kwh) + '%' }"></div>
                <span class="bar-day">{{ dayLabel(d.date) }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- X-Achsen-Kontext: Monat(e) -->
        <div class="x-axis-hint">
          {{ xAxisHint }}
        </div>
      </div>

      <!-- Chart 2: Energy per vehicle -->
      <div class="chart-card" v-if="stats.energy_per_vehicle.length > 0">
        <div class="chart-card__header">
          <h3 class="chart-card__title">{{ t('overview.energyPerVehicle') }}</h3>
          <span class="chart-card__sub">{{ t('overview.perVehicleSub') }}</span>
        </div>

        <div class="hbar-chart">
          <div v-for="v in stats.energy_per_vehicle" :key="v.name" class="hbar-row">
            <div class="hbar-name">{{ v.name }}</div>
            <div class="hbar-track">
              <div class="hbar-fill" :style="{ width: hbarPct(v.kwh) + '%' }"></div>
            </div>
            <div class="hbar-val">{{ fmtKwh(v.kwh) }}</div>
          </div>
        </div>
      </div>

    </template>
  </section>
</template>

<script setup lang="ts">
import type { Stats } from '~/types'

const { t, numLocale } = useLocale()

const props = defineProps<{
  loading: boolean
  stats: Stats | null
  error?: boolean
}>()

const maxDay = computed(() =>
  Math.max(...(props.stats?.energy_per_day.map(d => d.kwh) ?? [0]), 0.1)
)

const maxVehicle = computed(() =>
  Math.max(...(props.stats?.energy_per_vehicle.map(v => v.kwh) ?? [0]), 0.1)
)

function barPct(kwh: number): number {
  return (kwh / maxDay.value) * 96  // max 96% Höhe, damit die Spitze etwas Luft hat
}

function hbarPct(kwh: number): number {
  return (kwh / maxVehicle.value) * 100
}

function isToday(dateStr: string): boolean {
  return dateStr === new Date().toISOString().slice(0, 10)
}

function dayLabel(dateStr: string): string {
  // Führe '+T12:00' um Timezone-Probleme beim Parsen zu vermeiden
  const d = new Date(dateStr + 'T12:00:00')
  return String(d.getDate())
}

const xAxisHint = computed(() => {
  const days = props.stats?.energy_per_day
  if (!days?.length) return ''
  const locale = numLocale.value
  const first = new Date(days[0].date + 'T12:00:00')
  const last  = new Date(days[days.length - 1].date + 'T12:00:00')
  const fmt = (d: Date) => d.toLocaleDateString(locale, { month: 'long', year: 'numeric' })
  return first.getMonth() === last.getMonth()
    ? fmt(last)
    : `${first.toLocaleDateString(locale, { month: 'short' })} – ${fmt(last)}`
})

function fmtKwh(v: number): string {
  return v.toLocaleString(numLocale.value, { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}
</script>

<style scoped>
.charts-section {
  padding: 0 1.25rem 1.25rem;
  max-width: 1100px;
  margin: 0 auto;
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}
@media (min-width: 640px) {
  .charts-section { padding: 0 2rem 1.75rem; }
}

/* ── Fehler-Zustand ─────────────────────────────────────────────────── */
.stats-error {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 2rem 1.5rem;
  color: var(--text-muted);
  font-size: 0.875rem;
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.stats-error__hint {
  font-size: 0.775rem;
  color: var(--text-dim);
}

/* ── Stat-Kacheln ───────────────────────────────────────────────────── */
.stat-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 0.875rem;
}
.stat-tile {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem 1.5rem;
  box-shadow: var(--shadow);
}
.stat-tile__label {
  font-size: 0.7rem;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: var(--text-muted);
  font-weight: 600;
  margin-bottom: 0.4rem;
}
.stat-tile__value {
  font-size: 2.2rem;
  font-weight: 600;
  color: var(--text);
  line-height: 1;
  font-variant-numeric: tabular-nums;
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.stat-tile__unit {
  font-size: 1rem;
  font-weight: 400;
  color: var(--text-muted);
}
.stat-tile__sub {
  font-size: 0.72rem;
  color: var(--text-dim);
  margin-top: 0.35rem;
}

/* ── Chart-Karte ────────────────────────────────────────────────────── */
.chart-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.5rem;
  box-shadow: var(--shadow);
}
.chart-card__header {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}
.chart-card__title {
  font-size: 0.875rem;
  font-weight: 700;
  color: var(--text);
}
.chart-card__sub {
  font-size: 0.75rem;
  color: var(--text-muted);
}

/* ── Bar Chart ──────────────────────────────────────────────────────── */
.bar-chart-wrap {
  display: flex;
  gap: 0.5rem;
  align-items: stretch;
}

.y-axis {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding-bottom: 1.75rem; /* Platz für x-Labels */
  min-width: 36px;
  text-align: right;
}
.y-label {
  font-size: 0.65rem;
  color: var(--text-dim);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.bar-chart-inner {
  flex: 1;
  position: relative;
}

.grid-lines {
  position: absolute;
  inset: 0;
  bottom: 1.75rem; /* Platz für x-Labels */
  pointer-events: none;
}
.grid-line {
  position: absolute;
  left: 0;
  right: 0;
  height: 1px;
  background: var(--border-soft);
}

.bars {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  height: 240px;
  padding-bottom: 1.75rem; /* Platz für Labels */
  position: relative;
}

.bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  height: 100%;
  gap: 3px;
  position: relative;
  cursor: default;
}

.bar-tip {
  font-size: 0.58rem;
  color: var(--accent);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
  opacity: 0;
  transition: opacity 0.15s;
  position: absolute;
  bottom: calc(1.75rem + 100%);
  pointer-events: none;
}
.bar-col:hover .bar-tip {
  opacity: 1;
}

.bar {
  width: 100%;
  min-height: 0;
  background: linear-gradient(to top, var(--accent-dark), var(--accent));
  border-radius: 3px 3px 0 0;
  transition: height 0.7s cubic-bezier(0.16, 1, 0.3, 1);
  flex-shrink: 0;
}
.bar-col--today .bar {
  background: linear-gradient(to top, var(--accent), #4ade80);
  box-shadow: 0 0 10px var(--accent-glow);
}
.bar-col--empty .bar {
  background: var(--border);
  min-height: 2px;
}

.bar-day {
  position: absolute;
  bottom: 0;
  font-size: 0.65rem;
  color: var(--text-dim);
  font-variant-numeric: tabular-nums;
  height: 1.6rem;
  display: flex;
  align-items: center;
}
.bar-col--today .bar-day {
  color: var(--accent);
  font-weight: 700;
}

.x-axis-hint {
  text-align: right;
  font-size: 0.7rem;
  color: var(--text-dim);
  margin-top: 0.5rem;
}

/* ── Horizontal Bar Chart ───────────────────────────────────────────── */
.hbar-chart {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}
.hbar-row {
  display: grid;
  grid-template-columns: minmax(80px, 180px) 1fr 64px;
  align-items: center;
  gap: 0.875rem;
}
.hbar-name {
  font-size: 0.825rem;
  color: var(--text);
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.hbar-track {
  height: 10px;
  background: var(--bg-card-2);
  border-radius: 99px;
  overflow: hidden;
  border: 1px solid var(--border-soft);
}
.hbar-fill {
  height: 100%;
  background: linear-gradient(to right, var(--accent-dark), var(--accent));
  border-radius: 99px;
  transition: width 0.8s cubic-bezier(0.16, 1, 0.3, 1);
  min-width: 4px;
}
.hbar-val {
  font-size: 0.775rem;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
  text-align: right;
  font-weight: 500;
}
</style>
