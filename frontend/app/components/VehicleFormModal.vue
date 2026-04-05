<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal__header">
        <h3 class="modal__title">{{ editingVehicle ? 'Fahrzeug bearbeiten' : 'Neues Fahrzeug' }}</h3>
        <button class="modal__close" @click="$emit('close')">✕</button>
      </div>

      <div class="modal__body">
        <!-- Bild-Upload -->
        <div class="form-group">
          <label class="form-label">Bild</label>
          <div class="image-upload">
            <img v-if="form.image_data" :src="form.image_data" class="image-preview" alt="">
            <div v-else class="image-placeholder">Kein Bild ausgewählt</div>
            <div class="image-upload__btns">
              <label class="btn btn--ghost btn--sm">
                Bild wählen
                <input type="file" accept="image/*" class="sr-only" @change="handleImageUpload">
              </label>
              <button v-if="form.image_data" class="btn btn--ghost btn--sm" @click="form.image_data = null">
                Entfernen
              </button>
            </div>
          </div>
        </div>

        <!-- Name -->
        <div class="form-group">
          <label class="form-label">Name <span class="required">*</span></label>
          <input v-model="form.name" class="form-input" placeholder="z.B. ID 3" type="text">
        </div>

        <!-- RFID-Tag -->
        <div class="form-group">
          <label class="form-label">RFID-Tag</label>
          <input v-model="form.id_tag" class="form-input mono" placeholder="z.B. RFID-0001" type="text">
          <div class="form-hint">Wird beim Laden per RFID automatisch erkannt und zugewiesen</div>
        </div>
      </div>

      <div class="modal__footer">
        <button class="btn btn--ghost" @click="$emit('close')">Abbrechen</button>
        <button class="btn btn--primary" @click="submit" :disabled="!form.name.trim() || saving">
          {{ saving ? 'Speichern …' : 'Speichern' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Vehicle } from '~/types'

const props = defineProps<{
  editingVehicle: Vehicle | null
  saving: boolean
}>()

const emit = defineEmits<{
  close: []
  save: [data: { name: string; id_tag: string | null; image_data: string | null }]
}>()

const form = ref({ name: '', id_tag: '', image_data: null as string | null })

// Formular bei jedem Öffnen / Wechsel des bearbeiteten Fahrzeugs neu befüllen
watch(() => props.editingVehicle, (v) => {
  form.value = v
    ? { name: v.name, id_tag: v.id_tag || '', image_data: v.image_data }
    : { name: '', id_tag: '', image_data: null }
}, { immediate: true })

function handleImageUpload(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = (e) => { form.value.image_data = e.target?.result as string }
  reader.readAsDataURL(file)
}

function submit() {
  if (!form.value.name.trim()) return
  emit('save', {
    name: form.value.name.trim(),
    id_tag: form.value.id_tag.trim() || null,
    image_data: form.value.image_data,
  })
}
</script>
