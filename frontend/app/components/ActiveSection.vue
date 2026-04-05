<template>
  <section class="active-section">

    <!-- Lädt -->
    <div v-if="loading" class="state-card">
      <div class="spinner"></div>
      <span class="state-card__text">Verbinde…</span>
    </div>

    <!-- Kein aktiver Ladevorgang -->
    <div v-else-if="sessions.length === 0" class="state-card state-card--idle">
      <div class="state-card__text">Kein aktiver Ladevorgang</div>
      <div class="state-card__sub">Gerät wartet auf Verbindung</div>
    </div>

    <!-- Aktive Ladevorgänge -->
    <ChargeCard
      v-else
      v-for="s in sessions"
      :key="s.session_id"
      :session="s"
      :vehicles="vehicles"
      :vehicleSelection="sessionVehicleSelection[s.session_id] ?? null"
      @update:vehicleSelection="$emit('updateSelection', { sessionId: s.session_id, vehicleId: $event })"
      @assign="$emit('assignVehicle', s.session_id)"
    />
  </section>
</template>

<script setup lang="ts">
import type { ActiveSession, Vehicle } from '~/types'

defineProps<{
  loading: boolean
  sessions: ActiveSession[]
  vehicles: Vehicle[]
  sessionVehicleSelection: Record<number, number | null>
}>()

defineEmits<{
  updateSelection: [{ sessionId: number; vehicleId: number | null }]
  assignVehicle: [sessionId: number]
}>()
</script>
