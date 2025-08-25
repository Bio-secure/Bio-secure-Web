<script lang="ts">
import { defineComponent, ref, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import AgreementPopUp from '../components/AgreementPopUp.vue';

// Importing icons for the cards
import { 
  UserPlusIcon, 
  ArrowsRightLeftIcon, 
  ChartPieIcon,
  ArrowRightIcon
} from '@heroicons/vue/24/outline';

export default defineComponent({
  name: 'MainMenu',
  components: {
    AgreementPopUp,
    RouterLink,
    UserPlusIcon,
    ArrowsRightLeftIcon,
    ChartPieIcon,
    ArrowRightIcon
  },
  setup() {
    const showAgreement = ref(false);

    onMounted(() => {
      const hasAgreed = localStorage.getItem('privacyAcknowledged') === 'true';
      showAgreement.value = !hasAgreed;
    });

    const handleAgreementAcknowledged = () => {
      showAgreement.value = false;
    };

    return { showAgreement, handleAgreementAcknowledged };
  }
});
</script>

<template>
  <div class="relative min-h-screen flex flex-col items-center justify-center p-8 font-sans overflow-hidden">

    <agreement-pop-up v-if="showAgreement" @acknowledged="handleAgreementAcknowledged" />

    <div class="relative z-10 text-center">
      <h1 class="text-5xl font-bold text-gray-800 tracking-tight">Welcome to Bio-secure</h1>
      <p class="mt-4 text-lg text-gray-600">Please select an action to continue.</p>
    </div>

    <div class="relative z-10 grid grid-cols-1 md:grid-cols-3 gap-8 mt-12 w-full max-w-5xl">
      
      <RouterLink to="/register" class="group bg-white/70 backdrop-blur-xl p-8 rounded-2xl shadow-lg border border-gray-200 hover:shadow-2xl hover:-translate-y-2 transition-all duration-300 flex flex-col items-start">
        <div class="bg-blue-100 text-blue-600 p-4 rounded-full">
          <UserPlusIcon class="w-8 h-8" />
        </div>
        <h2 class="text-2xl font-bold text-gray-800 mt-6">Register Customer</h2>
        <p class="text-gray-600 mt-2 flex-grow">Onboard a new customer, record their personal details, and prepare for biometric enrollment.</p>
        <div class="mt-6 font-semibold text-blue-600 flex items-center gap-2">
          Go to Registration
          <ArrowRightIcon class="w-5 h-5 group-hover:translate-x-1 transition-transform" />
        </div>
      </RouterLink>

      <RouterLink to="/identify" class="group bg-white/70 backdrop-blur-xl p-8 rounded-2xl shadow-lg border border-gray-200 hover:shadow-2xl hover:-translate-y-2 transition-all duration-300 flex flex-col items-start">
        <div class="bg-green-100 text-green-600 p-4 rounded-full">
          <ArrowsRightLeftIcon class="w-8 h-8" />
        </div>
        <h2 class="text-2xl font-bold text-gray-800 mt-6">Transaction Process</h2>
        <p class="text-gray-600 mt-2 flex-grow">Look up an existing customer by their ID or name to perform a deposit or withdrawal.</p>
        <div class="mt-6 font-semibold text-green-600 flex items-center gap-2">
          Find Customer
          <ArrowRightIcon class="w-5 h-5 group-hover:translate-x-1 transition-transform" />
        </div>
      </RouterLink>

      <RouterLink to="/monitor" class="group bg-white/70 backdrop-blur-xl p-8 rounded-2xl shadow-lg border border-gray-200 hover:shadow-2xl hover:-translate-y-2 transition-all duration-300 flex flex-col items-start">
        <div class="bg-indigo-100 text-indigo-600 p-4 rounded-full">
          <ChartPieIcon class="w-8 h-8" />
        </div>
        <h2 class="text-2xl font-bold text-gray-800 mt-6">View Dashboard</h2>
        <p class="text-gray-600 mt-2 flex-grow">Access the monitoring dashboard to see real-time logs, registration statistics, and system activity.</p>
        <div class="mt-6 font-semibold text-indigo-600 flex items-center gap-2">
          Open Dashboard
          <ArrowRightIcon class="w-5 h-5 group-hover:translate-x-1 transition-transform" />
        </div>
      </RouterLink>
      
    </div>
  </div>
</template>