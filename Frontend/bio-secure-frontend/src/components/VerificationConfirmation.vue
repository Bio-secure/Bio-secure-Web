<!-- VerificationConfirmation.vue -->
<script setup>
import { CheckCircleIcon, XCircleIcon } from '@heroicons/vue/24/solid';

const props = defineProps({
  isOpen: { type: Boolean, default: false },
  success: { type: Boolean, default: false },
  message: { type: String, default: "" },
  details: { type: Object, default: null },
});

const emit = defineEmits(["close"]);
</script>

<template>
  <transition
    enter-active-class="transition ease-out duration-300"
    enter-from-class="opacity-0 scale-90"
    enter-to-class="opacity-100 scale-100"
    leave-active-class="transition ease-in duration-200"
    leave-from-class="opacity-100 scale-100"
    leave-to-class="opacity-0 scale-90"
  >
    <div
      v-if="isOpen"
      class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
    >
      <div
        class="bg-white p-6 rounded-2xl shadow-2xl w-full max-w-sm relative"
      >
        <!-- Close -->
        <button
          @click="$emit('close')"
          class="absolute top-3 right-3 text-gray-400 hover:text-gray-600"
        >
          ✕
        </button>

        <!-- Icon -->
        <div class="flex justify-center mb-4">
          <div
            class="w-20 h-20 rounded-full flex items-center justify-center shadow-md animate-pulse"
            :class="success ? 'bg-green-100' : 'bg-red-100'"
          >
            <CheckCircleIcon
              v-if="success"
              class="w-12 h-12 text-green-600 "
            />
            <XCircleIcon
              v-else
              class="w-12 h-12 text-red-600"
            />
          </div>
        </div>

        <!-- Title -->
        <h2
          class="text-2xl font-bold text-center mb-2"
          :class="success ? 'text-green-700' : 'text-red-700'"
        >
          {{ success ? 'Verification Successful' : 'Verification Failed' }}
        </h2>

        <!-- Message -->
        <p class="text-gray-600 text-center mb-6">
          {{ message }}
        </p>

        <!-- Details Section -->
        <div v-if="details" class="text-sm text-gray-700 bg-gray-50 p-3 rounded-lg overflow-auto max-h-48">
          <div class="mt-2">
          <!-- Face -->
          <p v-if="details.face?.details.message">
            <strong>Face:</strong> {{ details.face.details.message }} 
            <span v-if="details.face.details.distance !== undefined">
              <strong>Distance:</strong> {{ ((1 - details.face.details.distance) * 100).toFixed(1) }}%
            </span>
          </p>

          <!-- Left Iris -->
          <p v-if="details.left_iris?.message && !details.left_iris.message.includes('No left iris image provided')">
            <strong>Left Iris:</strong> {{ details.left_iris.message }} 
            <span v-if="details.left_iris.distance !== undefined">
              Distance: {{ ((1 - details.left_iris.distance) * 100).toFixed(1) }}%
            </span>
          </p>

          <!-- Right Iris -->
          <p v-if="details.right_iris?.message && !details.right_iris.message.includes('No right iris image provided')">
            <strong>Right Iris:</strong> {{ details.right_iris.message }} 
            <span v-if="details.right_iris.distance !== undefined">
              Distance: {{ ((1 - details.right_iris.distance) * 100).toFixed(1) }}%
            </span>
          </p>
        </div>
          
        </div>

        <!-- OK Button -->
        <div class="flex justify-center">
          <button
            @click="$emit('close')"
            class="px-6 py-2 rounded-lg font-semibold shadow-md transition transform hover:scale-105"
            :class="success
              ? 'bg-green-600 text-white hover:bg-green-700'
              : 'bg-red-600 text-white hover:bg-red-700'"
          >
            OK
          </button>
        </div>
      </div>
    </div>
  </transition>
</template>
