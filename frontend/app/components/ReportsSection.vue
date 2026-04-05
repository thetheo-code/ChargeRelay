<template>
  <section class="reports-section">
    <div class="section-header">
      <h2 class="section-title">Reports</h2>
      <button class="btn btn--primary" @click="$emit('openNew')">+ Neuer Report</button>
    </div>

    <div v-if="loading" class="loading-hint">Lade Reports …</div>

    <!-- Leer-Zustand -->
    <div v-else-if="reports.length === 0" class="empty-state">
      <div class="empty-state__icon">—</div>
      <div class="empty-state__text">Noch keine Reports konfiguriert.</div>
      <button class="btn btn--primary" @click="$emit('openNew')">Jetzt anlegen</button>
    </div>

    <!-- Report-Liste -->
    <div v-else class="reports-list">
      <div v-for="r in reports" :key="r.id" class="report-card">

        <!-- Kopf: Name + Aktionen -->
        <div class="report-card__head">
          <span class="report-card__name">{{ r.name }}</span>
          <div class="report-card__actions">
            <button class="btn btn--sm btn--ghost" @click="$emit('openEdit', r)">Bearbeiten</button>
            <button class="btn btn--sm btn--danger" @click="$emit('confirmDelete', r)">Löschen</button>
          </div>
        </div>

        <!-- Fahrzeuge -->
        <div class="report-card__section">
          <span class="report-card__label">Fahrzeuge</span>
          <div class="report-card__tags">
            <span v-for="v in r.vehicles" :key="v.id" class="tag tag--vehicle">{{ v.name }}</span>
            <span v-if="r.vehicles.length === 0" class="tag tag--empty">Keine</span>
          </div>
        </div>

        <!-- Lieferwege -->
        <div class="report-card__section">
          <span class="report-card__label">Lieferwege</span>
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
            <span v-if="r.deliveries.length === 0" class="tag tag--empty">Keine</span>
          </div>
        </div>

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

const INTERVAL_LABELS: Record<string, string> = {
  daily:   'täglich',
  weekly:  'wöchentlich',
  monthly: 'monatlich',
  yearly:  'jährlich',
}

function intervalLabel(v: string | null): string {
  return v ? (INTERVAL_LABELS[v] ?? v) : '–'
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
</style>
