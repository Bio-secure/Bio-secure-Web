<template>
    <div class="font-inter antialiased text-gray-800 bg-gray-50 min-h-screen flex flex-col justify-center items-center p-4 sm:p-6 lg:p-8">
      <!-- Main content of your application (hidden behind the modal when active) -->
      <h1 class="text-4xl sm:text-5xl font-extrabold text-indigo-700 mb-6 text-center">
        Welcome to Our Website!
      </h1>
      <p class="text-lg sm:text-xl text-gray-600 text-center max-w-2xl mb-8">
        This is your main content. The privacy agreement pop-up will appear on top of this.
      </p>
      <div class="bg-white p-6 sm:p-8 rounded-xl shadow-lg border border-gray-200 w-full max-w-3xl text-center">
        <h2 class="text-2xl sm:text-3xl font-bold text-gray-900 mb-4">
          Explore Our Features
        </h2>
        <p class="text-md sm:text-lg text-gray-700 leading-relaxed">
          We offer a variety of services designed to enhance your experience.
          Navigate through our sections to discover more!
        </p>
      </div>
  
      <!-- Privacy Agreement Modal -->
      <div v-if="showPrivacyModal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-70 backdrop-blur-sm">
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
  
      <!-- Tailwind CSS Script - Ensures Tailwind classes are available -->
      <script src="https://cdn.tailwindcss.com"></script>
      <!-- Inter Font - Ensures the desired font is loaded -->
      <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet" />
    </div>
  </template>
  
  <script>
  export default {
    name: 'PrivacyAgreementPopup',
    data() {
      return {
        showPrivacyModal: true, // State to control the visibility of the privacy modal
      };
    },
    watch: {
      // Watch for changes in showPrivacyModal to control body scrolling
      showPrivacyModal(newValue) {
        if (newValue) {
          document.body.style.overflow = 'hidden'; // Disable scrolling
        } else {
          document.body.style.overflow = 'unset'; // Re-enable scrolling
        }
      },
    },
    mounted() {
      // Initial setup: disable scrolling if modal is visible on mount
      if (this.showPrivacyModal) {
        document.body.style.overflow = 'hidden';
      }
    },
    beforeUnmount() {
      // Cleanup: re-enable scrolling when component unmounts
      document.body.style.overflow = 'unset';
    },
    methods: {
      // Function to handle the "Acknowledge" button click
      handleAcknowledge() {
        this.showPrivacyModal = false; // Hide the modal
        console.log('Privacy agreement acknowledged!');
        // You can add further logic here, e.g., storing a flag in localStorage
      },
    },
  };
  </script>
  
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
  