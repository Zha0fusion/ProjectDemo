<template>
  <section class="card">
    <div class="card-head">
      <h2>Session Scanner</h2>
      <span class="muted">Session {{ activeSession?.session_id || '-' }}</span>
      <button class="ghost" @click="toggleFullscreen">Fullscreen</button>
    </div>

    <div class="scanner-layout">
      <div class="panel-left">
        <div class="panel-bg" :style="{ backgroundImage: `url(${activeSession?.image_url || fallbackImage})` }"></div>
        <div class="panel-overlay"></div>
        <div class="panel-content">
          <div class="session-head">
            <div class="eyebrow">{{ activeSession?.event_title || 'No event loaded' }}</div>
            <div class="session-line">Session {{ activeSession?.session_id || '-' }} · {{ sessionOrder ? `#${sessionOrder.position} of ${sessionOrder.total}` : 'N/A' }}</div>
          </div>
          <div class="info-grid">
            <div><strong>Time</strong><span>{{ formatDateTime(activeSession?.start_time) }} - {{ formatDateTime(activeSession?.end_time) }}</span></div>
            <div><strong>Capacity</strong><span>{{ activeSession?.current_registered || 0 }}/{{ activeSession?.capacity || '-' }}</span></div>
            <div><strong>Status</strong><span>{{ activeSession?.status || '-' }}</span></div>
          </div>

          <div class="card current-card">
            <h4>Current Check-in</h4>
            <div v-if="!currentCheckin" class="muted">No scans yet.</div>
            <div v-else class="current-row" :class="currentCheckin.status">
              <div class="pill" :class="currentCheckin.status === 'success' ? 'pill-success' : 'pill-error'">{{ currentCheckin.status }}</div>
              <div class="message">{{ currentCheckin.message }}</div>
              <div class="muted">User: {{ currentCheckin.user_name || currentCheckin.user_id || '-' }}</div>
              <div class="muted">Session: {{ currentCheckin.session_id || '-' }}</div>
              <div class="muted">Time: {{ formatDateTime(currentCheckin.time) }}</div>
            </div>
          </div>
        </div>
      </div>

      <div class="scan-panel">
        <div id="qr-scan-area" ref="scannerRef" class="scan-box" />
        <div v-if="qrInitError" class="muted" style="color: #f87171;">{{ qrInitError }}</div>
        <div v-else class="muted">Point the camera at the QR code; results appear in Current Check-in on the left.</div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { Html5QrcodeScanner } from 'html5-qrcode';
import { useRouter } from 'vue-router';
import { useAppStore } from '../stores/appStore';

const store = useAppStore();
const router = useRouter();

const loadingSessions = ref(false);
const todaySessions = ref([]);
const activeSession = ref(null);
const currentCheckin = ref(null);
const qrInitError = ref('');

const scannerRef = ref(null);
let scannerInstance = null;
const fallbackImage = 'https://imgs.design006.com/202311/Design006_Mf3aN4faZD.jpg';

const sessionIdFromQuery = computed(() => Number(router.currentRoute.value.query.session_id) || null);
const sessionOrder = computed(() => {
  if (!activeSession.value || !todaySessions.value.length) return null;
  const sameEvent = todaySessions.value
    .filter((s) => s.eid === activeSession.value.eid)
    .sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
  const idx = sameEvent.findIndex((s) => s.session_id === activeSession.value.session_id);
  if (idx === -1) return null;
  return { position: idx + 1, total: sameEvent.length };
});

function formatDateTime(val) {
  if (!val) return '';
  return new Date(val).toLocaleString();
}

function setCurrent(entry) {
  currentCheckin.value = { ...entry, time: entry.time || new Date().toISOString() };
}

async function ensureUser() {
  if (!store.state.currentUser && store.state.token) {
    await store.fetchMe();
  }
  if (!store.isStaff.value) {
    router.push({ name: 'visitor' });
  }
}

async function loadSessions() {
  loadingSessions.value = true;
  try {
    const resp = await fetch(store.apiPath('/events/today-sessions'), { headers: store.getAuthHeaders() });
    if (!resp.ok) throw new Error('Failed to load sessions');
    todaySessions.value = await resp.json();
    todaySessions.value.sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
    const target = todaySessions.value.find((s) => s.session_id === sessionIdFromQuery.value);
    if (target) {
      activeSession.value = target;
      startScanner();
    } else {
      qrInitError.value = 'Session not found or not today.';
    }
  } catch (err) {
    qrInitError.value = err.message || 'Failed to load sessions';
  } finally {
    loadingSessions.value = false;
  }
}

function startScanner() {
  if (!scannerRef.value || !activeSession.value) {
    qrInitError.value = 'No session selected.';
    return;
  }
  stopScanner();
  qrInitError.value = '';
  const config = { fps: 10, qrbox: 250, rememberLastUsedCamera: true, aspectRatio: 1.0 };
  scannerInstance = new Html5QrcodeScanner('qr-scan-area', config, false);
  scannerInstance.render(
    (decodedText) => {
      handleDecoded(decodedText);
    },
    (errorMessage) => {
      if (!qrInitError.value && typeof errorMessage === 'string') {
        const lower = errorMessage.toLowerCase();
        if (lower.includes('camera') || lower.includes('permission') || lower.includes('not found')) {
          qrInitError.value = errorMessage;
        }
      }
    }
  );
}

function stopScanner() {
  if (scannerInstance?.clear) {
    scannerInstance.clear().catch(() => {});
  }
  scannerInstance = null;
}

async function handleDecoded(decodedText) {
  let payload;
  try {
    payload = JSON.parse(decodedText);
  } catch (e) {
    setCurrent({ status: 'error', message: 'QR content is not valid JSON', session_id: activeSession.value?.session_id });
    return;
  }
  const userId = payload.user_id;
  const qrSessionId = payload.session_id;
  const targetSessionId = activeSession.value?.session_id;
  if (qrSessionId && qrSessionId !== targetSessionId) {
    setCurrent({ status: 'error', message: `Session mismatch: QR ${qrSessionId} vs current ${targetSessionId}`, user_id: userId, session_id: targetSessionId });
    return;
  }
  await performCheckin(userId, targetSessionId);
}

async function performCheckin(userId, sessionId) {
  if (!userId) {
    setCurrent({ status: 'error', message: 'Missing user id', session_id: sessionId });
    return;
  }
  if (!sessionId) {
    setCurrent({ status: 'error', message: 'Missing session id', session_id: '-' });
    return;
  }
  try {
    const resp = await fetch(store.apiPath('/checkin/'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...store.getAuthHeaders() },
      body: JSON.stringify({ user_id: userId, session_id: sessionId }),
    });
    const data = await resp.json();
    if (resp.ok) {
      setCurrent({ status: 'success', message: data.message_en || data.message_zh || 'Checked in', user_id: userId, user_name: data.user_name, session_id: sessionId });
    } else {
      setCurrent({ status: 'error', message: data.message_en || data.message_zh || 'Check-in failed', user_id: userId, session_id: sessionId });
    }
  } catch (err) {
    setCurrent({ status: 'error', message: err.message || 'Network error', user_id: userId, session_id: sessionId });
  }
}

function toggleFullscreen() {
  const el = document.documentElement;
  if (!document.fullscreenElement) {
    el.requestFullscreen?.();
  } else {
    document.exitFullscreen?.();
  }
}

onMounted(async () => {
  await ensureUser();
  await loadSessions();
});

onBeforeUnmount(() => {
  stopScanner();
});
</script>

<style scoped>
.scanner-layout {
  display: grid;
  grid-template-columns: 1.05fr 1fr;
  gap: 16px;
  align-items: stretch;
}
.panel-left {
  position: relative;
  min-height: 480px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 8px 20px rgba(0,0,0,0.2);
}
.panel-bg {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  transform: scale(1.05);
  filter: blur(12px);
}
.panel-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0,0,0,0.45);
}
.panel-content {
  position: relative;
  z-index: 1;
  height: 100%;
  padding: 20px;
  color: #fff;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.session-head {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.eyebrow {
  font-size: 14px;
  color: #cbd5e1;
  letter-spacing: 0.02em;
}
.session-line {
  font-weight: 700;
  font-size: 20px;
}
.info-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 10px;
  padding: 12px;
}
.info-grid div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.info-grid strong {
  font-size: 13px;
  color: #cbd5e1;
  font-weight: 600;
}
.info-grid span {
  font-size: 15px;
}
.scan-panel {
  background: #0b0b0b;
  border-radius: 12px;
  padding: 12px;
  color: #fff;
  box-shadow: 0 8px 20px rgba(0,0,0,0.2);
}
.current-card {
  padding: 12px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.08);
  color: #fff;
}
.current-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.pill {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  display: inline-block;
  text-transform: capitalize;
  width: fit-content;
}
.pill-success { background: #ecfdf3; color: #0f9f6e; }
.pill-error { background: #fef2f2; color: #b91c1c; }
.ghost {
  background: #f8fafc;
  color: #111827;
  border: 1px solid #e5e7eb;
  padding: 8px 12px;
  border-radius: 8px;
  cursor: pointer;
}
.scan-box {
  width: 100%;
  min-height: 360px;
  border-radius: 12px;
  overflow: hidden;
  background: #000;
}
.muted {
  color: #9ca3af;
}
@media (max-width: 900px) {
  .scanner-layout {
    grid-template-columns: 1fr;
  }
}
</style>
