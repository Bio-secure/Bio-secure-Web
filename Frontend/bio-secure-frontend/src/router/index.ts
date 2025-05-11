// src/router/index.ts

import { createRouter, createWebHistory} from 'vue-router'
import MainMenu from '../view/MainMenu.vue'

const routes = [
  {
    path: '/',
    name: 'MainMenu',
    component: MainMenu
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
