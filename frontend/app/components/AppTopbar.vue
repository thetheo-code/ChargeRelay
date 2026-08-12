<template>
  <header class="topbar">
    <div class="topbar__inner">

      <div class="topbar__brand">
        <svg class="topbar__bolt" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
          <path fill="#16a34a" d="M13 2 L4 13 H10 L9 22 L20 11 H14 Z"/>
        </svg>
        <span class="topbar__title">ChargeRelay</span>
      </div>

      <!-- Desktop nav -->
      <nav class="topbar__nav topbar__nav--desktop" aria-label="Main">
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
        <select
          class="lang-select"
          :value="locale"
          :aria-label="locale === 'de' ? 'Sprache' : 'Language'"
          @change="setLocale(($event.target as HTMLSelectElement).value as typeof locale)"
        >
          <option v-for="l in LOCALES" :key="l.code" :value="l.code">{{ l.label }}</option>
        </select>

        <button
          class="topbar__refresh"
          :class="{ spinning: loading }"
          @click="$emit('refresh')"
          :aria-label="t('nav.refresh')"
        >↻</button>
      </div>

    </div>
  </header>

  <!-- Mobile bottom tabs -->
  <nav class="bottom-nav" aria-label="Main">
    <button
      class="bottom-nav__item"
      :class="{ 'bottom-nav__item--active': activeTab === 'overview' }"
      @click="$emit('update:activeTab', 'overview')"
    >
      <svg class="bottom-nav__icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M4 11.5 12 4l8 7.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1v-8.5Z"
              stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
      </svg>
      <span class="bottom-nav__label">{{ t('nav.overview') }}</span>
    </button>
    <button
      class="bottom-nav__item"
      :class="{ 'bottom-nav__item--active': activeTab === 'sessions' }"
      @click="$emit('toSessions')"
    >
      <svg class="bottom-nav__icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M13 2 4 13h6l-1 9 11-11h-6l1-9Z"
              stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
      </svg>
      <span class="bottom-nav__label">{{ t('nav.sessions') }}</span>
    </button>
    <button
      class="bottom-nav__item"
      :class="{ 'bottom-nav__item--active': activeTab === 'vehicles' }"
      @click="$emit('toVehicles')"
    >
      <svg class="bottom-nav__icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M5 16h14l-1.2-4.2A2 2 0 0 0 15.9 10H8.1a2 2 0 0 0-1.9 1.8L5 16Z"
              stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
        <path d="M7 16v2M17 16v2M3 16h18" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
        <circle cx="8" cy="19.5" r="1.2" fill="currentColor"/>
        <circle cx="16" cy="19.5" r="1.2" fill="currentColor"/>
      </svg>
      <span class="bottom-nav__label">{{ t('nav.vehicles') }}</span>
    </button>
    <button
      class="bottom-nav__item"
      :class="{ 'bottom-nav__item--active': activeTab === 'reports' }"
      @click="$emit('toReports')"
    >
      <svg class="bottom-nav__icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path d="M7 3h7l5 5v13a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z"
              stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/>
        <path d="M14 3v5h5M9 13h6M9 17h4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
      </svg>
      <span class="bottom-nav__label">{{ t('nav.reports') }}</span>
    </button>
  </nav>
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
  gap: 0.35rem;
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

/* Desktop nav stays in topbar; mobile uses bottom tabs */
.topbar__nav--desktop { display: none; }
@media (min-width: 768px) {
  .topbar__nav--desktop { display: flex; }
  .bottom-nav { display: none !important; }
}

.bottom-nav {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 100;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.15rem;
  padding: 0.35rem 0.4rem calc(0.35rem + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(14px);
  -webkit-backdrop-filter: blur(14px);
  border-top: 1px solid var(--border);
  box-shadow: 0 -8px 24px rgba(15, 23, 42, 0.06);
}

.bottom-nav__item {
  appearance: none;
  border: none;
  background: transparent;
  border-radius: 12px;
  padding: 0.4rem 0.25rem 0.35rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.15rem;
  color: var(--text-muted);
  cursor: pointer;
  transition: color 0.15s, background 0.15s, transform 0.12s;
  min-height: 52px;
  -webkit-tap-highlight-color: transparent;
}
.bottom-nav__item:active {
  transform: scale(0.96);
}
.bottom-nav__item--active {
  color: var(--accent);
  background: var(--accent-dim);
}
.bottom-nav__icon {
  width: 22px;
  height: 22px;
  flex-shrink: 0;
}
.bottom-nav__label {
  font-size: 0.62rem;
  font-weight: 600;
  letter-spacing: 0.01em;
  line-height: 1.1;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0 2px;
}
</style>
