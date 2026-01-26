import { createRouter, createWebHistory } from 'vue-router'
import { isLoggedIn } from '@/api/request'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/LoginView.vue'),
      meta: { requiresAuth: false }
    },
    {
      path: '/',
      component: () => import('@/layouts/MainLayout.vue'),
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          name: 'Dashboard',
          component: () => import('@/views/DashboardView.vue'),
        },
        {
          path: 'resume',
          name: 'Resume',
          component: () => import('@/views/ResumeView.vue'),
        },
        {
          path: 'jd',
          name: 'JD',
          component: () => import('@/views/JDView.vue'),
        },
        {
          path: 'chat',
          name: 'Chat',
          component: () => import('@/views/ChatView.vue'),
        },
        {
          path: 'interviews',
          name: 'Interview',
          component: () => import('@/views/InterviewView.vue'),
        },
        {
          path: 'dimensions',
          name: 'Dimension',
          component: () => import('@/views/DimensionView.vue'),
        },
      ],
    },
  ],
})

// 路由守卫 - 检查登录状态
router.beforeEach((to, _from, next) => {
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth !== false)

  if (requiresAuth && !isLoggedIn()) {
    // 需要登录但未登录，跳转到登录页
    next({
      path: '/login',
      query: { redirect: to.fullPath }
    })
  } else if (to.path === '/login' && isLoggedIn()) {
    // 已登录但访问登录页，跳转到首页
    next('/')
  } else {
    next()
  }
})

export default router
