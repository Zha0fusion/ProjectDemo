<template>
  
  签到
</template>

<script setup>
import { computed, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { useAppStore } from '../stores/appStore';

const store = useAppStore();
const router = useRouter();
const hasAccess = computed(() => store.isStaff.value);
const checkinSessionId = ref(null);
const checkinList = ref([]);
const manualUserId = ref(null);
const videoRef = ref(null);

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

async function loadCheckinList() {
  if (!checkinSessionId.value) return;
  const resp = await fetch(store.apiPath(`/registrations/session/${checkinSessionId.value}`), { headers: store.getAuthHeaders() });
  if (resp.ok) checkinList.value = await resp.json();
}

async function doManualCheckin() {
  if (!manualUserId.value || !checkinSessionId.value) return;
  const resp = await fetch(store.apiPath('/checkin/'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...store.getAuthHeaders() },
    body: JSON.stringify({ user_id: manualUserId.value, session_id: checkinSessionId.value }),
  });
  const data = await resp.json();
  if (resp.ok) {
    ElMessage.success(data.message_en || 'Checked in');
    loadCheckinList();
  } else {
    ElMessage.error(data.message_en || 'Failed');
  }
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
  startCamera();
});
</script>
