<!-- VerificationConfirmation.vue -->
<script setup>
const props = defineProps({
  isOpen: { type: Boolean, default: false },
  success: { type: Boolean, default: false },
  message: { type: String, default: "" },
});

const emit = defineEmits(["close"]);
</script>

<template>
  <div v-if="isOpen" class="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
    <div class="bg-white p-6 rounded-xl shadow-xl w-full max-w-sm relative">
      <!-- Close -->
      <button
        @click="$emit('close')"
        class="absolute top-2 right-2 text-gray-500 hover:text-gray-800"
      >
        ✕
      </button>

      <h2
        class="text-xl font-bold mb-4"
        :class="success ? 'text-green-600' : 'text-red-600'"
      >
        {{ success ? 'Verification Successful' : 'Verification Failed' }}
      </h2>

      <p class="text-gray-700 text-center">{{ message }}</p>

      <div class="mt-4 flex justify-center">
        <button
          @click="$emit('close')"
          class="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg"
        >
          OK
        </button>
      </div>
    </div>
  </div>
</template>
