import { createRouter, createWebHistory} from 'vue-router'

import MainMenu from '../view/MainMenu.vue'
// @ts-ignore
import Register from '../view/Register.vue'
// @ts-ignore
import Identify from '../view/Identify.vue'
import Monitor from '../view/Monitor.vue'
import InfoPage from '../view/InfoPage.vue'

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
  {
    path: '/infopage',
    name: 'infopage',
    component: InfoPage
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
