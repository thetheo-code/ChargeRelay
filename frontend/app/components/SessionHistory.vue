<template>
  <section class="history-section">
    <div class="section-header">
      <h2 class="section-title">Letzte Ladevorgänge</h2>
    </div>

    <div v-if="loading" class="loading-hint">Lade Verlauf …</div>

    <template v-else>

      <!-- Desktop-Tabelle -->
      <div class="table-wrap">
        <table class="session-table">
          <thead>
            <tr>
              <th>Ladestation</th>
              <th>Fahrzeug / Ausweis</th>
              <th>Start</th>
              <th>Ende</th>
              <th>Energie</th>
              <th>Status</th>
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
                  <span class="cell-vehicle__tag mono">{{ s.id_tag }}</span>
                </div>
                <span v-else class="mono muted">{{ s.id_tag || '–' }}</span>
              </td>
              <td class="mono">{{ formatDate(s.start_time) }}</td>
              <td class="mono muted">{{ s.stop_time ? formatDate(s.stop_time) : '–' }}</td>
              <td class="mono energy">
                {{ s.energy_kwh != null
                  ? s.energy_kwh.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) + ' kWh'
                  : '–' }}
              </td>
              <td>
                <span v-if="!s.stop_time" class="status status--active">Aktiv</span>
                <span v-else class="status status--done">Fertig</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Mobile-Karten -->
      <div class="session-cards">
        <div v-for="s in sessions" :key="s.session_id" class="scard" :class="{ 'scard--active': !s.stop_time }">
          <div class="scard__head">
            <div>
              <span class="cp-name">{{ s.model || s.charge_point_id }}</span>
              <span class="connector-badge">C{{ s.connector_id }}</span>
            </div>
            <div class="scard__head-right">
              <span v-if="!s.stop_time" class="status status--active">Aktiv</span>
              <span v-else class="status status--done">Fertig</span>
            </div>
          </div>
          <div class="scard__rows">
            <div class="scard__row">
              <span class="scard__key">Fahrzeug</span>
              <span v-if="s.vehicle_name" class="scard__val">{{ s.vehicle_name }}</span>
              <span v-else class="scard__val mono muted">{{ s.id_tag || '–' }}</span>
            </div>
            <div class="scard__row">
              <span class="scard__key">Start</span>
              <span class="scard__val mono">{{ formatDate(s.start_time) }}</span>
            </div>
            <div class="scard__row" v-if="s.stop_time">
              <span class="scard__key">Ende</span>
              <span class="scard__val mono">{{ formatDate(s.stop_time) }}</span>
            </div>
            <div class="scard__row" v-if="s.energy_kwh != null">
              <span class="scard__key">Energie</span>
              <span class="scard__val energy mono">
                {{ s.energy_kwh.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }} kWh
              </span>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Seitennavigation -->
    <div class="pagination">
      <button :disabled="page <= 1" @click="$emit('changePage', page - 1)">‹ Zurück</button>
      <span class="pagination__info">Seite {{ page }} / {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="$emit('changePage', page + 1)">Weiter ›</button>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { Session } from '~/types'

defineProps<{
  loading: boolean
  sessions: Session[]
  page: number
  totalPages: number
}>()

defineEmits<{ changePage: [page: number] }>()

const { formatDate } = useFormatters()
</script>
