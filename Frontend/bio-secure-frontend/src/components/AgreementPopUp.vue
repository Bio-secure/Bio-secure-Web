<script lang="ts">
import { defineComponent, ref, watch, onMounted, onBeforeUnmount } from 'vue';

export default defineComponent({
  name: 'AgreementPopUp',
  setup(_, {emit}) {
    const showPrivacyModal = ref(true); // State to control the visibility of the privacy modal

    const handleAcknowledge = () => {
      showPrivacyModal.value = false;
      localStorage.setItem('privacyAcknowledged', 'true');
      emit('acknowledged'); // Notify the parent component
    };

    watch(showPrivacyModal, (newValue) => {
      if (newValue) {
        document.body.style.overflow = 'hidden'; // Disable scrolling
      } else {
        document.body.style.overflow = 'unset'; // Re-enable scrolling
      }
    });

    // Initial setup: disable scrolling if modal is visible on mount
    onMounted(() => {
      if (showPrivacyModal.value) {
        console.log('AgreementPopUp mounted');
        document.body.style.overflow = 'hidden';
      }
    });

    // Cleanup: re-enable scrolling when component unmounts
    onBeforeUnmount(() => {
      document.body.style.overflow = 'unset';
    });

    return {
      showPrivacyModal,
      handleAcknowledge,
    };
  },
});


</script>

<template>
  <!-- Privacy Agreement Modal -->
  <div v-if="showPrivacyModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-10 backdrop-blur-sm">
    <div class="bg-white rounded-xl shadow-2xl p-6 sm:p-8 md:p-10 max-w-md w-full m-auto transform transition-all duration-300 ease-out scale-95 opacity-0 animate-scaleIn animate-fadeIn">
      <h2 class="text-2xl sm:text-3xl font-bold text-indigo-700 text-center mb-6">
        Privacy Agreement
      </h2>
      <div class="text-gray-700 text-sm sm:text-base leading-relaxed overflow-y-auto max-h-64 mb-8 pr-2">
        <p class="mb-4">
          Welcome to our website! Before you proceed, please take a moment to
          review our privacy policy. We value your privacy and are committed
          to protecting your personal data.
        </p>
        <p class="mb-4">
          This policy outlines how we collect, use, and safeguard your
          information when you visit our site. We collect data such as your
          IP address, browser type, and interaction patterns to improve our
          services and user experience.
        </p>
        <p class="mb-4">
          By continuing to use this website, you agree to the terms
          outlined in our privacy policy. This includes the use of cookies
          and similar technologies to enhance your browsing experience,
          personalize content, and analyze site traffic.
        </p>
        <p class="mb-4">
          We do not share your personal information with third parties
          without your explicit consent, except as required by law. You have
          the right to access, correct, or delete your personal data held
          by us.
        </p>
        <p class="mb-4">
          For more detailed information, please refer to our full Privacy
          Policy link provided in the footer of our website. Your continued
          use implies your acceptance of these terms.
        </p>
        <p>
          Thank you for your understanding and cooperation.
        </p>
      </div>
      <button
        @click="handleAcknowledge"
        class="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold py-3 px-6 rounded-lg transition duration-300 ease-in-out transform hover:scale-105 focus:outline-none focus:ring-4 focus:ring-indigo-300 shadow-md hover:shadow-lg"
      >
        Acknowledge and Continue
      </button>
    </div>
  </div>
</template>

<style scoped>
/* Basic animation styles for the modal */
.font-inter {
  font-family: 'Inter', sans-serif;
}
@keyframes scaleIn {
  from { transform: scale(0.95); opacity: 0; }
  to { transform: scale(1); opacity: 1; }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
.animate-scaleIn {
  animation: scaleIn 0.3s forwards;
}
.animate-fadeIn {
  animation: fadeIn 0.3s forwards;
}
</style>