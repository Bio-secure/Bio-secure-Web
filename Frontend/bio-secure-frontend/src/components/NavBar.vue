<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router';
import { computed, ref } from 'vue';
// @ts-ignore
import authState, { logout } from '../services/authService';

const route = useRoute();
const router = useRouter();
const showAgreement = ref(false)

// This computed property checks if the user is currently on the login page.
const onLoginPage = computed(() => route.name === 'login');

const handleLogout = () => {
  logout();
  localStorage.setItem('privacyAcknowledged', 'false')
  router.push('/'); // The path for the 'login' route is '/'
};
</script>

<template>
  <nav class="bg-[#1b2d3d] px-6 py-3 flex justify-between items-center">
    <div class="text-white font-bold text-xl tracking-wide">
      
      <RouterLink 
        v-if="!onLoginPage" 
        to="/main"
        class="hover:text-gray-300 transition-colors"
      >
        Bio-secure
      </RouterLink>

      <span v-else>
        Bio-secure
      </span>

    </div>
    
    <button
      v-if="authState.isLoggedIn"
      @click="handleLogout"
      class="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded-lg text-sm shadow-md transition duration-300 ease-in-out"
    >
      Logout ({{ authState.name }} {{ authState.surname }})
    </button>
  </nav>
</template>