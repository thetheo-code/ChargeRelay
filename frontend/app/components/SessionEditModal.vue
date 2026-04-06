<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">

      <div class="modal__header">
        <h3 class="modal__title">{{ t('sessionEdit.title') }}</h3>
        <button class="modal__close" @click="$emit('close')">✕</button>
      </div>

      <div class="modal__body">

        <!-- Session info -->
        <div class="session-info">
          <div class="session-info__row">
            <span class="session-info__label">{{ t('sessionEdit.chargePoint') }}</span>
            <span class="session-info__val">
              {{ session.model || session.charge_point_id }}
              <span class="connector-badge">C{{ session.connector_id }}</span>
            </span>
          </div>
          <div class="session-info__row">
            <span class="session-info__label">{{ t('sessionEdit.start') }}</span>
            <span class="session-info__val mono">{{ formatDate(session.start_time) }}</span>
          </div>
          <div class="session-info__row" v-if="session.stop_time">
            <span class="session-info__label">{{ t('sessionEdit.end') }}</span>
            <span class="session-info__val mono">{{ formatDate(session.stop_time) }}</span>
          </div>
          <div class="session-info__row" v-if="session.energy_kwh != null">
            <span class="session-info__label">{{ t('sessionEdit.energy') }}</span>
            <span class="session-info__val mono energy">
              {{ session.energy_kwh.toLocaleString(numLocale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }} kWh
            </span>
          </div>
        </div>

        <!-- Vehicle assignment -->
        <div class="form-group">
          <label class="form-label">{{ t('sessionEdit.vehicle') }}</label>
          <select v-model="selectedVehicleId" class="form-input" :disabled="confirmingDelete">
            <option :value="null">{{ t('sessionEdit.noVehicle') }}</option>
            <option v-for="v in vehicles" :key="v.id" :value="v.id">{{ v.name }}</option>
          </select>
        </div>

        <!-- Delete confirmation -->
        <div v-if="confirmingDelete" class="delete-confirm">
          <span class="delete-confirm__text">{{ t('sessionEdit.deleteConfirm') }}</span>
          <div class="delete-confirm__btns">
            <button class="btn btn--ghost btn--sm" @click="confirmingDelete = false">{{ t('sessionEdit.cancel') }}</button>
            <button class="btn btn--danger btn--sm" @click="$emit('delete')" :disabled="saving">
              {{ saving ? t('sessionEdit.deleting') : t('sessionEdit.confirmDelete') }}
            </button>
          </div>
        </div>

      </div>

      <div class="modal__footer">
        <!-- Delete button left -->
        <button
          v-if="!confirmingDelete"
          class="btn btn--danger btn--sm footer-delete"
          @click="confirmingDelete = true"
        >{{ t('sessionEdit.delete') }}</button>

        <div class="footer-right">
          <button class="btn btn--ghost" @click="$emit('close')" :disabled="saving">{{ t('sessionEdit.cancel') }}</button>
          <button class="btn btn--primary" @click="submit" :disabled="saving || confirmingDelete">
            {{ saving ? t('sessionEdit.saving') : t('sessionEdit.save') }}
          </button>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import type { Session, Vehicle } from '~/types'

const props = defineProps<{
  session: Session
  vehicles: Vehicle[]
  saving: boolean
}>()

const emit = defineEmits<{
  close: []
  save: [{ vehicleId: number | null }]
  delete: []
}>()

const { t, numLocale } = useLocale()
const { formatDate } = useFormatters()

const selectedVehicleId = ref<number | null>(props.session.vehicle_id)
const confirmingDelete = ref(false)

function submit() {
  emit('save', { vehicleId: selectedVehicleId.value })
}
</script>

<style scoped>
.session-info {
  background: var(--bg-card-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 0.875rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}
.session-info__row {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: 1rem;
}
.session-info__label {
  font-size: 0.75rem;
  color: var(--text-muted);
  white-space: nowrap;
  flex-shrink: 0;
}
.session-info__val {
  font-size: 0.875rem;
  color: var(--text);
  text-align: right;
}

/* Inline-Bestätigung */
.delete-confirm {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  background: var(--danger-dim);
  border: 1px solid rgba(197,48,48,0.2);
  border-radius: var(--radius-sm);
  padding: 0.65rem 0.875rem;
  flex-wrap: wrap;
}
.delete-confirm__text {
  font-size: 0.825rem;
  font-weight: 600;
  color: var(--danger);
}
.delete-confirm__btns {
  display: flex;
  gap: 0.5rem;
}

/* Footer-Layout */
.modal__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.footer-delete {
  flex-shrink: 0;
}
.footer-right {
  display: flex;
  gap: 0.75rem;
  margin-left: auto;
}
</style>
