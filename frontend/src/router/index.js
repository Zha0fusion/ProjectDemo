import { createRouter, createWebHistory } from 'vue-router';
import AuthView from '../views/AuthView.vue';
import VisitorView from '../views/VisitorView.vue';
import AdminView from '../views/AdminView.vue';
import CheckinView from '../views/CheckinView.vue';
import { useAppStore } from '../stores/appStore';

const routes = [
  { path: '/', redirect: '/auth' },
  { path: '/auth', name: 'auth', component: AuthView },
  { path: '/visitor', name: 'visitor', component: VisitorView },
  { path: '/admin', name: 'admin', component: AdminView, meta: { role: 'admin' } },
  { path: '/checkin', name: 'checkin', component: CheckinView, meta: { role: 'staff' } },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach(async (to, _from, next) =>
  {
    const store = useAppStore();
    const needsAuth = to.name !== 'auth';
    if (!store.state.currentUser && store.state.token) {
      await store.fetchMe();
    }
    if (needsAuth && !store.state.currentUser) {
      return next({ name: 'auth' });
    }
    if (to.meta.role === 'admin' && !(store.state.currentUser && store.state.currentUser.role === 'admin')) {
      return next({ name: 'visitor' });
    }
    if (to.meta.role === 'staff' && !(store.isStaff.value)) {
      return next({ name: 'visitor' });
    }
    return next();
  });

export default router;
