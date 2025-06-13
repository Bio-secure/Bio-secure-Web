import { createRouter, createWebHistory} from 'vue-router'

import MainMenu from '../view/MainMenu.vue'
// @ts-ignore
import Register from '../view/Register.vue'
// @ts-ignore
import Identify from '../view/Identify.vue'
// @ts-ignore
import Monitor from '../view/Monitor.vue'
import InfoPage from '../view/InfoPage.vue'
// @ts-ignore
import EmLogin from '../view/EmLogin.vue'
// @ts-ignore
import authState from '../services/authService'; 

const routes = [
  {
    path: '/',
    name: 'login',
    component: EmLogin
  },
  {
    path: '/main',
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
    component: Monitor,
    meta: { requiresAuth: true, requiresAdmin: true }
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

// Navigation Guard for authentication and admin check
router.beforeEach((to, from, next) => {
  console.log('--- Navigation Guard Start ---');
  console.log('Attempting to go to:', to.path, 'with meta:', to.meta);
  console.log('Current authState:', {
    isLoggedIn: authState.isLoggedIn,
    isAdmin: authState.isAdmin,
    employeeId: authState.employeeId,
    name: authState.name,
    surname: authState.surname
  });

  // Check if the route requires authentication (like '/monitor')
  if (to.meta.requiresAuth) {
    console.log('Route requires authentication.');
    if (!authState.isLoggedIn) {
      console.log('User is NOT logged in. Redirecting to login page.');
      alert("Please log in to access this page.");
      next({ name: 'login' }); // Redirect to your EmLogin page
    } else {
      console.log('User IS logged in.');
      // If the route specifically requires admin privileges
      if (to.meta.requiresAdmin) {
        console.log('Route also requires admin privileges.');
        if (!authState.isAdmin) {
          console.log('User is logged in but IS NOT an admin. Redirecting to main menu.');
          alert("Access denied: Admin privileges required to view this page.");
          next({ name: 'mainmenu' }); // Redirect to MainMenu if not admin
        } else {
          console.log('User is logged in and IS an admin. Proceeding to route.');
          next(); // Logged in and is admin, proceed
        }
      } else {
        console.log('Route does not require admin. Proceeding to route.');
        next(); // Logged in and doesn't require admin, proceed
      }
    }
  } else {
    // Routes that do not require authentication (e.g., '/', '/main', '/register', etc.)
    console.log('Route does not require authentication. Proceeding to route.');
    next(); 
  }
  console.log('--- Navigation Guard End ---');
});


export default router