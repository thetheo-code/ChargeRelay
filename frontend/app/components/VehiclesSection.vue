<template>
  <section class="vehicles-section">
    <div class="section-header">
      <h2 class="section-title">Fahrzeuge</h2>
      <button class="btn btn--primary" @click="$emit('openNew')">+ Neues Fahrzeug</button>
    </div>

    <div v-if="loading" class="loading-hint">Lade Fahrzeuge …</div>

    <!-- Leer-Zustand -->
    <div v-else-if="vehicles.length === 0" class="empty-state">
      <div class="empty-state__icon">🚗</div>
      <div class="empty-state__text">Noch keine Fahrzeuge registriert.</div>
      <button class="btn btn--primary" @click="$emit('openNew')">Jetzt anlegen</button>
    </div>

    <!-- Fahrzeug-Raster -->
    <div v-else class="vehicles-grid">
      <div v-for="v in vehicles" :key="v.id" class="vehicle-card">
        <div class="vehicle-card__img-wrap">
          <img v-if="v.image_data" :src="v.image_data" class="vehicle-card__img" alt="">
          <div v-else class="vehicle-card__no-img">🚗</div>
        </div>
        <div class="vehicle-card__body">
          <div class="vehicle-card__name">{{ v.name }}</div>
          <div v-if="v.id_tag" class="vehicle-card__rfid">
            <span class="badge-rfid">{{ v.id_tag }}</span>
          </div>
          <div v-else class="vehicle-card__rfid vehicle-card__rfid--none">Kein RFID-Tag</div>
        </div>
        <div class="vehicle-card__actions">
          <button class="btn btn--sm btn--ghost" @click="$emit('openEdit', v)">Bearbeiten</button>
          <button class="btn btn--sm btn--danger" @click="$emit('confirmDelete', v)">Löschen</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import type { Vehicle } from '~/types'

defineProps<{
  loading: boolean
  vehicles: Vehicle[]
}>()

defineEmits<{
  openNew: []
  openEdit: [vehicle: Vehicle]
  confirmDelete: [vehicle: Vehicle]
}>()
</script>
