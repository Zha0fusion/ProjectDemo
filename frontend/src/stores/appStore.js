import { computed, reactive } from 'vue';

const state = reactive({
  token: localStorage.getItem('jwt_token') || null,
  currentUser: null,
  theme: localStorage.getItem('theme') || 'light',
  appTitle: localStorage.getItem('app_title') || 'SDSC5003 Event Registration System',
  brandColor: localStorage.getItem('brand_color') || '#409EFF',
});

const apiPath = (p) => `/api${p}`;

function setToken(token) {
  state.token = token;
  if (token) localStorage.setItem('jwt_token', token);
  else localStorage.removeItem('jwt_token');
}

function setUser(user) {
  state.currentUser = user;
}

function clearAuth() {
  setToken(null);
  setUser(null);
}

function applyTheme(val) {
  const next = val || state.theme || 'light';
  state.theme = next;
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('theme', next);
}

function applyBrandColor(val) {
  const color = val || state.brandColor;
  state.brandColor = color;
  document.documentElement.style.setProperty('--el-color-primary', color);
  localStorage.setItem('brand_color', color);
}

function persistTitle() {
  localStorage.setItem('app_title', state.appTitle);
}

function getAuthHeaders() {
  return state.token ? { Authorization: `Bearer ${state.token}` } : {};
}

async function fetchMe() {
  if (!state.token) return null;
  const resp = await fetch(apiPath('/auth/me'), { headers: getAuthHeaders() });
  if (resp.ok) {
    const user = await resp.json();
    setUser(user);
    return user;
  }
  clearAuth();
  return null;
}

export function useAppStore() {
  const isStaff = computed(() => state.currentUser && (state.currentUser.role === 'staff' || state.currentUser.role === 'admin'));
  const isAdmin = computed(() => state.currentUser && state.currentUser.role === 'admin');

  return {
    state,
    isStaff,
    isAdmin,
    apiPath,
    setToken,
    setUser,
    clearAuth,
    applyTheme,
    applyBrandColor,
    persistTitle,
    getAuthHeaders,
    fetchMe,
  };
}
