<template>
  <section v-if="store.isAdmin.value">
    <el-tabs v-model="adminTab" class="content-tabs">
      <el-tab-pane label="Events" name="events" />
      <el-tab-pane label="Users" name="users" />
      <el-tab-pane label="Analytics & Export" name="analytics" />
      <el-tab-pane label="Settings" name="settings" />
    </el-tabs>

    <div v-if="adminTab === 'events'" class="card">
      <div class="card-head" style="gap: 8px; flex-wrap: wrap;">
        <h2>Event List</h2>
        <el-input v-model="adminEventKeyword" size="small" placeholder="Search by name/ID" style="max-width: 220px;" />
        <el-button type="primary" size="small" @click="openCreateEvent">New Event</el-button>
      </div>
      <el-table v-loading="!adminLoaded" :data="filteredAdminEvents" size="small" style="width: 100%">
        <el-table-column prop="eid" label="ID" width="70" />
        <el-table-column prop="title" label="Title" />
        <el-table-column prop="status" label="Status" width="120" />
        <el-table-column prop="allow_multi_session" label="Multi-session" width="110" :formatter="(r)=> r.allow_multi_session ? 'Yes' : 'No'" />
        <el-table-column label="Actions" width="260">
          <template #default="scope">
            <el-button size="small" @click="openEditEvent(scope.row)">Edit</el-button>
            <el-button size="small" type="primary" @click="openPeople(scope.row)">People</el-button>
            <el-button size="small" type="danger" @click="deleteEventRow(scope.row)">Delete</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div v-if="adminTab === 'users'" class="card">
      <div class="card-head">
        <h3>User Management</h3>
        <el-input v-model="userSearch" placeholder="Search users" style="max-width: 260px;" @change="searchUsers" />
        <el-button size="small" type="primary" @click="createUser">Add visitor</el-button>
      </div>
      <el-table :data="userResults" size="small">
        <el-table-column prop="user_id" label="ID" width="70" />
        <el-table-column prop="name" label="Name" />
        <el-table-column prop="email" label="Email" />
        <el-table-column prop="role" label="Role" width="100" />
        <el-table-column label="Actions" width="200">
          <template #default="scope">
            <el-select v-model="scope.row.role" size="small" style="width: 110px;" @change="(val)=>updateUserRole(scope.row, val)">
              <el-option label="visitor" value="visitor" />
              <el-option label="staff" value="staff" />
              <el-option label="admin" value="admin" />
            </el-select>
            <el-button size="small" type="danger" @click="deleteUser(scope.row.user_id)">Delete</el-button>
          </template>
        </el-table-column>
      </el-table>

    </div>

    <div v-if="adminTab === 'analytics'" class="card">
      <h3>Analytics & Export</h3>

      <div class="summary-row">
        <el-statistic v-for="item in analyticsSummary" :key="item.label" :title="item.label" :value="item.value" />
      </div>

      <div style="display: flex; gap: 8px; margin: 10px 0; align-items: center; flex-wrap: wrap;">
        <el-input v-model="analyticsEventId" placeholder="event id" style="max-width: 200px;" />
        <el-button size="small" type="primary" @click="loadEventOverview">Load overview</el-button>
      </div>

      <div class="card" style="padding: 12px; margin-bottom: 12px;">
        <div class="card-head" style="margin-bottom: 8px;">
          <strong>Recent events (5 per page)</strong>
          <span class="muted">Sorted by start time desc</span>
        </div>
        <el-table :data="recentEventsPage" size="small" stripe>
          <el-table-column prop="eid" label="ID" width="70" />
          <el-table-column prop="title" label="Title" />
          <el-table-column prop="status" label="Status" width="120" />
          <el-table-column prop="start_time" label="Start" :formatter="formatDateCell" />
          <el-table-column label="Actions" width="140">
            <template #default="scope">
              <el-button size="small" type="primary" @click="loadOverviewFromRecent(scope.row)">Load overview</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div style="display: flex; justify-content: flex-end; margin-top: 8px;">
          <el-pagination
            small
            layout="prev, pager, next"
            :page-size="recentPageSize"
            :total="adminEvents.length"
            :current-page="recentPage"
            @current-change="(p) => { recentPage = p; }"
          />
        </div>
      </div>

      <el-table v-if="analyticsRows.length" :data="analyticsRows" stripe size="small">
        <el-table-column prop="key" label="Metric" width="200" />
        <el-table-column prop="value" label="Value" />
      </el-table>
      <div v-else class="muted">No data loaded yet.</div>

      <div style="display: flex; justify-content: flex-end; margin-top: 12px;">
        <el-button size="small" @click="exportCsv">Export CSV</el-button>
      </div>

      <div v-if="analyticsRegistrations.length" class="card" style="padding: 12px; margin-top: 12px;">
        <div class="card-head" style="margin-bottom: 8px;">
          <strong>Registration details</strong>
          <span class="muted">Includes user, session, group, register/check-in time</span>
        </div>
        <el-table :data="analyticsRegistrations" size="small" stripe height="360">
          <el-table-column prop="user_id" label="User" width="70" />
          <el-table-column prop="user_name" label="Name" />
          <el-table-column prop="user_role" label="Role" width="90" />
          <el-table-column prop="status" label="Status" width="100" />
          <el-table-column prop="session_id" label="Session" width="80" />
          <el-table-column prop="session_start" label="Start" :formatter="formatDateCell" />
          <el-table-column prop="session_end" label="End" :formatter="formatDateCell" />
          <el-table-column prop="register_time" label="Registered at" :formatter="formatDateCell" />
          <el-table-column prop="checkin_time" label="Check-in at" :formatter="formatDateCell" />
          <el-table-column prop="group_name" label="Group" width="120" />
        </el-table>
      </div>
    </div>

    <div v-if="adminTab === 'settings'" class="card">
      <h3>Settings</h3>
      <el-form label-width="120px" style="max-width: 420px;">
        <el-form-item label="Panel title">
          <el-input v-model="store.state.appTitle" @change="store.persistTitle" />
        </el-form-item>
        <el-form-item label="Brand color">
          <el-color-picker v-model="store.state.brandColor" show-alpha @change="store.applyBrandColor" />
        </el-form-item>
      </el-form>
    </div>

    <el-dialog v-model="eventDialogVisible" :title="isEditingEvent ? 'Edit event' : 'New event'" width="720px" class="event-dialog">
      <el-form label-width="120px" :model="eventForm" :disabled="eventSaving">
        <el-form-item label="Title"><el-input v-model="eventForm.title" /></el-form-item>
        <el-form-item label="Description"><el-input type="textarea" v-model="eventForm.description" /></el-form-item>
        <el-form-item label="Location"><el-input v-model="eventForm.location" /></el-form-item>
        <el-form-item label="Status">
          <el-select v-model="eventForm.status" style="width: 160px;">
            <el-option label="draft" value="draft" />
            <el-option label="published" value="published" />
            <el-option label="closed" value="closed" />
            <el-option label="archived" value="archived" />
          </el-select>
        </el-form-item>
        <el-form-item label="Type ID"><el-input-number v-model="eventForm.type_id" :min="1" /></el-form-item>
        <el-form-item label="Cover URL"><el-input v-model="eventForm.image_url" /></el-form-item>
        <el-form-item label="Allow multi-session"><el-switch v-model="eventForm.allow_multi_session" /></el-form-item>
        <el-form-item label="Tags">
          <el-select v-model="eventForm.tag_names" multiple filterable placeholder="Select or enter tags" style="width: 100%;">
            <el-option v-for="t in tags" :key="t.tag_id" :label="t.tag_name" :value="t.tag_name" />
          </el-select>
        </el-form-item>

        <template v-if="!isEditingEvent">
          <el-divider>Sessions</el-divider>
          <div v-for="(session, idx) in eventForm.sessions" :key="idx" class="session-edit">
            <el-date-picker v-model="session.start_time" type="datetime" placeholder="Start time" style="width: 220px;" />
            <el-date-picker v-model="session.end_time" type="datetime" placeholder="End time" style="width: 220px;" />
            <el-input-number v-model="session.capacity" :min="1" label="capacity" />
            <el-input-number v-model="session.waiting_list_limit" :min="0" label="waitlist" />
            <el-button v-if="eventForm.sessions.length > 1" size="small" type="danger" @click="removeSessionRow(idx)">Delete</el-button>
          </div>
          <el-button size="small" @click="addSessionRow">Add session</el-button>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="eventDialogVisible = false">Cancel</el-button>
        <el-button type="primary" :loading="eventSaving" @click="submitEventForm">Save</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="tagDialogVisible" title="Update tags" width="400px">
      <el-select v-model="tagEditSelection" multiple filterable style="width: 100%;" placeholder="Select tags">
        <el-option v-for="t in tags" :key="t.tag_id" :label="t.tag_name" :value="t.tag_name" />
      </el-select>
      <template #footer>
        <el-button @click="tagDialogVisible = false">Cancel</el-button>
        <el-button type="primary" @click="saveTags">Save</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="groupDialogVisible" :title="`People & groups - ${groupModalEventTitle}`" width="840px">
      <div class="card" style="padding: 12px; margin-bottom: 12px;">
        <div class="card-head">
          <strong>Groups</strong>
          <div style="display: flex; gap: 8px; align-items: center;">
            <el-input v-model="newGroupName" size="small" placeholder="New group name" style="max-width: 200px;" />
            <el-button size="small" type="primary" @click="createGroup">Create group</el-button>
            <el-button size="small" @click="loadGroupSummary">Refresh</el-button>
          </div>
        </div>
        <el-table :data="groupSummary" size="small">
          <el-table-column prop="group_id" label="ID" width="60" />
          <el-table-column prop="group_name" label="Group name">
            <template #default="scope">
              <el-input v-model="scope.row.group_name" size="small" @change="() => renameGroup(scope.row)" />
            </template>
          </el-table-column>
          <el-table-column prop="member_count" label="Members" width="90" />
        </el-table>
      </div>

      <div class="card" style="padding: 12px; margin-bottom: 12px;">
        <div class="card-head">
          <strong>Members</strong>
          <span class="muted">Current registrations and groups</span>
        </div>
        <el-table :data="groupMembersFlat" size="small" height="260">
          <el-table-column prop="user_id" label="User" width="70" />
          <el-table-column prop="name" label="Name" />
          <el-table-column prop="email" label="Email" />
          <el-table-column prop="session_id" label="Session" width="80" />
          <el-table-column prop="start_time" label="Start" :formatter="formatDateCell" />
          <el-table-column prop="register_time" label="Registered at" :formatter="formatDateCell" />
          <el-table-column prop="status" label="Status" width="90" />
          <el-table-column label="Group" width="220">
            <template #default="scope">
              <el-select
                v-model="scope.row.group_id"
                placeholder="Select group"
                size="small"
                style="width: 180px;"
                @change="(val) => assignGroupInline(scope.row.user_id, val)"
              >
                <el-option :label="'Unassigned'" :value="null" />
                <el-option v-for="g in groupSummary" :key="g.group_id" :label="g.group_name" :value="g.group_id" />
              </el-select>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-dialog>
  </section>
  <section v-else class="card">Admin access required.</section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { useAppStore } from '../stores/appStore';

const store = useAppStore();
const adminTab = ref('events');

const adminEvents = ref([]);
const adminLoaded = ref(false);
const eventDialogVisible = ref(false);
const isEditingEvent = ref(false);
const eventSaving = ref(false);
const tags = ref([]);
const tagDialogVisible = ref(false);
const tagEditSelection = ref([]);

const eventForm = reactive({
  eid: null,
  title: '',
  description: '',
  location: '',
  status: 'draft',
  type_id: 1,
  image_url: '',
  allow_multi_session: false,
  tag_names: [],
  sessions: [
    { start_time: '', end_time: '', capacity: 50, waiting_list_limit: 0 },
  ],
});

const userSearch = ref('');
const userResults = ref([]);

const adminEventKeyword = ref('');
const filteredAdminEvents = computed(() => adminEvents.value.filter((ev) => {
  const kw = adminEventKeyword.value.toLowerCase();
  if (!kw) return true;
  return `${ev.eid}`.includes(kw) || (ev.title || '').toLowerCase().includes(kw);
}));

const groupEventId = ref(null);
const groupSummary = ref([]);
const groupMembers = ref([]);
const groupMembersFlat = ref([]);
const newGroupName = ref('');
const groupDialogVisible = ref(false);
const groupModalEventTitle = ref('');

const analyticsEventId = ref('');
const eventOverview = ref({});
const analyticsRows = computed(() => Object.entries(eventOverview.value || {}).map(([key, value]) => ({ key, value })));
const analyticsRegistrations = computed(() => eventOverview.value?.registrations || []);
const analyticsSummary = computed(() => {
  const total = adminEvents.value.length;
  const published = adminEvents.value.filter((e) => e.status === 'published').length;
  const draft = adminEvents.value.filter((e) => e.status === 'draft').length;
  return [
      { label: 'Total events', value: total },
      { label: 'Published', value: published },
      { label: 'Draft/Other', value: Math.max(total - published, 0) },
  ];
});
const recentPage = ref(1);
const recentPageSize = 5;
const recentEventsSorted = computed(() => {
  const clone = [...adminEvents.value];
  return clone.sort((a, b) => {
    const aTime = new Date(a.start_time || a.created_at || 0).getTime();
    const bTime = new Date(b.start_time || b.created_at || 0).getTime();
    if (Number.isNaN(aTime) && Number.isNaN(bTime)) return (b.eid || 0) - (a.eid || 0);
    if (Number.isNaN(aTime)) return 1;
    if (Number.isNaN(bTime)) return -1;
    return bTime - aTime;
  });
});
const recentEventsPage = computed(() => {
  const start = (recentPage.value - 1) * recentPageSize;
  return recentEventsSorted.value.slice(start, start + recentPageSize);
});

watch(adminEvents, () => {
  recentPage.value = 1;
});

const tagName = ref('');

function resetEventForm() {
  Object.assign(eventForm, {
    eid: null,
    title: '',
    description: '',
    location: '',
    status: 'draft',
    type_id: 1,
    image_url: '',
    allow_multi_session: false,
    tag_names: [],
    sessions: [{ start_time: '', end_time: '', capacity: 50, waiting_list_limit: 0 }],
  });
}

function addSessionRow() {
  eventForm.sessions.push({ start_time: '', end_time: '', capacity: 50, waiting_list_limit: 0 });
}

function removeSessionRow(idx) {
  eventForm.sessions.splice(idx, 1);
}

async function loadAdminEvents() {
  adminLoaded.value = false;
  try {
    const resp = await fetch(store.apiPath('/events/manage'), { headers: store.getAuthHeaders() });
    if (resp.ok) adminEvents.value = await resp.json();
  } finally {
    adminLoaded.value = true;
  }
}

function openCreateEvent() {
  resetEventForm();
  isEditingEvent.value = false;
  eventDialogVisible.value = true;
}

function openEditEvent(row) {
  resetEventForm();
  isEditingEvent.value = true;
  Object.assign(eventForm, {
    eid: row.eid,
    title: row.title,
    description: row.description,
    location: row.location,
    status: row.status,
    type_id: row.type_id,
    image_url: row.image_url,
    allow_multi_session: !!row.allow_multi_session,
  });
  tagEditSelection.value = [];
  eventDialogVisible.value = true;
}

function openTags(row) {
  isEditingEvent.value = true;
  eventForm.eid = row.eid;
  tagEditSelection.value = [];
  tagDialogVisible.value = true;
}

function openPeople(row) {
  groupEventId.value = row.eid;
  groupModalEventTitle.value = row.title;
  groupDialogVisible.value = true;
  groupMembersFlat.value = [];
  loadGroupSummary();
  loadEventMembers();
}

async function submitEventForm() {
  eventSaving.value = true;
  try {
    const payload = {
      title: eventForm.title,
      description: eventForm.description,
      location: eventForm.location,
      status: eventForm.status,
      type_id: eventForm.type_id,
      image_url: eventForm.image_url,
      allow_multi_session: eventForm.allow_multi_session,
      tag_names: eventForm.tag_names,
    };
    if (isEditingEvent.value && eventForm.eid) {
      const resp = await fetch(store.apiPath(`/events/${eventForm.eid}`), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json', ...store.getAuthHeaders() },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) {
        ElMessage.error(data.message_en || 'Update failed');
        return;
      }
      ElMessage.success('Updated');
    } else {
      payload.sessions = eventForm.sessions.map((session) => ({
        ...session,
        start_time: toMySQLDateTime(session.start_time),
        end_time: toMySQLDateTime(session.end_time),
      }));
      const resp = await fetch(store.apiPath('/events/'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...store.getAuthHeaders() },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) {
        ElMessage.error(data.message_en || 'Create failed');
        return;
      }
      ElMessage.success('Created');
    }
    eventDialogVisible.value = false;
    resetEventForm();
    loadAdminEvents();
  } finally {
    eventSaving.value = false;
  }
}

async function deleteEventRow(row) {
  const ok = confirm(`Delete event ${row.title}?`);
  if (!ok) return;
  const resp = await fetch(store.apiPath(`/events/${row.eid}`), { method: 'DELETE', headers: store.getAuthHeaders() });
  if (resp.ok) {
    ElMessage.success('Deleted');
    loadAdminEvents();
  }
}

async function loadTags() {
  const resp = await fetch(store.apiPath('/admin/tags'), { headers: store.getAuthHeaders() });
  if (resp.ok) tags.value = await resp.json();
}

async function saveTags() {
  if (!eventForm.eid) return;
  const resp = await fetch(store.apiPath(`/events/${eventForm.eid}/tags`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...store.getAuthHeaders() },
    body: JSON.stringify({ tag_names: tagEditSelection.value }),
  });
  if (resp.ok) {
    ElMessage.success('Tags updated');
    tagDialogVisible.value = false;
    loadTags();
  }
}

async function createTag() {
  if (!tagName.value) return;
  const resp = await fetch(store.apiPath('/admin/tags'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...store.getAuthHeaders() },
    body: JSON.stringify({ tag_name: tagName.value }),
  });
  if (resp.ok) {
    tagName.value = '';
    loadTags();
  }
}

async function deleteTag(id) {
  const resp = await fetch(store.apiPath(`/admin/tags/${id}`), { method: 'DELETE', headers: store.getAuthHeaders() });
  if (resp.ok) loadTags();
}

async function searchUsers() {
  const q = userSearch.value || '';
  const resp = await fetch(store.apiPath(`/admin/users?q=${encodeURIComponent(q)}`), { headers: store.getAuthHeaders() });
  if (resp.ok) userResults.value = await resp.json();
}

async function createUser() {
  const resp = await fetch(store.apiPath('/admin/users'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...store.getAuthHeaders() },
    body: JSON.stringify({ name: 'New User', email: `user${Date.now()}@example.com`, password: 'password', role: 'visitor' }),
  });
  if (resp.ok) searchUsers();
}

async function updateUserRole(row, role) {
  const resp = await fetch(store.apiPath(`/admin/users/${row.user_id}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...store.getAuthHeaders() },
    body: JSON.stringify({ role }),
  });
  if (!resp.ok) ElMessage.error('Update failed');
}

async function deleteUser(userId) {
  const resp = await fetch(store.apiPath(`/admin/users/${userId}`), { method: 'DELETE', headers: store.getAuthHeaders() });
  if (resp.ok) searchUsers();
}

async function loadGroupSummary() {
  if (!groupEventId.value) return;
  const resp = await fetch(store.apiPath(`/admin/events/${groupEventId.value}/groups/summary`), { headers: store.getAuthHeaders() });
  if (resp.ok) {
    groupSummary.value = await resp.json();
  }
}

async function loadGroupMembers(groupId) {
  const resp = await fetch(store.apiPath(`/admin/events/${groupEventId.value}/groups/${groupId}/members`), { headers: store.getAuthHeaders() });
  if (resp.ok) groupMembers.value = await resp.json();
}

async function loadEventMembers() {
  if (!groupEventId.value) return;
  const resp = await fetch(store.apiPath(`/admin/events/${groupEventId.value}/members`), { headers: store.getAuthHeaders() });
  if (resp.ok) {
    const rows = await resp.json();
    groupMembersFlat.value = rows.map((row) => ({
      ...row,
      group_name: row.group_name || 'Unassigned',
    }));
  }
}

async function assignGroupInline(userId, groupId) {
  if (!groupEventId.value) return;
  const resp = await fetch(store.apiPath(`/admin/events/${groupEventId.value}/groups/assign`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...store.getAuthHeaders() },
    body: JSON.stringify({ user_id: userId, group_id: groupId || null }),
  });
  if (resp.ok) {
    ElMessage.success('Assignment completed');
    loadGroupSummary();
    loadEventMembers();
  }
}

async function createGroup() {
  if (!groupEventId.value || !newGroupName.value) return;
  const resp = await fetch(store.apiPath(`/admin/events/${groupEventId.value}/groups`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...store.getAuthHeaders() },
    body: JSON.stringify({ group_name: newGroupName.value }),
  });
  if (resp.ok) {
    ElMessage.success('Group created');
    newGroupName.value = '';
    loadGroupSummary();
  }
}

async function renameGroup(group) {
  if (!groupEventId.value || !group.group_id) return;
  const resp = await fetch(store.apiPath(`/admin/events/${groupEventId.value}/groups/${group.group_id}`), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json', ...store.getAuthHeaders() },
    body: JSON.stringify({ group_name: group.group_name }),
  });
  if (resp.ok) {
    ElMessage.success('Group updated');
    loadGroupSummary();
  }
}

async function loadEventOverview() {
  if (!analyticsEventId.value) return;
  const url = store.apiPath(`/analytics/events/${analyticsEventId.value}/overview`);
  const resp = await fetch(url, { headers: store.getAuthHeaders() });
  if (resp.ok) eventOverview.value = await resp.json();
}

function loadOverviewFromRecent(row) {
  analyticsEventId.value = row.eid;
  loadEventOverview();
}

async function exportCsv() {
  if (!analyticsEventId.value) return;
  const resp = await fetch(store.apiPath(`/admin/events/${analyticsEventId.value}/registrations/export`), { headers: store.getAuthHeaders() });
  if (!resp.ok) return;
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `event_${analyticsEventId.value}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

function toDateParam(val) {
  if (!val) return '';
  const d = new Date(val);
  if (Number.isNaN(d.getTime())) return '';
  return d.toISOString().split('T')[0];
}

function formatDateCell(row) {
  const raw = row.start_time || row.created_at;
  if (!raw) return '';
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw;
  return d.toLocaleString();
}

function toMySQLDateTime(val) {
  if (!val) return null;
  const d = new Date(val);
  if (Number.isNaN(d.getTime())) return null;
  const pad = (n) => n.toString().padStart(2, '0');
  const year = d.getFullYear();
  const month = pad(d.getMonth() + 1);
  const day = pad(d.getDate());
  const hours = pad(d.getHours());
  const minutes = pad(d.getMinutes());
  const seconds = pad(d.getSeconds());
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

onMounted(() => {
  loadAdminEvents();
  loadTags();
  searchUsers();
});
</script>

<style scoped>
:deep(.event-dialog .el-dialog__header) {
  background: transparent;
}
</style>
