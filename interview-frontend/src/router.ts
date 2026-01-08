import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory('/interview/'),
  routes: [
    {
      path: '/hr/replay',
      name: 'HRReplay',
      component: () => import('./views/HRReplay.vue'),
      meta: { title: 'HR面试回放' }
    },
    {
      path: '/hr/monitor',
      name: 'HRMonitor',
      component: () => import('./views/HRMonitor.vue'),
      meta: { title: 'HR实时监控' }
    },
    {
      path: '/:token',
      name: 'InterviewEntry',
      component: () => import('./views/InterviewEntry.vue'),
      meta: { title: '面试入口' }
    },
    {
      path: '/:token/written',
      name: 'WrittenTest',
      component: () => import('./views/WrittenTest.vue'),
      meta: { title: '笔试测评' }
    },
    {
      path: '/:token/voice',
      name: 'VoiceInterview',
      component: () => import('./views/VoiceInterview.vue'),
      meta: { title: '语音面试' }
    },
    {
      path: '/:token/complete',
      name: 'InterviewComplete',
      component: () => import('./views/InterviewComplete.vue'),
      meta: { title: '面试完成' }
    },
    {
      path: '/:pathMatch(.*)*',
      redirect: '/'
    }
  ]
})

// 路由守卫
router.beforeEach((to, _from, next) => {
  // 设置页面标题
  document.title = (to.meta.title as string) || '面试系统'
  next()
})

export default router
