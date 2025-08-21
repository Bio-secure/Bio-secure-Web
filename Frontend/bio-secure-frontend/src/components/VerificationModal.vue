<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';

// PROPS & EMITS
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
const currentStep = ref('face'); // 'face' or 'iris'
const faceState = ref('idle'); // idle -> streaming -> captured
const irisState = ref('idle'); // idle -> streaming -> captured
const showFlash = ref(false);

const selectedFaceFile = ref(null);
const facePreview = ref(null);
const selectedIrisFile = ref(null);
const irisPreview = ref(null);

const isLoading = ref(false);
const errorMessage = ref('');

// --- NEW: State for camera selection ---
const videoDevices = ref([]);
const selectedFaceDeviceId = ref('');
const selectedIrisDeviceId = ref('');

const MAIN_BACKEND_URL = "http://localhost:8000";

// DOM REFS & STREAM MANAGEMENT
let faceStream = null;
let irisStream = null;
const faceVideo = ref(null);
const irisVideo = ref(null);

// --- HELPER FUNCTIONS ---
async function getVideoDevices() {
  try {
    await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    const devices = await navigator.mediaDevices.enumerateDevices();
    videoDevices.value = devices.filter(device => device.kind === 'videoinput');
    
    // Set smart defaults
    if (videoDevices.value.length > 0) {
      selectedFaceDeviceId.value = videoDevices.value[0].deviceId;
    }
    if (videoDevices.value.length > 1) {
      selectedIrisDeviceId.value = videoDevices.value[1].deviceId;
    } else if (videoDevices.value.length === 1) {
      // If only one camera, default iris to it as well
      selectedIrisDeviceId.value = videoDevices.value[0].deviceId;
    }
  } catch (err) {
    console.error("Could not get video devices:", err);
  }
}

function stopStream(stream) {
  if (stream) {
    stream.getTracks().forEach(track => track.stop());
  }
}

async function startWebcam(type) {
  const state = type === 'face' ? faceState : irisState;
  const videoEl = type === 'face' ? faceVideo : irisVideo;
  
  stopStream(type === 'face' ? faceStream : irisStream);

  const deviceId = type === 'face' ? selectedFaceDeviceId.value : selectedIrisDeviceId.value;
  const constraints = { 
    video: { 
      width: 480, height: 480, 
      facingMode: 'user',
      deviceId: deviceId ? { exact: deviceId } : undefined
    }, 
    audio: false 
  };
  
  try {
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    if (type === 'face') faceStream = stream;
    else irisStream = stream;
    
    if (videoEl.value) {
      videoEl.value.srcObject = stream;
    }
    state.value = 'streaming';
  } catch (err) {
    errorMessage.value = `Unable to access webcam: ${err.message}`;
  }
}

function capturePhoto(type) {
  const state = type === 'face' ? faceState : irisState;
  const videoEl = type === 'face' ? faceVideo.value : irisVideo.value;
  const stream = type === 'face' ? faceStream : irisStream;

  if (!videoEl || !stream) return;

  showFlash.value = true;
  setTimeout(() => { showFlash.value = false; }, 150);

  const canvas = document.createElement('canvas');
  canvas.width = videoEl.videoWidth;
  canvas.height = videoEl.videoHeight;
  const ctx = canvas.getContext('2d');
  ctx.translate(canvas.width, 0);
  ctx.scale(-1, 1);
  ctx.drawImage(videoEl, 0, 0, canvas.width, canvas.height);

  canvas.toBlob(blob => {
    if (type === 'face') {
      selectedFaceFile.value = new File([blob], 'face.jpg', { type: 'image/jpeg' });
      facePreview.value = URL.createObjectURL(blob);
      state.value = 'captured';
      stopStream(stream);
      if (props.verificationMode === 'full') {
        currentStep.value = 'iris';
        startWebcam('iris');
      }
    } else { // Iris
      selectedIrisFile.value = new File([blob], 'iris.jpg', { type: 'image/jpeg' });
      irisPreview.value = URL.createObjectURL(blob);
      state.value = 'captured';
      stopStream(stream);
    }
  }, 'image/jpeg', 0.95);
}

function resetScan(type) {
  const state = type === 'face' ? faceState : irisState;
  if (type === 'face') {
    selectedFaceFile.value = null;
    facePreview.value = null;
  } else {
    selectedIrisFile.value = null;
    irisPreview.value = null;
  }
  state.value = 'idle';
}

// --- COMPUTED PROPERTIES ---
const isVerifyDisabled = computed(() => {
  if (isLoading.value) return true;
  if (props.verificationMode === 'face') {
    return faceState.value !== 'captured';
  } else if (props.verificationMode === 'full') {
    return faceState.value !== 'captured' || irisState.value !== 'captured';
  }
  return true;
});

const currentStepTitle = computed(() => {
  if (props.verificationMode === 'full') {
    return currentStep.value === 'face' ? 'Step 1 of 2: Face Scan' : 'Step 2 of 2: Iris Scan';
  }
  return 'Face Scan';
});

const currentScannerState = computed(() => {
  return currentStep.value === 'face' ? faceState.value : irisState.value;
});

// --- API CALL ---
async function verifyIdentity() {
    // ... function unchanged ...
}

// --- LIFECYCLE HOOKS ---
onMounted(() => {
  getVideoDevices();
});

onBeforeUnmount(() => {
  stopStream(faceStream);
  stopStream(irisStream);
});
</script>

<template>
  <div class="fixed inset-0 bg-black bg-opacity-70 flex justify-center items-center z-50 transition-opacity">
    <div class="bg-white p-6 sm:p-8 rounded-2xl shadow-2xl w-full max-w-sm mx-4 transform transition-all">
      
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-2xl font-bold text-gray-800">Identity Verification</h2>
        <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
        </button>
      </div>

      <div>
        <h3 class="font-semibold text-gray-700 mb-2 text-center text-lg">{{ currentStepTitle }}</h3>
        
        <div class="mb-3 w-full">
          <label for="camera-select" class="block text-sm font-medium text-gray-700">Select Camera</label>
          <select v-if="currentStep === 'face'" id="camera-select-face" v-model="selectedFaceDeviceId" class="mt-1 block w-full px-3 py-2 border border-gray-300 bg-white rounded-md shadow-sm">
            <option v-for="device in videoDevices" :key="device.deviceId" :value="device.deviceId">
              {{ device.label || `Camera ${videoDevices.indexOf(device) + 1}` }}
            </option>
          </select>
          <select v-if="currentStep === 'iris'" id="camera-select-iris" v-model="selectedIrisDeviceId" class="mt-1 block w-full px-3 py-2 border border-gray-300 bg-white rounded-md shadow-sm">
            <option v-for="device in videoDevices" :key="device.deviceId" :value="device.deviceId">
              {{ device.label || `Camera ${videoDevices.indexOf(device) + 1}` }}
            </option>
          </select>
        </div>
        
        <div class="relative w-full aspect-square">
            <div class="relative w-full h-full bg-gray-100 rounded-full overflow-hidden border-2 border-gray-200 flex items-center justify-center">
                <template v-if="currentStep === 'face'">
                    <div v-if="faceState === 'idle'" class="text-center text-gray-500 p-4">Click "Start Camera" to begin.</div>
                    <video v-show="faceState === 'streaming'" ref="faceVideo" autoplay playsinline class="w-full h-full object-cover transform -scale-x-100"></video>
                    <img v-if="faceState === 'captured'" :src="facePreview" class="w-full h-full object-cover">
                </template>
                 <template v-if="currentStep === 'iris'">
                    <div v-if="irisState === 'idle'" class="text-center text-gray-500 p-4">Camera is starting...</div>
                    <video v-show="irisState === 'streaming'" ref="irisVideo" autoplay playsinline class="w-full h-full object-cover transform -scale-x-100"></video>
                    <img v-if="irisState === 'captured'" :src="irisPreview" class="w-full h-full object-cover">
                </template>
            </div>
            
            <div v-if="currentScannerState === 'streaming' && currentStep === 'face'" class="absolute inset-0 pointer-events-none">
                <svg class="w-full h-full" viewBox="0 0 100 100"><defs><mask id="faceMaskModal"><rect width="100" height="100" fill="white"></rect><ellipse cx="50" cy="48" rx="28" ry="38" fill="black"></ellipse></mask></defs><rect width="100" height="100" fill="rgba(255, 255, 255, 0.6)" mask="url(#faceMaskModal)"></rect></svg>
            </div>
            <transition enter-active-class="ease-out duration-150" enter-from-class="opacity-0" enter-to-class="opacity-100" leave-active-class="ease-in duration-150" leave-from-class="opacity-100" leave-to-class="opacity-0">
              <div v-if="showFlash" class="absolute inset-0 bg-white rounded-full"></div>
            </transition>
        </div>

        <div class="flex gap-2 mt-4 justify-center h-12 items-center">
            <template v-if="currentStep === 'face'">
                <button v-if="faceState === 'idle'" @click="startWebcam('face')" :disabled="!selectedFaceDeviceId" class="bg-blue-600 text-white px-5 py-2 rounded-lg font-semibold hover:bg-blue-700 transition shadow-sm disabled:bg-gray-400">Start Camera</button>
                <button v-if="faceState === 'streaming'" @click="capturePhoto('face')" class="bg-green-600 text-white px-5 py-2 rounded-lg font-semibold hover:bg-green-700 transition shadow-sm">Capture Photo</button>
                <button v-if="faceState === 'captured'" @click="resetScan('face')" class="bg-gray-200 text-gray-700 px-5 py-2 rounded-lg font-semibold hover:bg-gray-300 transition">Retake Face</button>
            </template>
            <template v-if="currentStep === 'iris'">
                <button v-if="irisState === 'idle'" class="text-gray-500" disabled>Starting camera...</button>
                <button v-if="irisState === 'streaming'" @click="capturePhoto('iris')" class="bg-green-600 text-white px-5 py-2 rounded-lg font-semibold hover:bg-green-700 transition shadow-sm">Capture Iris</button>
                <button v-if="irisState === 'captured'" @click="resetScan('iris'); startWebcam('iris')" class="bg-gray-200 text-gray-700 px-5 py-2 rounded-lg font-semibold hover:bg-gray-300 transition">Retake Iris</button>
            </template>
        </div>
      </div>
      
      <p v-if="errorMessage" class="text-red-600 bg-red-100 text-center p-3 rounded-lg mt-6 text-sm">{{ errorMessage }}</p>

      <div class="flex justify-end gap-4 mt-8 pt-4 border-t">
        <button @click="$emit('close')" class="bg-gray-200 text-gray-800 px-6 py-2 rounded-lg font-semibold hover:bg-gray-300 transition">Cancel</button>
        <button @click="verifyIdentity" :disabled="isVerifyDisabled" class="bg-blue-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-blue-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed flex items-center">
          <svg v-if="isLoading" class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
          {{ isLoading ? 'Verifying...' : 'Verify Identity' }}
        </button>
      </div>
    </div>
  </div>
</template>