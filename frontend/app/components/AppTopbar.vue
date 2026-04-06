<template>
  <header class="topbar">
    <div class="topbar__inner">

      <div class="topbar__brand">
        <svg class="topbar__bolt" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path fill="#16a34a" d="M13 2 L4 13 H10 L9 22 L20 11 H14 Z"/>
        </svg>
        <span class="topbar__title">ChargeRelay</span>
      </div>

      <nav class="topbar__nav">
        <button
          class="tab-btn"
          :class="{ 'tab-btn--active': activeTab === 'overview' }"
          @click="$emit('update:activeTab', 'overview')"
        >{{ t('nav.overview') }}</button>
        <button
          class="tab-btn"
          :class="{ 'tab-btn--active': activeTab === 'sessions' }"
          @click="$emit('toSessions')"
        >{{ t('nav.sessions') }}</button>
        <button
          class="tab-btn"
          :class="{ 'tab-btn--active': activeTab === 'vehicles' }"
          @click="$emit('toVehicles')"
        >{{ t('nav.vehicles') }}</button>
        <button
          class="tab-btn"
          :class="{ 'tab-btn--active': activeTab === 'reports' }"
          @click="$emit('toReports')"
        >{{ t('nav.reports') }}</button>
      </nav>

      <div class="topbar__right">
        <!-- Language dropdown -->
        <select
          class="lang-select"
          :value="locale"
          :aria-label="locale === 'de' ? 'Sprache' : 'Language'"
          @change="setLocale(($event.target as HTMLSelectElement).value as typeof locale)"
        >
          <option v-for="l in LOCALES" :key="l.code" :value="l.code">{{ l.label }}</option>
        </select>

        <!-- Refresh -->
        <button
          class="topbar__refresh"
          :class="{ spinning: loading }"
          @click="$emit('refresh')"
          :aria-label="t('nav.refresh')"
        >↻</button>
      </div>

    </div>
  </header>
</template>

<script setup lang="ts">
import { LOCALES } from '~/composables/useLocale'

const { t, locale, setLocale } = useLocale()

defineProps<{
  activeTab: 'overview' | 'sessions' | 'vehicles' | 'reports'
  loading: boolean
}>()

defineEmits<{
  'update:activeTab': ['overview' | 'sessions' | 'vehicles' | 'reports']
  refresh: []
  toSessions: []
  toVehicles: []
  toReports: []
}>()
</script>

<style scoped>
.topbar__right {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.lang-select {
  appearance: none;
  -webkit-appearance: none;
  background: var(--bg-card) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' stroke='%23888' stroke-width='1.5' fill='none' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") no-repeat right 7px center;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  color: var(--text-muted);
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 600;
  letter-spacing: 0.04em;
  padding: 4px 24px 4px 7px;
  min-width: 72px;
  transition: border-color 0.15s, color 0.15s, background-color 0.15s;
  line-height: 1.4;
}
.lang-select:hover {
  border-color: var(--accent);
  color: var(--text);
}
.lang-select:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-dim);
}
</style>
