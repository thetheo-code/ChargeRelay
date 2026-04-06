<template>
  <div class="modal-overlay" @click.self="$emit('close')">
    <div class="modal">
      <div class="modal__header">
        <h3 class="modal__title">{{ editingVehicle ? t('vehicleForm.titleEdit') : t('vehicleForm.titleNew') }}</h3>
        <button class="modal__close" @click="$emit('close')">✕</button>
      </div>

      <div class="modal__body">
        <!-- Image upload -->
        <div class="form-group">
          <label class="form-label">{{ t('vehicleForm.image') }}</label>
          <div class="image-upload">
            <img v-if="form.image_data" :src="form.image_data" class="image-preview" alt="">
            <div v-else class="image-placeholder">–</div>
            <div class="image-upload__btns">
              <label class="btn btn--ghost btn--sm">
                {{ t('vehicleForm.chooseImage') }}
                <input type="file" accept="image/*" class="sr-only" @change="handleImageUpload">
              </label>
              <button v-if="form.image_data" class="btn btn--ghost btn--sm" @click="form.image_data = null">
                {{ t('vehicleForm.removeImage') }}
              </button>
            </div>
          </div>
        </div>

        <!-- Name -->
        <div class="form-group">
          <label class="form-label">{{ t('vehicleForm.name') }} <span class="required">*</span></label>
          <input v-model="form.name" class="form-input" :placeholder="t('vehicleForm.namePlaceholder')" type="text">
        </div>

        <!-- RFID tag -->
        <div class="form-group">
          <label class="form-label">{{ t('vehicleForm.rfid') }}</label>
          <input v-model="form.id_tag" class="form-input mono" :placeholder="t('vehicleForm.rfidPlaceholder')" type="text">
          <div class="form-hint">{{ t('vehicleForm.rfidHint') }}</div>
        </div>
      </div>

      <div class="modal__footer">
        <button class="btn btn--ghost" @click="$emit('close')">{{ t('vehicleForm.cancel') }}</button>
        <button class="btn btn--primary" @click="submit" :disabled="!form.name.trim() || saving">
          {{ saving ? t('vehicleForm.saving') : t('vehicleForm.save') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { Vehicle } from '~/types'

const { t } = useLocale()

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
