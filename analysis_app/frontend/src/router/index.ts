import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [

    {
      path: '/',
      name: 'home',
      // route level code-splitting
      // this generates a separate chunk (About.[hash].js) for this route
      // which is lazy-loaded when the route is visited.
      component: () => import('../views/data-graph/home-data-main.vue'),
    },

    // 项目详情页（独立页面，通过路由参数 codeId 展示项目信息 / K线）
    {
      path: '/project/:codeId',
      name: 'project-detail',
      component: () => import('../views/project-detail/home-project-detail.vue'),
    },

    // 新闻独立查询页
    {
      path: '/news',
      name: 'news',
      component: () => import('../views/news/news-list.vue'),
    },

    // 新闻详情页（按 id 展示单条新闻）
    {
      path: '/news/:id',
      name: 'news-detail',
      component: () => import('../views/news/news-detail.vue'),
    },
  ],
})

export default router
