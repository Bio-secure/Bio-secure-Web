<script setup>
import { ref, computed } from 'vue';

// The component receives the customerId and verificationMode from the InfoPage
const props = defineProps({
  customerId: {
    type: [String, Number],
    required: true
  },
  verificationMode: {
    type: String,
    default: 'face' // 'face' or 'full'
  }
});

// It emits events to notify the InfoPage of the outcome
const emit = defineEmits(['close', 'verification-success', 'verification-fail']);

const selectedFaceFile = ref(null);
const facePreview = ref(null);
const selectedIrisFile = ref(null);
const irisPreview = ref(null);

const isLoading = ref(false);
const errorMessage = ref('');

// Define the URL for the Main Backend API (iris_model_api.js is now called internally by Main.py)
const MAIN_BACKEND_URL = "http://localhost:8000";

/**
 * Triggers the hidden file input for face image selection.
 */
function triggerFaceUpload() {
  document.getElementById("modalFaceFileInput").click();
}

/**
 * Triggers the hidden file input for iris image selection.
 */
function triggerIrisUpload() {
  document.getElementById("modalIrisFileInput").click();
}

/**
 * Handles the file change event for both face and iris inputs.
 * Updates the selected file and creates a URL for image preview.
 * @param {Event} event The change event from the file input.
 * @param {string} type The type of biometric ('face' or 'iris').
 */
function handleFileChange(event, type) {
  const file = event.target.files[0];
  if (!file) return;
  errorMessage.value = ''; // Clear any previous error messages

  if (type === 'face') {
    selectedFaceFile.value = file;
    facePreview.value = URL.createObjectURL(file);
  } else if (type === 'iris') {
    selectedIrisFile.value = file;
    irisPreview.value = URL.createObjectURL(file);
  }
}

/**
 * Computed property to determine if the "Verify Identity" button should be disabled.
 * It considers loading state, and whether required files (face and optionally iris) are selected.
 */
const isVerifyDisabled = computed(() => {
  if (isLoading.value) return true; // Disable if an operation is already in progress

  // If verificationMode is 'face', only face scan is required
  if (props.verificationMode === 'face') {
    return !selectedFaceFile.value;
  } 
  // If verificationMode is 'full', both face and iris files are required
  else if (props.verificationMode === 'full') {
    return !selectedFaceFile.value || !selectedIrisFile.value;
  }
  return true; // Should not happen, but default to disabled
});

/**
 * Initiates the identity verification process by sending all relevant files
 * to the Main backend's combined /verify endpoint.
 */
async function verifyIdentity() {
  isLoading.value = true;
  errorMessage.value = ''; // Clear previous errors

  const formData = new FormData();
  formData.append("customer_id", props.customerId);

  // Append face image if selected
  if (selectedFaceFile.value) {
    formData.append("face_image", selectedFaceFile.value);
  }

  // Append iris image if in 'full' mode and selected
  if (props.verificationMode === 'full' && selectedIrisFile.value) {
    formData.append("iris_image", selectedIrisFile.value);
  }

  try {
    const res = await fetch(`${MAIN_BACKEND_URL}/verify`, {
      method: "POST",
      body: formData
    });
    const data = await res.json();

    // The 'verified' property from Main.py now represents the overall success
    const overallSuccess = data.verified;
    const responseMessage = data.message;

    if (overallSuccess) {
      emit('verification-success');
    } else {
      errorMessage.value = responseMessage || "Verification failed due to unknown reasons.";
      emit('verification-fail', errorMessage.value);
    }

  } catch (err) {
    console.error("Network or unexpected error during verification:", err);
    errorMessage.value = `Verification request failed: ${err.message}`;
    emit('verification-fail', errorMessage.value);
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div class="fixed inset-0 bg-black bg-opacity-60 flex justify-center items-center z-50">
    <div class="bg-white p-8 rounded-2xl shadow-xl w-full max-w-lg mx-4">
      <h2 class="text-2xl font-bold text-center text-gray-800 mb-4">Identity Verification Required</h2>
      <p class="text-center text-gray-600 mb-6">Please provide the required biometric scans to proceed.</p>

      <input id="modalFaceFileInput" type="file" accept="image/*" class="hidden" @change="handleFileChange($event, 'face')" />
      <input id="modalIrisFileInput" type="file" accept="image/*" class="hidden" @change="handleFileChange($event, 'iris')" />

      <div class="flex items-center justify-center gap-6 mb-6">
        <div class="flex flex-col items-center">
          <p class="font-semibold mb-2">Face Scan*</p>
          <div @click="triggerFaceUpload" class="w-48 h-48 bg-gray-100 rounded-full border-2 border-dashed flex items-center justify-center cursor-pointer hover:border-blue-500">
            <img v-if="facePreview" :src="facePreview" class="w-full h-full object-cover rounded-full">
            <span v-else class="text-gray-500 text-center p-2">Click to Upload</span>
          </div>
        </div>
        
        <div v-if="verificationMode === 'full'" class="flex flex-col items-center">
          <p class="font-semibold mb-2">Iris Scan*</p>
          <div @click="triggerIrisUpload" class="w-48 h-48 bg-gray-100 rounded-full border-2 border-dashed flex items-center justify-center cursor-pointer hover:border-blue-500">
            <img v-if="irisPreview" :src="irisPreview" class="w-full h-full object-cover rounded-full">
            <span v-else class="text-gray-500 text-center p-2">Click to Upload</span>
          </div>
        </div>
      </div>

      <p v-if="errorMessage" class="text-red-500 text-sm mb-4 text-center">{{ errorMessage }}</p>

      <div class="flex items-center justify-center gap-4">
        <button @click="$emit('close')" :disabled="isLoading" class="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-6 rounded-lg">
          Cancel
        </button>
        <button @click="verifyIdentity" :disabled="isVerifyDisabled" class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-6 rounded-lg disabled:bg-gray-400">
          <span v-if="isLoading">Verifying...</span>
          <span v-else>Verify Identity</span>
        </button>
      </div>
    </div>
  </div>
</template>
