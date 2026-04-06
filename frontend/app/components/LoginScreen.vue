<template>
  <div class="login-page">

    <!-- Topbar – same visual as the app topbar, brand only -->
    <header class="topbar">
      <div class="topbar__inner">
        <div class="topbar__brand">
          <svg class="login-bolt" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
            <path fill="#16a34a" d="M13 2 L4 13 H10 L9 22 L20 11 H14 Z"/>
          </svg>
          <span class="topbar__title">ChargeRelay</span>
        </div>
      </div>
    </header>

    <!-- Centered card -->
    <main class="login-main">
      <div class="login-card" :class="{ 'login-card--shake': shaking }">

        <div class="login-card__header">
          <h2 class="login-card__title">{{ t('auth.title') }}</h2>
          <p class="login-card__sub">{{ t('auth.subtitle') }}</p>
        </div>

        <form class="login-card__body" @submit.prevent="submit" novalidate>

          <div class="form-group">
            <label class="form-label" for="login-pw">{{ t('auth.password') }}</label>
            <div class="login-input-wrap">
              <input
                id="login-pw"
                ref="inputRef"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                class="form-input"
                :class="{ 'form-input--error': errorVisible }"
                placeholder="••••••••"
                autocomplete="current-password"
                spellcheck="false"
                @input="errorVisible = false"
              />
              <button
                type="button"
                class="login-eye"
                :aria-label="showPassword ? t('auth.hidePassword') : t('auth.showPassword')"
                @click="showPassword = !showPassword"
              >
                <!-- Eye open -->
                <svg v-if="!showPassword" viewBox="0 0 24 24" fill="none"
                     stroke="currentColor" stroke-width="2"
                     stroke-linecap="round" stroke-linejoin="round">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
                <!-- Eye closed -->
                <svg v-else viewBox="0 0 24 24" fill="none"
                     stroke="currentColor" stroke-width="2"
                     stroke-linecap="round" stroke-linejoin="round">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8
                           a18.45 18.45 0 0 1 5.06-5.94"/>
                  <path d="M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8
                           a18.5 18.5 0 0 1-2.16 3.19"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
              </button>
            </div>
            <Transition name="err">
              <p v-if="errorVisible" class="login-error" role="alert">
                {{ t('auth.wrongPassword') }}
              </p>
            </Transition>
          </div>

          <button
            type="submit"
            class="btn btn--primary login-submit"
            :disabled="submitting || !password.trim()"
          >
            <span v-if="!submitting">{{ t('auth.signIn') }}</span>
            <span v-else class="login-spinner" :aria-label="t('auth.signingIn')" />
          </button>

        </form>
      </div>
    </main>

  </div>
</template>

<script setup lang="ts">
const emit = defineEmits<{ authenticated: [] }>()

const { t } = useLocale()

const API = ''

const password     = ref('')
const showPassword = ref(false)
const submitting   = ref(false)
const errorVisible = ref(false)
const shaking      = ref(false)

const inputRef = useTemplateRef<HTMLInputElement>('inputRef')

onMounted(() => nextTick(() => inputRef.value?.focus()))

function triggerShake() {
  shaking.value = true
  setTimeout(() => { shaking.value = false }, 450)
}

async function submit() {
  if (submitting.value || !password.value.trim()) return
  submitting.value  = true
  errorVisible.value = false
  try {
    await $fetch(`${API}/api/auth/verify`, {
      method: 'POST',
      body: { password: password.value },
    })
    sessionStorage.setItem('cr_auth', '1')
    emit('authenticated')
  } catch {
    errorVisible.value = true
    password.value = ''
    triggerShake()
    nextTick(() => inputRef.value?.focus())
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
/* ── Page shell ───────────────────────────────────────────────────── */
.login-page {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--bg);
}

/* ── Topbar (mirrors global .topbar) ─────────────────────────────── */
.topbar {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
  padding: 0 1.25rem;
  height: 54px;
  display: flex;
  align-items: center;
}
.topbar__inner {
  display: flex;
  align-items: center;
  width: 100%;
  max-width: 1100px;
  margin: 0 auto;
}
.topbar__brand {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.login-bolt {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  filter: drop-shadow(0 0 5px rgba(22, 163, 74, 0.5));
}
.topbar__title {
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--text);
}

/* ── Centered content area ───────────────────────────────────────── */
.login-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1.25rem;
}

/* ── Card ────────────────────────────────────────────────────────── */
.login-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  width: 100%;
  max-width: 400px;
  overflow: hidden;
}

.login-card--shake {
  animation: shake 0.45s cubic-bezier(0.36, 0.07, 0.19, 0.97) both;
}
@keyframes shake {
  0%, 100% { transform: translateX(0); }
  15%       { transform: translateX(-7px); }
  30%       { transform: translateX(6px); }
  45%       { transform: translateX(-5px); }
  60%       { transform: translateX(4px); }
  75%       { transform: translateX(-2px); }
  90%       { transform: translateX(2px); }
}

.login-card__header {
  padding: 1.5rem 1.5rem 0;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.login-card__title {
  font-size: 1.1rem;
  font-weight: 700;
  color: var(--text);
}
.login-card__sub {
  font-size: 0.825rem;
  color: var(--text-muted);
}

.login-card__body {
  padding: 1.25rem 1.5rem 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

/* ── Password input with eye toggle ──────────────────────────────── */
.login-input-wrap {
  position: relative;
}

/* form-input is a global class – just add padding-right for the button */
.login-input-wrap :deep(.form-input),
.login-input-wrap .form-input {
  padding-right: 2.5rem;
}

.form-input--error {
  border-color: var(--danger) !important;
}
.form-input--error:focus {
  border-color: var(--danger) !important;
  box-shadow: 0 0 0 3px rgba(197, 48, 48, 0.1);
}

.login-eye {
  position: absolute;
  right: 0.6rem;
  top: 50%;
  translate: 0 -50%;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  color: var(--text-dim);
  display: flex;
  align-items: center;
  border-radius: var(--radius-sm);
  transition: color 0.15s, background 0.15s;
}
.login-eye:hover {
  color: var(--text-muted);
  background: var(--bg-hover);
}
.login-eye svg {
  width: 17px;
  height: 17px;
  pointer-events: none;
}

/* ── Error message ───────────────────────────────────────────────── */
.login-error {
  font-size: 0.775rem;
  color: var(--danger);
  margin-top: 0.2rem;
}
.err-enter-active { transition: opacity 0.2s, transform 0.2s; }
.err-leave-active { transition: opacity 0.15s; }
.err-enter-from   { opacity: 0; transform: translateY(-4px); }
.err-leave-to     { opacity: 0; }

/* ── Submit button ───────────────────────────────────────────────── */
.login-submit {
  width: 100%;
  justify-content: center;
  padding: 10px 16px;
  font-size: 0.925rem;
  min-height: 42px;
}

/* Spinner inside button */
.login-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.35);
  border-top-color: #fff;
  border-radius: 50%;
  display: inline-block;
  animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
