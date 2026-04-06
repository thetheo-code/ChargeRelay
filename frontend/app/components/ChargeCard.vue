<template>
  <div class="charge-card">

    <!-- Header: live indicator, charge point, connector -->
    <div class="charge-card__head">
      <div class="live-dot"></div>
      <span class="charge-card__live-label">{{ t('active.live') }}</span>
      <span class="charge-card__sep">·</span>
      <span class="charge-card__cp">{{ session.model || session.charge_point_id }}</span>
      <span class="badge">C{{ session.connector_id }}</span>
    </div>

    <!-- Inhalt: Messwerte + Fahrzeug-Hero oder Zuweisung -->
    <div class="charge-card__body" :class="{ 'charge-card__body--with-vehicle': session.vehicle_id }">

      <!-- Metrics grid -->
      <div class="metrics-grid">
        <div class="metric">
          <div class="metric__label">{{ t('active.runtime') }}</div>
          <div class="metric__value">{{ formatDuration(session.duration_seconds) }}</div>
        </div>
        <div class="metric" v-if="session.session_energy_kwh != null && session.session_energy_kwh > 0">
          <div class="metric__label">{{ t('active.energy') }}</div>
          <div class="metric__value metric__value--accent">
            {{ session.session_energy_kwh.toLocaleString(numLocale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}<span class="metric__unit">kWh</span>
          </div>
        </div>
        <div class="metric" v-if="getMeter(session, 'Power.Active.Import')">
          <div class="metric__label">{{ t('active.power') }}</div>
          <div class="metric__value">
            {{ formatPower(getMeter(session, 'Power.Active.Import')) }}<span class="metric__unit">kW</span>
          </div>
        </div>
        <div class="metric" v-if="getMeter(session, 'SoC')">
          <div class="metric__label">{{ t('active.soc') }}</div>
          <div class="metric__value metric__value--accent">
            {{ Number(getMeter(session, 'SoC')?.value).toFixed(0) }}<span class="metric__unit">%</span>
          </div>
        </div>
        <div class="metric" v-if="getMeter(session, 'Current.Import')">
          <div class="metric__label">{{ t('active.current') }}</div>
          <div class="metric__value">
            {{ Number(getMeter(session, 'Current.Import')?.value).toLocaleString(numLocale, { minimumFractionDigits: 1, maximumFractionDigits: 1 }) }}<span class="metric__unit">A</span>
          </div>
        </div>
        <div class="metric" v-if="getMeter(session, 'Voltage')">
          <div class="metric__label">{{ t('active.voltage') }}</div>
          <div class="metric__value">
            {{ Number(getMeter(session, 'Voltage')?.value).toFixed(0) }}<span class="metric__unit">V</span>
          </div>
        </div>
        <div class="metric metric--date">
          <div class="metric__label">{{ t('active.started') }}</div>
          <div class="metric__value">{{ formatTime(session.start_time) }}</div>
        </div>
      </div>

      <!-- Fahrzeug-Bild & Name (wenn zugewiesen) -->
      <div v-if="session.vehicle_id" class="vehicle-hero">
        <div class="vehicle-hero__img-wrap">
          <img
            v-if="getVehicle(session.vehicle_id)?.image_data"
            :src="getVehicle(session.vehicle_id)?.image_data ?? ''"
            class="vehicle-hero__img"
            alt=""
          >
          <div v-else class="vehicle-hero__placeholder">–</div>
        </div>
        <div class="vehicle-hero__name">
          {{ session.vehicle_name }}
          <span
            v-if="getVehicle(session.vehicle_id)?.id_tag &&
              (getVehicle(session.vehicle_id)?.id_tag === session.id_tag ||
               getVehicle(session.vehicle_id)?.id_tag === session.authorized_id_tag)"
            class="rfid-check"
            :title="t('active.autoRfid')"
          >✔</span>
        </div>
      </div>

      <!-- Assign vehicle (when not yet assigned) -->
      <div v-if="!session.vehicle_id" class="assign-block">
        <div class="assign-block__label">{{ t('active.assignVehicle') }}</div>
        <div class="vehicle-assign">
          <select v-model="selectedVehicleId" class="sel" :disabled="vehicles.length === 0">
            <option v-if="vehicles.length === 0" :value="null">{{ t('active.noVehicles') }}</option>
            <option v-for="v in vehicles" :key="v.id" :value="v.id">{{ v.name }}</option>
          </select>
          <button class="btn btn--sm btn--primary" @click="$emit('assign')" :disabled="!selectedVehicleId">
            {{ t('active.assign') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Ladestand-Balken -->
    <div v-if="getMeter(session, 'SoC')" class="soc-wrap">
      <div class="soc-track">
        <div class="soc-fill" :style="{ width: Number(getMeter(session, 'SoC')?.value) + '%' }"></div>
      </div>
      <span class="soc-label">{{ Number(getMeter(session, 'SoC')?.value).toFixed(0) }} %</span>
    </div>

    <!-- Animierter Ladebalken -->
    <div class="charge-anim">
      <div class="charge-anim__track"><div class="charge-anim__fill"></div></div>
      <span class="charge-anim__label">{{ t('active.charging') }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ActiveSession, Vehicle } from '~/types'

const props = defineProps<{
  session: ActiveSession
  vehicles: Vehicle[]
  vehicleSelection: number | null
}>()

const emit = defineEmits<{
  'update:vehicleSelection': [number | null]
  assign: []
}>()

const { t, numLocale } = useLocale()
const { getMeter, formatDuration, formatTime, formatEnergy, formatPower } = useFormatters()

const selectedVehicleId = computed({
  get: () => props.vehicleSelection,
  set: (val) => emit('update:vehicleSelection', val),
})

function getVehicle(id: number | null): Vehicle | undefined {
  if (id === null) return undefined
  return props.vehicles.find(v => v.id === id)
}
</script>
