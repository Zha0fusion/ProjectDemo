<template>
  <section>
    <el-row :gutter="12" style="margin-bottom: 12px; align-items: center;">
      <el-col :span="12">
        <el-input v-model="eventKeyword" placeholder="Search events" clearable @input="filterEvents" />
      </el-col>
      
    </el-row>

    <div v-if="!eventsLoaded" class="card">Loading events...</div>
    <div v-else-if="filteredEvents.length === 0" class="card">No published events.</div>
    <div v-else>
      <div class="card" v-for="ev in filteredEvents" :key="ev.eid">
        <div class="event-head">
          <el-image :src="ev.image_url || placeholderImage" fit="cover" style="width: 120px; height: 80px; border-radius: 6px;" />
          <div style="flex: 1;">
            <h2>{{ ev.title }}</h2>
            <small class="muted">{{ ev.location }}</small>
            <p v-if="ev.description" class="muted" style="margin: 4px 0;">{{ ev.description }}</p>
            <div class="tag" v-if="ev.allow_multi_session">Multi-session allowed</div>
          </div>
        </div>
        <div class="sessions">
          <div class="session-row" v-for="s in ev.sessions" :key="s.session_id">
            <div>
              <strong>{{ formatDateTime(s.start_time) }}</strong>
              <span class="muted"> - {{ formatDateTime(s.end_time) }}</span>
              <div class="muted">{{ s.current_registered }} / {{ s.capacity }} · {{ s.status }}</div>
            </div>
            <div>
              <el-button
                v-if="store.state.currentUser"
                size="small"
                type="primary"
                :disabled="isSessionRegistered(s.session_id) || s.status !== 'open'"
                @click="handleRegisterClick(s.session_id)"
              >
                {{ isSessionRegistered(s.session_id) ? 'Registered' : 'Register' }}
              </el-button>
              <span v-else class="muted">Login to register</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="card" style="margin-top: 16px;">
      <h2>My Events</h2>
      <div v-if="!myLoaded">Loading...</div>
      <div v-else>
        <el-table :data="myRegistrationsFiltered" size="small" style="width: 100%">
          <el-table-column prop="event_title" label="Event" />
          <el-table-column prop="event_location" label="Location" />
          <el-table-column prop="start_time" label="Start" :formatter="(r)=>formatDateTime(r.start_time)" />
          <el-table-column prop="status" label="Status" />
          <el-table-column label="Actions" width="180">
            <template #default="scope">
              <el-button v-if="scope.row.status !== 'cancelled'" size="small" type="danger" @click="cancelSession(scope.row.session_id)">Cancel</el-button>
              <el-button
                v-if="scope.row.status !== 'cancelled'"
                size="small"
                :icon="Download"
                @click="openQr(scope.row.session_id)"
              >QR</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <el-dialog v-model="noShowDialog" title="Registration Notice" width="420px" :header-style="{ background: 'transparent', borderBottom: 'none' }">
      <p>Missing three check-ins in a row will block your account for one month. Please register only if you will attend.</p>
      <el-checkbox v-model="suppressWarning">Do not show again for this session</el-checkbox>
      <template #footer>
        <el-button @click="noShowDialog = false">Cancel</el-button>
        <el-button type="primary" @click="proceedRegister">Proceed</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="qrDialog" title="Check-in QR" width="360px" :header-style="{ background: 'transparent', borderBottom: 'none' }">
      <div class="qr-panel">
        <div class="qr-bg" :style="{ backgroundImage: `url(${placeholderImage})` }"></div>
        <div class="qr-overlay">
          <img v-if="qrSrc" :src="qrSrc" alt="QR" class="qr-img" />
          <span v-else class="muted">No QR yet</span>
        </div>
      </div>
      <template #footer>
        <el-button @click="qrDialog = false">Close</el-button>
        <el-button type="primary" :icon="Download" @click="downloadQr">Download</el-button>
      </template>
    </el-dialog>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { Download } from '@element-plus/icons-vue';
import { useAppStore } from '../stores/appStore';

const store = useAppStore();
const router = useRouter();
const placeholderImage = 'https://via.placeholder.com/280x160?text=No+Image';

const events = ref([]);
const filteredEvents = ref([]);
const eventsLoaded = ref(false);
const eventKeyword = ref('');

const myRegistrations = ref([]);
const myLoaded = ref(false);
const myRegistrationsFiltered = computed(() => myRegistrations.value.filter((r) => r.status !== 'cancelled'));

const noShowDialog = ref(false);
const pendingSessionId = ref(null);
const suppressWarning = ref(false);

const qrDialog = ref(false);
const qrSrc = ref('');

function go(name) {
  router.push({ name });
}

function filterEvents() {
  const kw = eventKeyword.value.toLowerCase();
  filteredEvents.value = events.value.filter((ev) =>
    ev.title.toLowerCase().includes(kw) || (ev.description || '').toLowerCase().includes(kw),
  );
}

function formatDateTime(val) {
  if (!val) return '';
  return new Date(val).toLocaleString();
}

function isSessionRegistered(sessionId) {
  return myRegistrations.value.some((r) => r.session_id === sessionId && r.status !== 'cancelled');
}

async function loadEvents() {
  eventsLoaded.value = false;
  try {
    const resp = await fetch(store.apiPath('/events/'));
    const list = await resp.json();
    const withSessions = await Promise.all(
      list.map(async (ev) => {
        const sResp = await fetch(store.apiPath(`/events/${ev.eid}/sessions`));
        const sessions = await sResp.json();
        return { ...ev, sessions };
      }),
    );
    events.value = withSessions;
    filterEvents();
  } finally {
    eventsLoaded.value = true;
  }
}

async function loadMyRegistrations() {
  if (!store.state.token) return;
  myLoaded.value = false;
  try {
    const resp = await fetch(store.apiPath('/registrations/me'), { headers: store.getAuthHeaders() });
    if (resp.ok) myRegistrations.value = await resp.json();
  } finally {
    myLoaded.value = true;
  }
}

async function handleRegisterClick(sessionId) {
  if (suppressWarning.value) {
    await registerSession(sessionId);
    return;
  }
  pendingSessionId.value = sessionId;
  noShowDialog.value = true;
}

async function proceedRegister() {
  noShowDialog.value = false;
  if (pendingSessionId.value) {
    await registerSession(pendingSessionId.value);
    pendingSessionId.value = null;
  }
}

async function registerSession(sessionId) {
  try {
    const resp = await fetch(store.apiPath('/registrations/'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...store.getAuthHeaders() },
      body: JSON.stringify({ session_id: sessionId }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      ElMessage.error(data.message_en || data.message_zh || 'Registration failed');
    } else {
      ElMessage.success(data.message_en || 'Registration successful');
      loadEvents();
      loadMyRegistrations();
    }
  } catch (e) {
    ElMessage.error('Network error when registering');
  }
}

async function cancelSession(sessionId) {
  try {
    const resp = await fetch(store.apiPath('/registrations/cancel'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...store.getAuthHeaders() },
      body: JSON.stringify({ session_id: sessionId }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      ElMessage.error(data.message_en || 'Cancellation failed');
    } else {
      ElMessage.success(data.message_en || 'Cancelled');
      loadEvents();
      loadMyRegistrations();
    }
  } catch (e) {
    ElMessage.error('Network error when cancelling');
  }
}

async function openQr(sessionId) {
  const resp = await fetch(store.apiPath(`/registrations/qrcode/${sessionId}`), { headers: store.getAuthHeaders() });
  if (resp.ok) {
    const blob = await resp.blob();
    qrSrc.value = URL.createObjectURL(blob);
    qrDialog.value = true;
  }
}

function downloadQr() {
  if (!qrSrc.value) return;
  const a = document.createElement('a');
  a.href = qrSrc.value;
  a.download = 'registration_qr.png';
  a.click();
}

onMounted(() => {
  if (!store.state.currentUser) {
    store.fetchMe();
  }
  loadEvents();
  loadMyRegistrations();
});
</script>

<style scoped>

.qr-panel {
  position: relative;
  width: 100%;
  border-radius: 12px;
  overflow: hidden;
  min-height: 260px;
}
.qr-bg {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  filter: blur(10px);
  transform: scale(1.05);
}
.qr-overlay {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
}
.qr-img {
  max-width: 240px;
  border-radius: 8px;
  background: #fff;
  padding: 8px;
}
.muted {
  color: #6b7280;
}
</style>
