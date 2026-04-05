<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal modal--wide">

      <div class="modal__header">
        <h3 class="modal__title">{{ editingReport ? 'Report bearbeiten' : 'Neuer Report' }}</h3>
        <button class="modal__close" @click="$emit('close')">✕</button>
      </div>

      <div class="modal__body">

        <!-- Name -->
        <div class="form-group">
          <label class="form-label">Name <span class="required">*</span></label>
          <input v-model="form.name" class="form-input" placeholder="z.B. Monatsbericht Fuhrpark" type="text">
        </div>

        <!-- Fahrzeuge -->
        <div class="form-group">
          <div class="vehicles-header">
            <label class="form-label">Fahrzeuge <span class="required">*</span></label>
            <button
              v-if="vehicles.length > 0"
              type="button"
              class="select-all-btn"
              :class="{ 'select-all-btn--active': allSelected }"
              @click="toggleSelectAll"
            >
              <span class="select-all-btn__box">
                <span v-if="allSelected" class="select-all-btn__tick">✔</span>
              </span>
              Alle
            </button>
          </div>
          <div v-if="vehicles.length === 0" class="form-hint">Noch keine Fahrzeuge vorhanden.</div>
          <div v-else class="vehicle-checks">
            <label
              v-for="v in vehicles"
              :key="v.id"
              class="vehicle-check"
              :class="{ 'vehicle-check--active': form.vehicle_ids.includes(v.id) }"
            >
              <input
                type="checkbox"
                :value="v.id"
                v-model="form.vehicle_ids"
                class="sr-only"
              >
              <span class="vehicle-check__name">{{ v.name }}</span>
              <span v-if="form.vehicle_ids.includes(v.id)" class="vehicle-check__tick">✔</span>
            </label>
          </div>
        </div>

        <!-- Lieferwege -->
        <div class="form-group">
          <div class="deliveries-header">
            <label class="form-label">Lieferwege <span class="required">*</span></label>
            <button type="button" class="btn btn--ghost btn--sm" @click="addDelivery">+ Hinzufügen</button>
          </div>

          <div v-if="form.deliveries.length === 0" class="form-hint">
            Noch kein Lieferweg – klicke „+ Hinzufügen".
          </div>

          <div class="delivery-list">
            <div v-for="(d, i) in form.deliveries" :key="i" class="delivery-item">

              <!-- Typ-Auswahl -->
              <div class="delivery-item__row">
                <div class="form-group delivery-item__type">
                  <label class="form-label">Typ</label>
                  <select v-model="d.type" class="form-input">
                    <option value="mail">E-Mail</option>
                    <option value="ocpp">OCPP-Weiterleitung</option>
                  </select>
                </div>
                <button type="button" class="delivery-item__remove" @click="removeDelivery(i)" title="Entfernen">✕</button>
              </div>

              <!-- Mail-Felder -->
              <template v-if="d.type === 'mail'">
                <div class="delivery-item__row">
                  <div class="form-group delivery-item__field">
                    <label class="form-label">E-Mail-Adresse <span class="required">*</span></label>
                    <input v-model="d.email" class="form-input" type="email" placeholder="empfaenger@beispiel.de">
                  </div>
                  <div class="form-group delivery-item__field">
                    <label class="form-label">Intervall <span class="required">*</span></label>
                    <select v-model="d.interval" class="form-input">
                      <option value="daily">Täglich</option>
                      <option value="weekly">Wöchentlich</option>
                      <option value="monthly">Monatlich</option>
                      <option value="yearly">Jährlich</option>
                    </select>
                  </div>
                </div>
              </template>

              <!-- OCPP-Felder -->
              <template v-if="d.type === 'ocpp'">
                <div class="delivery-item__row">
                  <div class="form-group delivery-item__field delivery-item__field--grow">
                    <label class="form-label">Adresse <span class="required">*</span></label>
                    <input v-model="d.address" class="form-input mono" type="text" placeholder="relay.beispiel.de">
                  </div>
                  <div class="form-group delivery-item__field delivery-item__field--port">
                    <label class="form-label">Port <span class="required">*</span></label>
                    <input v-model="d.port" class="form-input mono" type="number" placeholder="9000" min="1" max="65535">
                  </div>
                </div>
              </template>

            </div>
          </div>
        </div>

      </div>

      <div class="modal__footer">
        <button class="btn btn--ghost" @click="$emit('close')">Abbrechen</button>
        <button class="btn btn--primary" @click="submit" :disabled="!canSave || saving">
          {{ saving ? 'Speichern …' : 'Speichern' }}
        </button>
      </div>

    </div>
  </div>
</template>

<script setup lang="ts">
import type { Report, Vehicle } from '~/types'

type DeliveryForm = {
  type: 'mail' | 'ocpp'
  email: string
  interval: string
  address: string
  port: string
}

type SavePayload = {
  name: string
  vehicle_ids: number[]
  deliveries: {
    type: string
    email: string | null
    interval: string | null
    address: string | null
    port: number | null
  }[]
}

const props = defineProps<{
  editingReport: Report | null
  vehicles: Vehicle[]
  saving: boolean
}>()

const emit = defineEmits<{
  close: []
  save: [data: SavePayload]
}>()

const form = ref({
  name: '',
  vehicle_ids: [] as number[],
  deliveries: [] as DeliveryForm[],
})

// Formular bei Öffnen / Wechsel befüllen
watch(() => props.editingReport, (r) => {
  if (r) {
    form.value = {
      name: r.name,
      vehicle_ids: r.vehicles.map(v => v.id),
      deliveries: r.deliveries.map(d => ({
        type: d.type,
        email: d.email ?? '',
        interval: d.interval ?? 'monthly',
        address: d.address ?? '',
        port: d.port?.toString() ?? '',
      })),
    }
  } else {
    form.value = { name: '', vehicle_ids: [], deliveries: [] }
  }
}, { immediate: true })

function addDelivery() {
  form.value.deliveries.push({ type: 'mail', email: '', interval: 'monthly', address: '', port: '' })
}

function removeDelivery(i: number) {
  form.value.deliveries.splice(i, 1)
}

const allSelected = computed(() =>
  props.vehicles.length > 0 &&
  props.vehicles.every(v => form.value.vehicle_ids.includes(v.id))
)

function toggleSelectAll() {
  if (allSelected.value) {
    form.value.vehicle_ids = []
  } else {
    form.value.vehicle_ids = props.vehicles.map(v => v.id)
  }
}

const canSave = computed(() =>
  form.value.name.trim().length > 0 &&
  form.value.vehicle_ids.length > 0 &&
  form.value.deliveries.length > 0 &&
  form.value.deliveries.every(d =>
    d.type === 'mail'
      ? d.email.trim().length > 0 && d.interval.length > 0
      : d.address.trim().length > 0 && d.port.trim().length > 0
  )
)

function submit() {
  if (!canSave.value) return
  emit('save', {
    name: form.value.name.trim(),
    vehicle_ids: form.value.vehicle_ids,
    deliveries: form.value.deliveries.map(d => ({
      type: d.type,
      email:    d.type === 'mail' ? d.email.trim()   : null,
      interval: d.type === 'mail' ? d.interval        : null,
      address:  d.type === 'ocpp' ? d.address.trim()  : null,
      port:     d.type === 'ocpp' ? (parseInt(d.port) || null) : null,
    })),
  })
}
</script>

<style scoped>
.modal--wide {
  max-width: 580px !important;
}

/* Fahrzeug-Header */
.vehicles-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}
.select-all-btn {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: none;
  border: 1px solid var(--border);
  border-radius: 99px;
  padding: 3px 10px 3px 6px;
  font-size: 0.775rem;
  font-weight: 500;
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.select-all-btn:hover {
  border-color: var(--accent);
  color: var(--text);
}
.select-all-btn--active {
  background: var(--accent-dim);
  border-color: rgba(22,163,74,0.35);
  color: var(--accent);
  font-weight: 600;
}
.select-all-btn__box {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  border: 1.5px solid currentColor;
  border-radius: 3px;
  font-size: 0.6rem;
  flex-shrink: 0;
}
.select-all-btn__tick {
  line-height: 1;
}

/* Fahrzeug-Checkboxen */
.vehicle-checks {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.vehicle-check {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 5px 12px;
  border-radius: 99px;
  border: 1px solid var(--border);
  background: var(--bg-card-2);
  cursor: pointer;
  font-size: 0.825rem;
  color: var(--text-muted);
  transition: background 0.15s, border-color 0.15s, color 0.15s;
  user-select: none;
}
.vehicle-check:hover {
  border-color: var(--accent);
  color: var(--text);
}
.vehicle-check--active {
  background: var(--accent-dim);
  border-color: rgba(22,163,74,0.35);
  color: var(--accent);
  font-weight: 600;
}
.vehicle-check__tick {
  font-size: 0.7rem;
  font-weight: 900;
}

/* Lieferwege */
.deliveries-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}
.delivery-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.delivery-item {
  background: var(--bg-card-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 0.875rem;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}
.delivery-item__row {
  display: flex;
  gap: 0.75rem;
  align-items: flex-end;
}
.delivery-item__type {
  flex: 1;
  margin-bottom: 0;
}
.delivery-item__remove {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-dim);
  font-size: 0.875rem;
  padding: 6px 8px;
  border-radius: var(--radius-sm);
  line-height: 1;
  transition: background 0.15s, color 0.15s;
  align-self: flex-end;
  flex-shrink: 0;
}
.delivery-item__remove:hover {
  background: var(--danger-dim);
  color: var(--danger);
}
.delivery-item__field {
  flex: 1;
  margin-bottom: 0;
}
.delivery-item__field--grow {
  flex: 2;
}
.delivery-item__field--port {
  flex: 0 0 100px;
}
</style>
