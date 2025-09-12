<script setup lang="ts">
defineProps<{
  show: boolean;
  title?: string;
  message?: string;
}>();
</script>
<template>
  <div v-if="show" class="fixed inset-0 flex items-center justify-center bg-black/20 z-50">
    <div class="bg-white p-6 rounded-2xl shadow-xl w-80">
      <h3 class="text-lg font-semibold mb-4">{{ title }}</h3>
      <p class="mb-6">{{ message }}</p>
      <div class="flex justify-end space-x-3">
        <button @click="$emit('cancel')" class="px-4 py-2 rounded-lg bg-gray-200 hover:bg-gray-300">Cancel</button>
        <button @click="$emit('confirm')" class="px-4 py-2 rounded-lg bg-red-500 text-white hover:bg-red-600">Confirm</button>
      </div>
    </div>
  </div>
</template>


