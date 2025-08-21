<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router';
import { computed } from 'vue';
// @ts-ignore
import authState, { logout } from '../services/authService';

// --- NEW IMPORTS for Dropdown Menu and Icons ---
import { Menu, MenuButton, MenuItems, MenuItem } from '@headlessui/vue'
import { ChevronDownIcon } from '@heroicons/vue/20/solid'

const route = useRoute();
const router = useRouter();

// This computed property checks if the user is currently on the login page.
const onLoginPage = computed(() => route.path === '/');

const handleLogout = () => {
  logout();
  localStorage.setItem('privacyAcknowledged', 'false')
  router.push('/');
};
</script>

<template>
  <nav class="bg-white shadow-md px-4 sm:px-6 py-3">
    <div class="max-w-7xl mx-auto flex justify-between items-center">
      
      <div class="flex-shrink-0">
        <RouterLink 
          to="/main"
          class="text-2xl font-bold text-blue-600 tracking-wide hover:opacity-80 transition"
        >
          Bio-secure
        </RouterLink>
      </div>
      
      <div v-if="authState.isLoggedIn && !onLoginPage" class="hidden md:flex items-center space-x-6">
        <RouterLink
          to="/register"
          class="text-gray-600 font-semibold hover:text-blue-600 transition-colors pb-1 border-b-2 border-transparent"
          active-class="!border-blue-600 !text-blue-600"
        >
          Register Customer
        </RouterLink>
        <RouterLink
          to="/identify"
          class="text-gray-600 font-semibold hover:text-blue-600 transition-colors pb-1 border-b-2 border-transparent"
          active-class="!border-blue-600 !text-blue-600"
        >
          Transaction
        </RouterLink>
        <RouterLink
          to="/monitor"
          class="text-gray-600 font-semibold hover:text-blue-600 transition-colors pb-1 border-b-2 border-transparent"
          active-class="!border-blue-600 !text-blue-600"
        >
          Dashboard
        </RouterLink>
      </div>
      
      <div v-if="authState.isLoggedIn" class="flex items-center">
        <Menu as="div" class="relative inline-block text-left">
          <div>
            <MenuButton class="inline-flex w-full items-center justify-center gap-x-2 rounded-full bg-gray-100 p-2 text-sm font-semibold text-gray-800 hover:bg-gray-200 transition">
              <div class="w-8 h-8 rounded-full bg-blue-200 flex items-center justify-center font-bold text-blue-700">
                {{ authState.name ? authState.name.charAt(0) : '' }}{{ authState.surname ? authState.surname.charAt(0) : '' }}
              </div>
              <span class="hidden sm:block">{{ authState.name }}</span>
              <ChevronDownIcon class="h-5 w-5 text-gray-500" aria-hidden="true" />
            </MenuButton>
          </div>

          <transition enter-active-class="transition ease-out duration-100" enter-from-class="transform opacity-0 scale-95" enter-to-class="transform opacity-100 scale-100" leave-active-class="transition ease-in duration-75" leave-from-class="transform opacity-100 scale-100" leave-to-class="transform opacity-0 scale-95">
            <MenuItems class="absolute right-0 z-10 mt-2 w-56 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
              <div class="py-1">
                <div class="px-4 py-2 border-b border-gray-100">
                  <p class="text-sm font-semibold text-gray-900">{{ authState.name }} {{ authState.surname }}</p>
                  <p class="text-sm text-gray-500">{{ authState.isAdmin ? 'Administrator' : 'Employee' }}</p>
                </div>
                <MenuItem v-slot="{ active }">
                  <a href="#" @click="handleLogout" :class="[active ? 'bg-red-50 text-red-800' : 'text-gray-700', 'block px-4 py-2 text-sm font-semibold']">
                    Logout
                  </a>
                </MenuItem>
              </div>
            </MenuItems>
          </transition>
        </Menu>
      </div>

    </div>
  </nav>
</template>