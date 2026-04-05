<template>
  <header class="topbar">
    <div class="topbar__inner">
      <div class="topbar__brand">
        <span class="topbar__title">ChargeRelay</span>
      </div>
      <nav class="topbar__nav">
        <button
          class="tab-btn"
          :class="{ 'tab-btn--active': activeTab === 'overview' }"
          @click="$emit('update:activeTab', 'overview')"
        >Übersicht</button>
        <button
          class="tab-btn"
          :class="{ 'tab-btn--active': activeTab === 'sessions' }"
          @click="$emit('toSessions')"
        >Ladevorgänge</button>
        <button
          class="tab-btn"
          :class="{ 'tab-btn--active': activeTab === 'vehicles' }"
          @click="$emit('toVehicles')"
        >Fahrzeuge</button>
        <button
          class="tab-btn"
          :class="{ 'tab-btn--active': activeTab === 'reports' }"
          @click="$emit('toReports')"
        >Reports</button>
      </nav>
      <button
        class="topbar__refresh"
        :class="{ spinning: loading }"
        @click="$emit('refresh')"
        aria-label="Aktualisieren"
      >↻</button>
    </div>
  </header>
</template>

<script setup lang="ts">
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
