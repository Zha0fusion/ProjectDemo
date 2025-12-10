<template>
  <section v-if="hasAccess" class="checkin-page">
    <header class="page-head">
      <div>
        <h2>Check-in Panel</h2>
        <p class="muted">Search registrants or open the dedicated scanner page.</p>
      </div>
      <button class="ghost" :disabled="loadingSessions" @click="loadTodaySessions">
        {{ loadingSessions ? 'Refreshing…' : 'Refresh sessions' }}
      </button>
    </header>

    <div class="grid">
      <div class="main-col">
        <div class="card block">
          <div class="block-head">
            <h3>Camera Preview</h3>
            <button class="ghost" @click="startCamera">Restart</button>
          </div>
          <div class="video-shell">
            <video ref="videoRef" autoplay playsinline muted></video>
          </div>
        </div>

        <div class="card block">
          <div class="block-head">
            <h3>Manual Search</h3>
            <span class="muted">Enter user id or name, then check in.</span>
          </div>
          <div class="search-row">
            <input
              v-model="searchKeyword"
              type="text"
              placeholder="User id or name"
              @keyup.enter="searchRegistrations"
            />
            <button :disabled="searchLoading" @click="searchRegistrations">
              {{ searchLoading ? 'Searching…' : 'Search' }}
            </button>
            <button class="ghost" @click="clearSearch">Clear</button>
          </div>
          <p v-if="searchError" class="error">{{ searchError }}</p>
          <p v-else-if="!searchResults.length && !searchLoading" class="muted">No results yet.</p>
          <div v-if="searchLoading" class="muted">Loading registrations…</div>
          <table v-if="searchResults.length" class="results">
            <thead>
              <tr>
                <th>Event</th>
                <th>Session</th>
                <th>User</th>
                <th>User ID</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in searchResults" :key="`${row.user_id}-${row.session_id}`">
                <td>{{ row.event_title }}</td>
                <td>{{ row.session_id }}</td>
                <td>{{ row.user_name || 'Unknown' }}</td>
                <td>{{ row.user_id }}</td>
                <td class="actions">
                  <button :disabled="checkinBusy" @click="checkinFromResult(row)">
                    {{ checkinBusy ? 'Working…' : 'Check in' }}
                  </button>
                  <span v-if="row.session_id !== activeSessionId" class="muted">Uses session {{ row.session_id }}</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="card block">
          <div class="block-head">
            <h3>Check-in History</h3>
            <button class="ghost" :disabled="historyLoading" @click="loadHistory">{{ historyLoading ? 'Refreshing…' : 'Refresh' }}</button>
          </div>
          <p v-if="historyError" class="error">{{ historyError }}</p>
          <el-table v-else :data="historyRows" size="small" style="width: 100%" :empty-text="historyLoading ? 'Loading…' : 'No history yet.'">
            <el-table-column prop="event_title" label="Event" />
            <el-table-column prop="session_id" label="Session" width="100" />
            <el-table-column prop="user_name" label="User" />
            <el-table-column prop="user_id" label="User ID" width="100" />
            <el-table-column prop="checkin_time" label="Check-in Time" :formatter="(_, __, val) => formatDateTime(val)" />
          </el-table>
        </div>
      </div>

      <div class="side-col card block">
        <div class="block-head">
          <h3>Today’s Sessions</h3>
        </div>
        <div v-if="loadingSessions" class="muted">Loading sessions…</div>
        <ul v-else class="session-list">
          <li v-for="session in todaySessions" :key="session.session_id" :class="{ active: session.session_id === activeSessionId }">
            <div class="session-meta">
              <strong>{{ session.title || session.event_title }}</strong>
              <div class="muted">{{ formatDateTime(session.start_time) }} - {{ formatDateTime(session.end_time) }}</div>
            </div>
            <div class="session-actions">
              <button class="ghost" :disabled="session.session_id === activeSessionId" @click="setActiveSession(session)">Set current</button>
              <button @click="openScanner(session)">Open scanner</button>
            </div>
          </li>
          <li v-if="!todaySessions.length" class="muted">No sessions today.</li>
        </ul>
      </div>
    </div>
  </section>

  <section v-else class="card">
    <p>Staff access only.</p>
  </section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { useAppStore } from '../stores/appStore';

const store = useAppStore();
const router = useRouter();
const hasAccess = computed(() => store.isStaff.value);

const loadingSessions = ref(false);
const todaySessions = ref([]);
const activeSessionId = ref(null);
const historyRows = ref([]);
const historyLoading = ref(false);
const historyError = ref('');
const checkinBusy = ref(false);

const videoRef = ref(null);

const searchKeyword = ref('');
const searchResults = ref([]);
const searchLoading = ref(false);
const searchError = ref('');

function formatDateTime(val) {
  if (!val) return '';
  const d = new Date(val);
  if (Number.isNaN(d.getTime())) return val;
  return d.toLocaleString();
}

async function ensureUser() {
  if (!store.state.currentUser && store.state.token) {
    await store.fetchMe();
  }
  if (!store.isStaff.value) {
    router.push({ name: 'visitor' });
  }
}

async function loadTodaySessions() {
  loadingSessions.value = true;
  try {
    const resp = await fetch(store.apiPath('/events/today-sessions'), { headers: store.getAuthHeaders() });
    if (!resp.ok) throw new Error('Failed to load sessions');
    todaySessions.value = await resp.json();
    todaySessions.value.sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
    if (todaySessions.value.length && !activeSessionId.value) {
      activeSessionId.value = todaySessions.value[0].session_id;
    }
  } catch (err) {
    todaySessions.value = [];
  } finally {
    loadingSessions.value = false;
  }
}

function setActiveSession(session) {
  activeSessionId.value = session.session_id;
}

function openScanner(session) {
  const resolved = router.resolve({ name: 'scan', query: { session_id: session.session_id } });
  window.open(resolved.href, '_blank');
}

async function performCheckin(userId, sessionId) {
  const sid = sessionId || activeSessionId.value;
  if (!userId) {
    return;
  }
  if (!sid) {
    return;
  }

  checkinBusy.value = true;
  try {
    const resp = await fetch(store.apiPath('/checkin/'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...store.getAuthHeaders() },
      body: JSON.stringify({ user_id: userId, session_id: sid }),
    });
    const data = await resp.json();
    if (!resp.ok) {
      throw new Error(data.message_en || data.message_zh || 'Check-in failed');
    }
    await loadHistory();
  } catch (err) {
    historyError.value = err.message || 'Check-in failed';
  } finally {
    checkinBusy.value = false;
  }
}

async function loadHistory() {
  historyLoading.value = true;
  historyError.value = '';
  try {
    const resp = await fetch(store.apiPath('/checkin/history?limit=100'), { headers: store.getAuthHeaders() });
    if (!resp.ok) throw new Error('Failed to load history');
    historyRows.value = await resp.json();
  } catch (err) {
    historyError.value = err.message || 'Failed to load history';
    historyRows.value = [];
  } finally {
    historyLoading.value = false;
  }
}

async function searchRegistrations() {
  searchError.value = '';
  searchResults.value = [];
  const kw = (searchKeyword.value || '').trim();
  if (!kw) {
    searchError.value = 'Enter a user id or name.';
    return;
  }
  searchLoading.value = true;
  try {
    const userIds = [];
    const userMap = new Map();
    if (!Number.isNaN(Number(kw))) {
      userIds.push(Number(kw));
    } else {
      const resp = await fetch(store.apiPath(`/admin/users?q=${encodeURIComponent(kw)}`), { headers: store.getAuthHeaders() });
      if (!resp.ok) {
        throw new Error('Name search requires admin permission.');
      }
      const users = await resp.json();
      users.forEach((u) => {
        userIds.push(u.user_id);
        userMap.set(u.user_id, u);
      });
    }
    if (!userIds.length) {
      searchError.value = 'No users found.';
      return;
    }
    const registrationLists = await Promise.all(
      userIds.map(async (uid) => {
        const r = await fetch(store.apiPath(`/registrations/user/${uid}`));
        if (!r.ok) return [];
        const rows = await r.json();
        return rows
          .filter((row) => row.status === 'registered')
          .map((row) => ({ ...row, user_id: uid, user_name: userMap.get(uid)?.name || row.user_name }));
      }),
    );
    searchResults.value = registrationLists.flat();
    if (!searchResults.value.length) {
      searchError.value = 'No registered entries found for this user.';
    }
  } catch (err) {
    searchError.value = err.message || 'Search failed';
  } finally {
    searchLoading.value = false;
  }
}

function clearSearch() {
  searchKeyword.value = '';
  searchResults.value = [];
  searchError.value = '';
}

function checkinFromResult(row) {
  performCheckin(row.user_id, row.session_id);
}

function startCamera() {
  navigator.mediaDevices?.getUserMedia({ video: { facingMode: 'environment' } })
    .then((stream) => {
      if (videoRef.value) {
        videoRef.value.srcObject = stream;
        videoRef.value.play?.();
      }
    })
    .catch(() => {});
}

onMounted(async () => {
  await ensureUser();
  await loadTodaySessions();
  await loadHistory();
  startCamera();
});
</script>

<style scoped>
.checkin-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 16px;
}

.card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04);
  padding: 16px;
}

.block {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.search-row {
  display: flex;
  gap: 8px;
}

.search-row input {
  flex: 1;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid #d1d5db;
}

.video-shell {
  background: #0f172a;
  border-radius: 12px;
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.results {
  width: 100%;
  border-collapse: collapse;
}

.results th,
.results td {
  text-align: left;
  padding: 10px;
  border-bottom: 1px solid #f1f5f9;
}

.results th {
  background: #f8fafc;
  font-weight: 600;
}

.actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.history {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.history li {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 10px;
  border: 1px solid #f1f5f9;
  border-radius: 8px;
  background: #f9fafb;
}

.pill {
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 12px;
  display: inline-block;
  text-transform: capitalize;
}

.pill-success {
  background: #ecfdf3;
  color: #0f9f6e;
}

.pill-error {
  background: #fef2f2;
  color: #b91c1c;
}

.message {
  font-weight: 600;
}

.meta {
  font-size: 12px;
  color: #6b7280;
}

.session-list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.session-list li {
  border: 1px solid #f1f5f9;
  border-radius: 10px;
  padding: 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.session-list li.active {
  border-color: #2563eb;
  box-shadow: 0 0 0 1px #2563eb33;
}

.session-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.session-actions {
  display: flex;
  gap: 8px;
}

button {
  padding: 10px 14px;
  border-radius: 8px;
  border: 1px solid #1f2937;
  background: #111827;
  color: #fff;
  cursor: pointer;
  transition: transform 0.1s ease, box-shadow 0.1s ease;
}

button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.1);
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

button.ghost {
  background: #f8fafc;
  color: #111827;
  border: 1px solid #e5e7eb;
}

.muted {
  color: #6b7280;
  font-size: 14px;
}

.error {
  color: #b91c1c;
}

@media (max-width: 960px) {
  .grid {
    grid-template-columns: 1fr;
  }

  .session-actions,
  .search-row,
  .actions {
    flex-wrap: wrap;
  }
}
</style>
