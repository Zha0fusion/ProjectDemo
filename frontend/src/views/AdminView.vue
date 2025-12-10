<template>
  <section v-if="store.isAdmin.value">
    <el-tabs v-model="adminTab" class="content-tabs">
      <el-tab-pane label="活动管理" name="events" />
      <el-tab-pane label="人员管理" name="people" />
      <el-tab-pane label="用户管理" name="users" />
      <el-tab-pane label="分析&导出" name="analytics" />
      <el-tab-pane label="设置" name="settings" />
    </el-tabs>

    <div v-if="adminTab === 'events'" class="card">
      <div class="card-head">
        <h2>活动列表</h2>
        <el-button type="primary" size="small" @click="openCreateEvent">新建活动</el-button>
      </div>
      <el-table v-loading="!adminLoaded" :data="adminEvents" size="small" style="width: 100%">
        <el-table-column prop="eid" label="ID" width="70" />
        <el-table-column prop="title" label="标题" />
        <el-table-column prop="status" label="状态" width="120" />
        <el-table-column prop="allow_multi_session" label="多场次" width="90" :formatter="(r)=> r.allow_multi_session ? 'Yes' : 'No'" />
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-button size="small" @click="openEditEvent(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteEventRow(scope.row)">删除</el-button>
            <el-button size="small" @click="openTags(scope.row)">标签</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div v-if="adminTab === 'people'" class="card">
      <div class="card-head">
        <h3>人员检索与强制报名</h3>
        <el-input v-model="userSearch" placeholder="用户ID/姓名/邮箱" clearable style="max-width: 320px;" @change="searchUsers" />
      </div>
      <el-table :data="userResults" size="small" style="width: 100%; margin-bottom: 12px;">
        <el-table-column prop="user_id" label="ID" width="70" />
        <el-table-column prop="name" label="姓名" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="role" label="角色" width="90" />
        <el-table-column label="强制报名" width="280">
          <template #default="scope">
            <el-input-number v-model="forceSessionId" :min="1" size="small" placeholder="session_id" />
            <el-select v-model="forceStatus" size="small" style="width: 110px; margin: 0 6px;">
              <el-option label="registered" value="registered" />
              <el-option label="waiting" value="waiting" />
              <el-option label="cancelled" value="cancelled" />
            </el-select>
            <el-button size="small" type="primary" @click="forceRegister(scope.row.user_id)">执行</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-divider>观众群组</el-divider>
      <el-input v-model.number="groupEventId" placeholder="查看的活动ID" style="max-width: 200px;" />
      <el-button size="small" @click="loadGroupSummary">刷新分组统计</el-button>
      <el-table :data="groupSummary" size="small" style="margin-top: 8px;">
        <el-table-column prop="group_name" label="Group" />
        <el-table-column prop="member_count" label="人数" width="100" />
        <el-table-column label="成员" width="160">
          <template #default="scope">
            <el-button size="small" @click="loadGroupMembers(scope.row.group_id)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-table v-if="groupMembers.length" :data="groupMembers" size="small" style="margin-top: 10px;">
        <el-table-column prop="user_id" label="User" width="80" />
        <el-table-column prop="name" label="Name" />
        <el-table-column prop="email" label="Email" />
      </el-table>

      <div style="margin-top: 12px; display: flex; gap: 8px; align-items: center;">
        <el-input-number v-model.number="assignUserId" :min="1" placeholder="user_id" />
        <el-input-number v-model.number="assignGroupId" :min="1" placeholder="group_id" />
        <el-button size="small" type="primary" @click="assignGroup">分配分组</el-button>
      </div>
    </div>

    <div v-if="adminTab === 'users'" class="card">
      <div class="card-head">
        <h3>用户管理</h3>
        <el-input v-model="userSearch" placeholder="搜索用户" style="max-width: 260px;" @change="searchUsers" />
        <el-button size="small" type="primary" @click="createUser">新增访客</el-button>
      </div>
      <el-table :data="userResults" size="small">
        <el-table-column prop="user_id" label="ID" width="70" />
        <el-table-column prop="name" label="姓名" />
        <el-table-column prop="email" label="邮箱" />
        <el-table-column prop="role" label="角色" width="100" />
        <el-table-column label="操作" width="200">
          <template #default="scope">
            <el-select v-model="scope.row.role" size="small" style="width: 110px;" @change="(val)=>updateUserRole(scope.row, val)">
              <el-option label="visitor" value="visitor" />
              <el-option label="staff" value="staff" />
              <el-option label="admin" value="admin" />
            </el-select>
            <el-button size="small" type="danger" @click="deleteUser(scope.row.user_id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-divider>标签管理</el-divider>
      <div style="display: flex; gap: 8px; margin-bottom: 8px;">
        <el-input v-model="tagName" placeholder="新标签" style="max-width: 200px;" />
        <el-button size="small" type="primary" @click="createTag">创建</el-button>
      </div>
      <el-tag v-for="t in tags" :key="t.tag_id" closable @close="deleteTag(t.tag_id)" style="margin: 4px;">
        {{ t.tag_name }}
      </el-tag>
    </div>

    <div v-if="adminTab === 'analytics'" class="card">
      <h3>数据分析与导出</h3>
      <div style="display: flex; gap: 8px; margin-bottom: 10px; align-items: center;">
        <el-input-number v-model.number="analyticsEventId" :min="1" placeholder="event id" />
        <el-button size="small" type="primary" @click="loadEventOverview">加载概览</el-button>
        <el-button size="small" @click="exportCsv">导出CSV</el-button>
      </div>
      <pre class="muted" v-if="Object.keys(eventOverview).length">{{ JSON.stringify(eventOverview, null, 2) }}</pre>
    </div>

    <div v-if="adminTab === 'settings'" class="card">
      <h3>设置</h3>
      <el-form label-width="120px" style="max-width: 420px;">
        <el-form-item label="面板标题">
          <el-input v-model="store.state.appTitle" @change="store.persistTitle" />
        </el-form-item>
        <el-form-item label="主题色">
          <el-color-picker v-model="store.state.brandColor" show-alpha @change="store.applyBrandColor" />
        </el-form-item>
      </el-form>
    </div>

    <el-dialog v-model="eventDialogVisible" :title="isEditingEvent ? '编辑活动' : '新建活动'" width="720px">
      <el-form label-width="120px" :model="eventForm" :disabled="eventSaving">
        <el-form-item label="标题"><el-input v-model="eventForm.title" /></el-form-item>
        <el-form-item label="描述"><el-input type="textarea" v-model="eventForm.description" /></el-form-item>
        <el-form-item label="地点"><el-input v-model="eventForm.location" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="eventForm.status" style="width: 160px;">
            <el-option label="draft" value="draft" />
            <el-option label="published" value="published" />
            <el-option label="closed" value="closed" />
            <el-option label="archived" value="archived" />
          </el-select>
        </el-form-item>
        <el-form-item label="类型ID"><el-input-number v-model="eventForm.type_id" :min="1" /></el-form-item>
        <el-form-item label="封面URL"><el-input v-model="eventForm.image_url" /></el-form-item>
        <el-form-item label="允许多场次"><el-switch v-model="eventForm.allow_multi_session" /></el-form-item>
        <el-form-item label="标签">
          <el-select v-model="eventForm.tag_names" multiple filterable placeholder="选择或输入标签" style="width: 100%;">
            <el-option v-for="t in tags" :key="t.tag_id" :label="t.tag_name" :value="t.tag_name" />
          </el-select>
        </el-form-item>

        <template v-if="!isEditingEvent">
          <el-divider>场次</el-divider>
          <div v-for="(session, idx) in eventForm.sessions" :key="idx" class="session-edit">
            <el-date-picker v-model="session.start_time" type="datetime" placeholder="开始时间" style="width: 220px;" />
            <el-date-picker v-model="session.end_time" type="datetime" placeholder="结束时间" style="width: 220px;" />
            <el-input-number v-model="session.capacity" :min="1" label="capacity" />
            <el-input-number v-model="session.waiting_list_limit" :min="0" label="waitlist" />
            <el-button v-if="eventForm.sessions.length > 1" size="small" type="danger" @click="removeSessionRow(idx)">删除</el-button>
          </div>
          <el-button size="small" @click="addSessionRow">添加场次</el-button>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="eventDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="eventSaving" @click="submitEventForm">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="tagDialogVisible" title="更新标签" width="400px">
      <el-select v-model="tagEditSelection" multiple filterable style="width: 100%;" placeholder="选择标签">
        <el-option v-for="t in tags" :key="t.tag_id" :label="t.tag_name" :value="t.tag_name" />
      </el-select>
      <template #footer>
        <el-button @click="tagDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveTags">保存</el-button>
      </template>
    </el-dialog>
  </section>
  <section v-else class="card">需要管理员权限。</section>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue';
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
const forceSessionId = ref(null);
const forceStatus = ref('registered');

const groupEventId = ref(null);
const groupSummary = ref([]);
const groupMembers = ref([]);
const assignUserId = ref(null);
const assignGroupId = ref(null);

const analyticsEventId = ref(null);
const eventOverview = ref({});

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
      payload.sessions = eventForm.sessions;
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

async function forceRegister(userId) {
  if (!forceSessionId.value) {
    ElMessage.error('请输入 session_id');
    return;
  }
  const resp = await fetch(store.apiPath('/admin/registrations/force'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...store.getAuthHeaders() },
    body: JSON.stringify({ user_id: userId, session_id: forceSessionId.value, status: forceStatus.value }),
  });
  if (resp.ok) {
    ElMessage.success('已更新');
  } else {
    const data = await resp.json();
    ElMessage.error(data.message_en || '失败');
  }
}

async function loadGroupSummary() {
  if (!groupEventId.value) return;
  const resp = await fetch(store.apiPath(`/admin/events/${groupEventId.value}/groups/summary`), { headers: store.getAuthHeaders() });
  if (resp.ok) groupSummary.value = await resp.json();
}

async function loadGroupMembers(groupId) {
  const resp = await fetch(store.apiPath(`/admin/events/${groupEventId.value}/groups/${groupId}/members`), { headers: store.getAuthHeaders() });
  if (resp.ok) groupMembers.value = await resp.json();
}

async function assignGroup() {
  if (!assignUserId.value || !assignGroupId.value || !groupEventId.value) return;
  const resp = await fetch(store.apiPath(`/admin/events/${groupEventId.value}/groups/assign`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...store.getAuthHeaders() },
    body: JSON.stringify({ user_id: assignUserId.value, group_id: assignGroupId.value }),
  });
  if (resp.ok) {
    ElMessage.success('分配完成');
    loadGroupSummary();
  }
}

async function loadEventOverview() {
  if (!analyticsEventId.value) return;
  const resp = await fetch(store.apiPath(`/analytics/events/${analyticsEventId.value}/overview`), { headers: store.getAuthHeaders() });
  if (resp.ok) eventOverview.value = await resp.json();
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

onMounted(() => {
  loadAdminEvents();
  loadTags();
  searchUsers();
});
</script>
