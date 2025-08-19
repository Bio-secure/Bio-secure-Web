<script setup>
import { ref, computed, onBeforeUnmount } from 'vue';

// PROPS & EMITS (unchanged)
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
const emit = defineEmits(['close', 'verification-success', 'verification-fail']);

// STATE MANAGEMENT
const faceState = ref('idle'); // idle -> streaming -> captured
const irisState = ref('idle'); // idle -> streaming -> captured

const selectedFaceFile = ref(null);
const facePreview = ref(null);
const selectedIrisFile = ref(null);
const irisPreview = ref(null);

const isLoading = ref(false);
const errorMessage = ref('');

// BACKEND URL (unchanged)
const MAIN_BACKEND_URL = "http://localhost:8000";

// DOM REFS & STREAM MANAGEMENT
let faceStream = null;
let irisStream = null;
const faceVideo = ref(null);
const irisVideo = ref(null);

// --- REFACTORED FUNCTIONS ---

/**
 * Stops a given media stream and its tracks.
 */
function stopStream(stream) {
  if (stream) {
    stream.getTracks().forEach(track => track.stop());
  }
}

/**
 * Starts the webcam for the specified scan type.
 */
async function startWebcam(type) {
  const state = type === 'face' ? faceState : irisState;
  const videoEl = type === 'face' ? faceVideo : irisVideo;

  // Stop any existing stream before starting a new one
  stopStream(type === 'face' ? faceStream : irisStream);

  const constraints = { video: { width: 480, height: 480 }, audio: false };
  try {
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    if (type === 'face') {
      faceStream = stream;
    } else {
      irisStream = stream;
    }
    videoEl.value.srcObject = stream;
    state.value = 'streaming';
  } catch (err) {
    errorMessage.value = `Unable to access webcam: ${err.message}`;
  }
}

/**
 * Captures a photo from the active video stream.
 */
function capturePhoto(type) {
  const state = type === 'face' ? faceState : irisState;
  const videoEl = type === 'face' ? faceVideo.value : irisVideo.value;
  const stream = type === 'face' ? faceStream : irisStream;

  if (!videoEl || !stream) return;

  const canvas = document.createElement('canvas');
  canvas.width = videoEl.videoWidth;
  canvas.height = videoEl.videoHeight;
  const ctx = canvas.getContext('2d');
  // Flip the image horizontally for a mirror effect
  ctx.translate(canvas.width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);

  canvas.toBlob(blob => {
    if (type === 'face') {
      selectedFaceFile.value = new File([blob], 'face.jpg', { type: 'image/jpeg' });
      facePreview.value = URL.createObjectURL(blob);
    } else {
      selectedIrisFile.value = new File([blob], 'iris.jpg', { type: 'image/jpeg' });
      irisPreview.value = URL.createObjectURL(blob);
    }
    state.value = 'captured';
    stopStream(stream); // Stop the stream after capture
  }, 'image/jpeg', 0.95);
}

/**
 * Resets a scan to its initial state, allowing a retake.
 */
function resetScan(type) {
  if (type === 'face') {
    selectedFaceFile.value = null;
    facePreview.value = null;
    faceState.value = 'idle';
  } else {
    selectedIrisFile.value = null;
    irisPreview.value = null;
    irisState.value = 'idle';
  }
}

// --- COMPUTED PROPERTIES for dynamic UI ---

const isVerifyDisabled = computed(() => {
  if (isLoading.value) return true;
  if (props.verificationMode === 'face') {
    return faceState.value !== 'captured';
  } else if (props.verificationMode === 'full') {
    return faceState.value !== 'captured' || irisState.value !== 'captured';
  }
  return true;
});

// --- API CALL (unchanged) ---

async function verifyIdentity() {
  isLoading.value = true;
  errorMessage.value = '';
  const formData = new FormData();
  formData.append("customer_id", props.customerId);
  if (selectedFaceFile.value) formData.append("face_image", selectedFaceFile.value);
  if (props.verificationMode === 'full' && selectedIrisFile.value) {
    formData.append("iris_image", selectedIrisFile.value);
  }

  try {
    const res = await fetch(`${MAIN_BACKEND_URL}/verify`, { method: "POST", body: formData });
    if (!res.ok) {
        const errorData = await res.json().catch(() => ({ message: 'Verification failed with status: ' + res.status }));
        throw new Error(errorData.message || 'Verification request failed.');
    }
    const data = await res.json();
    if (data.verified) {
      emit('verification-success');
    } else {
      errorMessage.value = data.message || "Verification failed. Biometrics did not match.";
      emit('verification-fail', errorMessage.value);
    }
  } catch (err) {
    errorMessage.value = `Error: ${err.message}`;
    emit('verification-fail', errorMessage.value);
  } finally {
    isLoading.value = false;
  }
}

// --- LIFECYCLE HOOKS ---

onBeforeUnmount(() => {
  stopStream(faceStream);
  stopStream(irisStream);
});
</script>

<template>
  <div class="fixed inset-0 bg-black bg-opacity-70 flex justify-center items-center z-50 transition-opacity">
    <div class="bg-white p-6 sm:p-8 rounded-2xl shadow-2xl w-full max-w-md mx-4 transform transition-all">
      
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-2xl font-bold text-gray-800">Identity Verification</h2>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
        </button>
      </div>

      <div class="space-y-6">
        <div>
          <div class="relative w-full aspect-square bg-gray-100 rounded-full overflow-hidden border-2 border-gray-200 flex items-center justify-center">
            <div v-if="faceState === 'idle'" class="text-center text-gray-500">
              <svg class="w-16 h-16 mx-auto opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"></path></svg>
              <p class="mt-2 text-sm">Camera is off</p>
            </div>
            <video v-show="faceState === 'streaming'" ref="faceVideo" autoplay playsinline class="w-full h-full object-cover transform -scale-x-100"></video>
            <img v-if="faceState === 'captured'" :src="facePreview" class="w-full h-full object-cover">
          </div>
          <div class="flex gap-2 mt-3 justify-center">
            <button v-if="faceState === 'idle'" @click="startWebcam('face')" class="bg-blue-600 text-white px-5 py-2 rounded-lg font-semibold hover:bg-blue-700 transition shadow-sm">Start Camera</button>
            <button v-if="faceState === 'streaming'" @click="capturePhoto('face')" class="bg-green-600 text-white px-5 py-2 rounded-lg font-semibold hover:bg-green-700 transition shadow-sm">Capture Photo</button>
            <button v-if="faceState === 'captured'" @click="resetScan('face')" class="bg-gray-200 text-gray-700 px-5 py-2 rounded-lg font-semibold hover:bg-gray-300 transition">Retake</button>
          </div>
        </div>

        <div v-if="verificationMode === 'full'">
          <h3 class="font-semibold text-gray-700 mb-2">Step 2: Iris Scan</h3>
          <div class="relative w-full aspect-square bg-gray-100 rounded-full overflow-hidden border-2 border-gray-200 flex items-center justify-center">
             <div v-if="irisState === 'idle'" class="text-center text-gray-500">
              <svg class="w-16 h-16 mx-auto opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>
              <p class="mt-2 text-sm">Camera is off</p>
            </div>
            <video v-show="irisState === 'streaming'" ref="irisVideo" autoplay playsinline class="w-full h-full object-cover transform -scale-x-100"></video>
            <img v-if="irisState === 'captured'" :src="irisPreview" class="w-full h-full object-cover">
          </div>
          <div class="flex gap-2 mt-3 justify-center">
            <button v-if="irisState === 'idle'" @click="startWebcam('iris')" class="bg-blue-600 text-white px-5 py-2 rounded-lg font-semibold hover:bg-blue-700 transition shadow-sm">Start Camera</button>
            <button v-if="irisState === 'streaming'" @click="capturePhoto('iris')" class="bg-green-600 text-white px-5 py-2 rounded-lg font-semibold hover:bg-green-700 transition shadow-sm">Capture Photo</button>
            <button v-if="irisState === 'captured'" @click="resetScan('iris')" class="bg-gray-200 text-gray-700 px-5 py-2 rounded-lg font-semibold hover:bg-gray-300 transition">Retake</button>
          </div>
        </div>
      </div>
      
      <p v-if="errorMessage" class="text-red-600 bg-red-100 text-center p-3 rounded-lg mt-6 text-sm">{{ errorMessage }}</p>

      <div class="flex justify-end gap-4 mt-8 pt-4 border-t">
        <button @click="$emit('close')" class="bg-gray-200 text-gray-800 px-6 py-2 rounded-lg font-semibold hover:bg-gray-300 transition">Cancel</button>
        <button @click="verifyIdentity" :disabled="isVerifyDisabled" class="bg-blue-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-blue-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center">
          <svg v-if="isLoading" class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ isLoading ? 'Verifying...' : 'Verify Identity' }}
        </button>
      </div>
    </div>
  </div>
</template>