<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { CheckCircleIcon } from '@heroicons/vue/24/solid';

const route = useRoute();
const router = useRouter();

const customerId = ref(route.params.id);
const faceState = ref('idle');
const showFlash = ref(false);

const selectedFaceFile = ref(null);
const facePreview = ref(null);

const isLoading = ref(false);
const errorMessage = ref('');

let faceStream = null;
const faceVideo = ref(null);

const videoDevices = ref([]);
const selectedFaceDeviceId = ref(''); // <-- NEW: State for selected face camera

// --- Webcam Functions ---

async function getVideoDevices() {
  try {
    await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
    const devices = await navigator.mediaDevices.enumerateDevices();
    videoDevices.value = devices.filter(device => device.kind === 'videoinput');
    
    // Set smart defaults if cameras are available
    if (videoDevices.value.length > 0) {
      selectedFaceDeviceId.value = videoDevices.value[0].deviceId;
    }
  } catch (err) {
    console.error("Could not get video devices:", err);
  }
}

function stopStream(stream) {
  if (stream) stream.getTracks().forEach(track => track.stop());
}

async function startWebcam(type) {
  const state = type === 'face' ? faceState : irisState;
  const videoEl = type === 'face' ? faceVideo : irisVideo;
  
  if (type === 'face') stopStream(faceStream);
  else stopStream(irisStream);

  state.value = 'streaming';
  errorMessage.value = '';
  try {
    // --- UPDATED: Logic now handles both face and iris device selection ---
    const deviceId = type === 'face' ? selectedFaceDeviceId.value : selectedIrisDeviceId.value;
    
    const constraints = { 
      video: { 
        width: 480, height: 480, 
        facingMode: 'user',
        deviceId: deviceId ? { exact: deviceId } : undefined
      }, 
      audio: false 
    };
    
    const stream = await navigator.mediaDevices.getUserMedia(constraints);
    if (type === 'face') {
      faceStream = stream;
    }
    videoEl.value.srcObject = stream;
  } catch (err) {
    errorMessage.value = `Unable to access ${type} camera: ${err.message}`;
    state.value = 'idle';
  }
}

function capturePhoto(type) {
  const videoEl = type === 'face' ? faceVideo.value : irisVideo.value;
  const stream = type === 'face' ? faceStream : irisStream;
  if (!videoEl || !stream) return;

  if (type === 'face') {
    showFlash.value = true;
    setTimeout(() => { showFlash.value = false; }, 150);
  }

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
      faceState.value = 'captured';
    } else {
      selectedIrisFile.value = new File([blob], 'iris.jpg', { type: 'image/jpeg' });
      irisPreview.value = URL.createObjectURL(blob);
      irisState.value = 'captured';
    }
    stopStream(stream);
  }, 'image/jpeg');
}

onMounted(() => {
  getVideoDevices();
  // We no longer start the webcam automatically, letting the user choose first.
});

onBeforeUnmount(() => {
  stopStream(faceStream);
});

// --- Submission Logic ---
const isSubmitDisabled = computed(() => {
  return isLoading.value || faceState.value !== 'captured';
});

async function submitBiometrics() {
  if (isSubmitDisabled.value) return;
  isLoading.value = true;
  errorMessage.value = '';

  const formData = new FormData();
  formData.append('national_id', customerId.value);
  formData.append('face_image', selectedFaceFile.value);

  try {
    const res = await fetch('http://localhost:8000/register-biometric-face', {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to submit biometrics.');
    
    console.log('Biometrics registered successfully!');
    router.push(`/register-biometric-iris/${customerId.value}`);

  } catch (err) {
    errorMessage.value = err.message;
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div class="min-h-screen py-12 px-4 flex flex-col items-center">
    <div class="w-full max-w-4xl">
      <div class="text-center">
        <h1 class="text-3xl font-bold text-gray-800">Biometric Registration</h1>
        <p class="text-lg text-gray-600 mt-2 mb-8">Select a camera and provide a clear photo for each biometric type.</p>
      </div>
      
      <div class="grid grid-cols-1 gap-8 bg-white p-8 rounded-2xl shadow-xl">
        
        <div class="flex flex-col items-center">
          <h3 class="font-semibold text-gray-700 mb-3 text-xl">Face Scan</h3>
          
          <div class="mb-3 w-full max-w-xs">
            <label for="face-camera" class="block text-sm font-medium text-gray-700">Select Camera</label>
            <select id="face-camera" v-model="selectedFaceDeviceId" class="mt-1 block w-full px-3 py-2 border border-gray-300 bg-white rounded-md shadow-sm">
              <option disabled value="">Please select a camera</option>
              <option v-for="device in videoDevices" :key="device.deviceId" :value="device.deviceId">
                {{ device.label || `Camera ${videoDevices.indexOf(device) + 1}` }}
              </option>
            </select>
          </div>

          <div class="relative w-80 h-80">
             <div class="relative w-full h-full bg-gray-200 rounded-full overflow-hidden border-4 border-white shadow-inner flex items-center justify-center">
              <div v-if="faceState === 'idle'" class="text-center text-gray-500"><p>Camera is off</p></div>
              <video v-show="faceState === 'streaming'" ref="faceVideo" autoplay playsinline class="w-full h-full object-cover transform -scale-x-100"></video>
              <img v-if="faceState === 'captured'" :src="facePreview" class="w-full h-full object-cover">
            </div>
            <div v-if="faceState === 'streaming'" class="absolute inset-0 pointer-events-none"><svg class="w-full h-full" viewBox="0 0 100 100"><defs><mask id="faceMask"><rect width="100" height="100" fill="white"></rect><ellipse cx="50" cy="48" rx="28" ry="38" fill="black"></ellipse></mask></defs><rect width="100" height="100" fill="rgba(255, 255, 255, 0.6)" mask="url(#faceMask)"></rect></svg></div>
            <div v-if="faceState === 'captured'" class="absolute inset-0 bg-green-500 bg-opacity-30 rounded-full flex items-center justify-center"><CheckCircleIcon class="w-24 h-24 text-white opacity-90" /></div>
            <transition enter-active-class="ease-out duration-150" enter-from-class="opacity-0" enter-to-class="opacity-100" leave-active-class="ease-in duration-150" leave-from-class="opacity-100" leave-to-class="opacity-0">
              <div v-if="showFlash" class="absolute inset-0 bg-white"></div>
            </transition>
          </div>
          <div class="flex flex-col items-center gap-2 mt-6 w-full max-w-xs">
            <p v-if="faceState === 'captured'" class="text-green-600 font-semibold mb-2">Face Captured!</p>
            <button v-if="faceState === 'idle'" @click="startWebcam('face')" :disabled="!selectedFaceDeviceId" class="w-full bg-blue-600 text-white px-5 py-3 rounded-lg font-bold text-lg hover:bg-blue-700 transition shadow-md disabled:bg-gray-400">Start Camera</button>
            <button v-if="faceState === 'streaming'" @click="capturePhoto('face')" class="w-full bg-blue-600 text-white px-5 py-3 rounded-lg font-bold text-lg hover:bg-blue-700 transition shadow-md">Capture Face</button>
            <button v-if="faceState === 'captured'" @click="startWebcam('face')" class="w-full bg-gray-200 text-gray-700 px-5 py-2 rounded-lg font-semibold hover:bg-gray-300 transition">Retake Photo</button>
          </div>
        </div>
      </div>

      <p v-if="errorMessage" class="text-red-600 bg-red-100 text-center p-3 rounded-lg mt-6 text-sm">{{ errorMessage }}</p>

      <div class="flex justify-center mt-8">
        <button @click="submitBiometrics" :disabled="isSubmitDisabled" class="bg-green-600 hover:bg-green-700 text-white font-bold text-lg px-16 py-3 rounded-full shadow-lg transition-transform transform hover:scale-105 disabled:bg-gray-400 disabled:cursor-not-allowed">
          <span v-if="isLoading">Submitting...</span>
          <span v-else>Finish Iris Registration</span>
        </button>
      </div>
    </div>
  </div>
</template>