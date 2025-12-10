<template>
  <section v-if="hasAccess" class="card">
    <div class="card-head">
      <h2>签到面板</h2>
      <span class="muted">列出今日场次，扫码签到</span>
    </div>
    <el-row :gutter="16">
      <el-col :span="10">
        <h4>当前签到信息</h4>
        <div class="card" style="padding: 12px;">
          <template v-if="currentResult">
            <div><strong>用户:</strong> {{ currentResult.user_name || currentResult.user_id || '-' }}</div>
            <div><strong>状态:</strong> {{ currentResult.status || '已处理' }}</div>
            <div class="muted">{{ currentResult.message || '已更新签到' }}</div>
            <div v-if="currentResult.session_id" class="muted">Session: {{ currentResult.session_id }}</div>
          </template>
          <template v-else>
            <div class="muted">等待扫码或手动输入...</div>
          </template>
        </div>

        <div class="card" style="padding: 12px; margin-top: 12px;">
          <h4>扫码/手动输入</h4>
          <el-input
            v-model="qrPayload"
            type="textarea"
            :rows="3"
            placeholder='粘贴二维码内容，形如 {"user_id":1,"session_id":2}'
            @keyup.enter.native="handleQrPayload"
          />
          <div class="form-row" style="margin-top: 8px;">
            <el-input-number v-model.number="manualUserId" :min="1" placeholder="user id" />
            <el-button type="primary" size="small" :loading="checkinBusy" @click="doManualCheckin">手动签到</el-button>
            <el-button size="small" :loading="checkinBusy" @click="handleQrPayload">处理二维码</el-button>
          </div>
          <small class="muted">未提供 session_id 时默认使用当前选中的场次。</small>
        </div>
      </el-col>

      <el-col :span="14">
        <h4>今日场次</h4>
        <el-skeleton v-if="loadingSessions" rows="4" animated />
        <div v-else>
          <div v-if="!todaySessions.length" class="muted">今日暂无场次。</div>
          <el-timeline v-else>
            <el-timeline-item
              v-for="s in todaySessions"
              :key="s.session_id"
              :timestamp="formatDateTime(s.start_time)"
              :color="s.session_id === activeSessionId ? store.state.brandColor : '#dcdfe6'"
            >
              <div style="display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap;">
                <div>
                  <strong>{{ s.event_title }}</strong>
                  <div class="muted">{{ s.session_id }} · {{ s.status }} · {{ s.current_registered || 0 }}/{{ s.capacity }}</div>
                </div>
                <div>
                  <el-button size="small" type="primary" @click="setActiveSession(s)">进入签到</el-button>
                </div>
              </div>
            </el-timeline-item>
          </el-timeline>
        </div>

        <div class="card" style="padding: 12px; margin-top: 12px;">
          <h4>摄像头预览</h4>
          <video ref="videoRef" autoplay playsinline muted style="width: 100%; border-radius: 8px; background: #000;" />
          <p class="muted">摄像头用于扫码引导（仅预览，无解析）。</p>
        </div>
      </el-col>
    </el-row>
  </section>
  <section v-else class="card">需要工作人员或管理员权限。</section>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { useAppStore } from '../stores/appStore';

const store = useAppStore();
const router = useRouter();
const hasAccess = computed(() => store.isStaff.value);

const loadingSessions = ref(false);
const todaySessions = ref([]);
const activeSessionId = ref(null);
const currentResult = ref(null);
const checkinBusy = ref(false);
const qrPayload = ref('');

const manualUserId = ref(null);
const videoRef = ref(null);

function isToday(val) {
  if (!val) return false;
  const d = new Date(val);
  const now = new Date();
  return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate();
}

function formatDateTime(val) {
  if (!val) return '';
  return new Date(val).toLocaleString();
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
    if (!resp.ok) {
      throw new Error('加载场次失败');
    }
    todaySessions.value = await resp.json();
    todaySessions.value.sort((a, b) => new Date(a.start_time) - new Date(b.start_time));
    if (todaySessions.value.length) {
      activeSessionId.value = todaySessions.value[0].session_id;
    }
  } catch (err) {
    todaySessions.value = [];
    ElMessage.error(err.message || '无法获取场次');
  } finally {
    loadingSessions.value = false;
  }
}

function setActiveSession(session) {
  activeSessionId.value = session.session_id;
  currentResult.value = null;
  ElMessage.success(`已切换到场次 #${session.session_id}`);
}

async function performCheckin(userId, sessionId) {
  if (!userId) {
    ElMessage.error('缺少 user_id');
    return;
  }
  const sid = sessionId || activeSessionId.value;
  if (!sid) {
    ElMessage.error('请先选择场次');
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
    if (resp.ok) {
      currentResult.value = {
        user_id: userId,
        session_id: sid,
        status: data.status || 'checked_in',
        message: data.message_en || data.message_zh || 'Checked in',
        user_name: data.user_name,
      };
      ElMessage.success(currentResult.value.message);
    } else {
      currentResult.value = {
        user_id: userId,
        session_id: sid,
        status: 'failed',
        message: data.message_en || data.message_zh || 'Failed',
      };
      ElMessage.error(currentResult.value.message);
    }
  } finally {
    checkinBusy.value = false;
  }
}

async function handleQrPayload() {
  if (!qrPayload.value && !manualUserId.value) {
    ElMessage.error('请输入二维码内容或手动 user_id');
    return;
  }
  let payloadUserId = manualUserId.value || null;
  let payloadSessionId = null;
  if (qrPayload.value) {
    try {
      const parsed = JSON.parse(qrPayload.value);
      payloadUserId = parsed.user_id || payloadUserId;
      payloadSessionId = parsed.session_id || payloadSessionId;
    } catch (e) {
      ElMessage.error('二维码内容不是有效 JSON');
      return;
    }
  }
  await performCheckin(payloadUserId, payloadSessionId);
}

async function doManualCheckin() {
  await performCheckin(manualUserId.value, activeSessionId.value);
}

function startCamera() {
  navigator.mediaDevices?.getUserMedia({ video: true }).then((stream) => {
    if (videoRef.value) {
      videoRef.value.srcObject = stream;
    }
  }).catch(() => {});
}

onMounted(async () => {
  await ensureUser();
  await loadTodaySessions();
  startCamera();
});
</script>
