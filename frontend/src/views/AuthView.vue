<template>
  <section>
    <el-card style="max-width: 520px; margin: 24px auto;">
      <div class="card-head">
        <span class="card-title">{{ isRegister ? 'Create an account' : 'Login' }}</span>
        <el-button type="text" size="small" @click="toggleMode">
          {{ isRegister ? 'Already have an account? Login' : 'New here? Create one' }}
        </el-button>
      </div>
      <el-form v-if="!isRegister" label-width="90px">
        <el-form-item label="Email">
          <el-input v-model="loginForm.email" type="email" placeholder="email" />
        </el-form-item>
        <el-form-item label="Password">
          <el-input v-model="loginForm.password" type="password" placeholder="password" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="doLogin">Login</el-button>
        </el-form-item>
      </el-form>
      <el-form v-else label-width="90px">
        <el-form-item label="Name">
          <el-input v-model="registerForm.name" placeholder="name" />
        </el-form-item>
        <el-form-item label="Email">
          <el-input v-model="registerForm.email" type="email" placeholder="email" />
        </el-form-item>
        <el-form-item label="Password">
          <el-input v-model="registerForm.password" type="password" placeholder="password" show-password />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="doRegister">Register</el-button>
        </el-form-item>
      </el-form>
      <p class="muted" style="margin-top: 6px;">Sign up auto logs you in as visitor.</p>
    </el-card>
  </section>
</template>

<script setup>
import { reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import { ElMessage } from 'element-plus';
import { useAppStore } from '../stores/appStore';

const store = useAppStore();
const router = useRouter();
const isRegister = ref(false);

const loginForm = reactive({ email: '', password: '' });
const registerForm = reactive({ name: '', email: '', password: '' });

function toggleMode() {
  isRegister.value = !isRegister.value;
}

async function doLogin() {
  try {
    const resp = await fetch(store.apiPath('/auth/login'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(loginForm),
    });
    const data = await resp.json();
    if (!resp.ok) {
      ElMessage.error(data.message_en || data.message_zh || 'Login failed');
      return;
    }
    store.setToken(data.token);
    store.setUser(data.user);
    ElMessage.success(data.message_en || 'Login successful');
    router.push({ name: data.user.role === 'admin' ? 'admin' : 'visitor' });
  } catch (e) {
    ElMessage.error('Network error when logging in');
  }
}

async function doRegister() {
  try {
    const resp = await fetch(store.apiPath('/auth/register'), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(registerForm),
    });
    const data = await resp.json();
    if (!resp.ok) {
      ElMessage.error(data.message_en || data.message_zh || 'Registration failed');
      return;
    }
    store.setToken(data.token);
    store.setUser(data.user);
    ElMessage.success(data.message_en || 'Registration successful');
    isRegister.value = false;
    router.push({ name: 'visitor' });
  } catch (e) {
    ElMessage.error('Network error when registering');
  }
}
</script>
