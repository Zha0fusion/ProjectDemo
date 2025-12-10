<template>
  <el-config-provider :namespace="'el'">
    <el-container>
      <el-header height="60px" class="app-header">
        <div class="header-left">
          <h1 :style="{ color: headerTextColor }">{{ store.state.appTitle }}</h1>
          <span v-if="store.state.currentUser" class="muted">Hello, {{ store.state.currentUser.name }} ({{ store.state.currentUser.role }})</span>
        </div>
        <div class="header-right">
          <template v-if="store.state.currentUser">
            <el-link v-if="store.isStaff.value" type="primary" @click="go('visitor')">游客面板</el-link>
            <el-link v-if="store.isStaff.value" type="primary" @click="go('checkin')">签到面板</el-link>
            <el-link v-if="store.isAdmin.value" type="primary" @click="go('admin')">管理面板</el-link>
            <el-button size="small" @click="logout">Logout</el-button>
          </template>
          <template v-else>
            <el-link type="primary" @click="go('auth')">去登录</el-link>
            <span class="muted">Not logged in</span>
          </template>
        </div>
      </el-header>

      <el-main>
        <div class="container">
          <router-view />
        </div>
      </el-main>
    </el-container>
  </el-config-provider>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAppStore } from './stores/appStore';

const store = useAppStore();
const router = useRouter();
const headerTextColor = computed(() => (store.state.theme === 'dark' ? '#e5e7eb' : '#fff'));

function go(name) {
  router.push({ name });
}

function logout() {
  store.clearAuth();
  router.push({ name: 'auth' });
}

onMounted(() => {
  store.applyTheme(store.state.theme);
  store.applyBrandColor(store.state.brandColor);
  if (!store.state.currentUser && store.state.token) {
    store.fetchMe();
  }
});
</script>
