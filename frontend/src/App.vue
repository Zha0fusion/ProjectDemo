<template>
  <el-config-provider :namespace="'el'">
    <el-container>
      <el-header v-if="!hideHeader" height="64px" class="app-header">
        <div class="header-left">
          <h1>{{ store.state.appTitle }}</h1>
          <span v-if="store.state.currentUser" class="muted">Hello, {{ store.state.currentUser.name }} ({{ store.state.currentUser.role }})</span>
        </div>
        <div class="header-right">
          <template v-if="store.state.currentUser">
            <el-link v-if="store.isStaff.value" type="primary" @click="go('visitor')">Visitor Panel</el-link>
            <el-link v-if="store.isStaff.value" type="primary" @click="go('checkin')">Check-in Panel</el-link>
            <el-link v-if="store.isAdmin.value" type="primary" @click="go('admin')">Admin Panel</el-link>
            <el-button size="small" @click="logout">Logout</el-button>
          </template>
          <template v-else>
            <el-link type="primary" @click="go('auth')">Log in</el-link>
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
import { useRoute, useRouter } from 'vue-router';
import { useAppStore } from './stores/appStore';

const store = useAppStore();
const router = useRouter();
const route = useRoute();

const hideHeader = computed(() => route.name === 'scan');

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

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: #fff;
  color: #c4c7cc;
}
.header-left {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}
.muted {
  color: #bbc2ca;
}
.container {
  padding: 16px;
}
</style>
