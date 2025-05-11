// src/router/index.ts

import { createRouter, createWebHistory} from 'vue-router'
import MainMenu from '../view/MainMenu.vue'
import Register from '../view/Register.vue'
import Identify from '../view/Identify.vue'
import Monitor from '../view/Monitor.vue'

const routes = [
  {
    path: '/',
    name: 'mainmenu',
    component: MainMenu
  },
  {
    path: '/register',
    name: 'register',
    component: Register
  },
  {
    path: '/identify',
    name: 'identify',
    component: Identify
  },
  {
    path: '/monitor',
    name: 'monitor',
    component: Monitor
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
