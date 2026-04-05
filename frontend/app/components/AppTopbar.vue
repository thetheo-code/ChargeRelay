<template>
  <header class="topbar">
    <div class="topbar__inner">
      <div class="topbar__brand">
        <span class="topbar__title">Wallbox</span>
      </div>
      <nav class="topbar__nav">
        <button
          class="tab-btn"
          :class="{ 'tab-btn--active': activeTab === 'overview' }"
          @click="$emit('update:activeTab', 'overview')"
        >Übersicht</button>
        <button
          class="tab-btn"
          :class="{ 'tab-btn--active': activeTab === 'vehicles' }"
          @click="$emit('toVehicles')"
        >Fahrzeuge</button>
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
  activeTab: 'overview' | 'vehicles'
  loading: boolean
}>()

defineEmits<{
  'update:activeTab': ['overview' | 'vehicles']
  refresh: []
  toVehicles: []
}>()
</script>
