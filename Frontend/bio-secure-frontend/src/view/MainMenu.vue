<script lang="ts">
import { defineComponent, ref, onMounted } from 'vue';
import AgreementPopUp from '../components/AgreementPopUp.vue';

export default defineComponent({
  name: 'MainMenu',
  components: {
    AgreementPopUp
  },
  setup() {
    const showAgreement = ref(false);

    onMounted(() => {
      const hasAgreed = localStorage.getItem('privacyAcknowledged') === 'true';
      // Only show the modal if the user has never agreed
      showAgreement.value = !hasAgreed;
    });

    // Hide modal from parent when child acknowledges
    const handleAgreementAcknowledged = () => {
      showAgreement.value = false;
    };

    return { showAgreement, handleAgreementAcknowledged };
  }
});
</script>

<template>
  <div class="min-h-screen flex items-center justify-center">
    <agreement-pop-up v-if="showAgreement" @acknowledged="handleAgreementAcknowledged" />
    <div class="grid grid-cols-3 gap-28">
      <!-- Register -->
      <div class="p-10 flex flex-col items-center">
        <img src="../assets/Register.png" alt="Register" class="w-60 h-60 mb-8" />
        <RouterLink to="/register">
          <button class="mt-6 bg-blue-300 text-black font-bold text-2xl px-8 py-4 rounded-2xl shadow-md hover:bg-blue-400">
            REGISTER
          </button>
        </RouterLink>
      </div>

      <!-- Identify -->
      <div class="p-10 flex flex-col items-center">
        <img src="../assets/Identify.png" alt="Identify" class="w-60 h-60 mb-8" />
        <RouterLink to="/identify">
          <button class="mt-6 bg-blue-300 text-black font-bold text-2xl px-8 py-4 rounded-2xl shadow-md hover:bg-blue-400">
            IDENTIFY
          </button>
        </RouterLink>
      </div>

      <!-- Dashboard -->
      <div class="p-10 flex flex-col items-center">
        <img src="../assets/Monitor.png" alt="Dashboard" class="w-60 h-60 mb-8" />
        <RouterLink to="/monitor">
          <button class="mt-6 bg-blue-300 text-black font-bold text-2xl px-8 py-4 rounded-2xl shadow-md hover:bg-blue-400">
            DASHBOARD
          </button>
        </RouterLink>
      </div>
    </div>
  </div>
</template>
