<template>
  <section class="history-section">
    <div class="section-header">
      <h2 class="section-title">{{ t('sessions.title') }}</h2>
    </div>

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
import type { Session } from '~/types'

defineProps<{
  loading: boolean
  sessions: Session[]
  page: number
  totalPages: number
}>()

defineEmits<{
  changePage: [page: number]
  editSession: [session: Session]
}>()

const { t, numLocale } = useLocale()
const { formatDate } = useFormatters()
</script>

<style scoped>
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
