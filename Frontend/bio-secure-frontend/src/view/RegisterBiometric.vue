// in views/RegisterBiometric.vue

<script setup>
import { ref, onMounted, onBeforeUnmount, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();

const customerId = ref(route.params.id);
const faceState = ref('idle'); // idle -> streaming -> captured
const irisState = ref('idle'); // idle -> streaming -> captured

const selectedFaceFile = ref(null);
const facePreview = ref(null);
const selectedIrisFile = ref(null);
const irisPreview = ref(null);

const isLoading = ref(false);
const errorMessage = ref('');

let faceStream = null;
let irisStream = null;
const faceVideo = ref(null);
const irisVideo = ref(null);

// --- Webcam Functions ---
function stopStream(stream) {
  if (stream) stream.getTracks().forEach(track => track.stop());
}

async function startWebcam(type) {
  const state = type === 'face' ? faceState : irisState;
  const videoEl = type === 'face' ? faceVideo : irisVideo;
  stopStream(type === 'face' ? faceStream : irisStream);

  state.value = 'streaming';
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { width: 480, height: 480 }, audio: false });
    if (type === 'face') faceStream = stream;
    else irisStream = stream;
    videoEl.value.srcObject = stream;
  } catch (err) {
    errorMessage.value = `Unable to access webcam: ${err.message}`;
    state.value = 'idle';
  }
}

function capturePhoto(type) {
  const videoEl = type === 'face' ? faceVideo.value : irisVideo.value;
  const stream = type === 'face' ? faceStream : irisStream;
  if (!videoEl || !stream) return;

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

// Automatically start the face webcam when the page loads
onMounted(() => {
  if (faceVideo.value) {
    startWebcam('face');
  }
});

// Clean up streams when leaving the page
onBeforeUnmount(() => {
  stopStream(faceStream);
  stopStream(irisStream);
});

// --- Submission Logic ---
const isSubmitDisabled = computed(() => {
  return isLoading.value || !selectedFaceFile.value; // At a minimum, face is required
});

async function submitBiometrics() {
  if (isSubmitDisabled.value) return;
  isLoading.value = true;
  errorMessage.value = '';

  const formData = new FormData();
  formData.append('national_id', customerId.value);
  if (selectedFaceFile.value) formData.append('face_image', selectedFaceFile.value);
  if (selectedIrisFile.value) formData.append('iris_image', selectedIrisFile.value);

  try {
    const res = await fetch('http://localhost:8000/register-biometric', {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Failed to submit biometrics.');
    
    alert('Biometrics registered successfully!');
    router.push(`/info/${customerId.value}`); // Navigate to customer info page on success

  } catch (err) {
    errorMessage.value = err.message;
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 py-12 px-4 flex flex-col items-center">
    <div class="w-full max-w-2xl">
      <h1 class="text-3xl font-bold text-gray-800 text-center">Biometric Registration</h1>
      <p class="text-lg text-gray-600 text-center mt-2 mb-8">Please provide a clear photo of your face and iris.</p>
      
      <div class="grid grid-cols-1 md:grid-cols-2 gap-8 bg-white p-8 rounded-2xl shadow-xl">
        <div class="flex flex-col items-center">
          <h3 class="font-semibold text-gray-700 mb-3 text-xl">Face Scan (Required)</h3>
          <div class="relative w-64 h-64 bg-gray-100 rounded-full overflow-hidden border-2 flex items-center justify-center">
            <video v-show="faceState === 'streaming'" ref="faceVideo" autoplay playsinline class="w-full h-full object-cover transform -scale-x-100"></video>
            <img v-if="faceState === 'captured'" :src="facePreview" class="w-full h-full object-cover">
          </div>
          <div class="flex gap-2 mt-4">
            <button v-if="faceState === 'streaming'" @click="capturePhoto('face')" class="bg-blue-600 text-white px-5 py-2 rounded-lg font-semibold hover:bg-blue-700 transition shadow-sm">Capture Face</button>
            <button v-if="faceState === 'captured'" @click="startWebcam('face')" class="bg-gray-200 text-gray-700 px-5 py-2 rounded-lg font-semibold hover:bg-gray-300 transition">Retake</button>
          </div>
        </div>

        <div v-if="false" class="flex flex-col items-center">
          <h3 class="font-semibold text-gray-700 mb-3 text-xl">Iris Scan (Optional)</h3>
          <div class="relative w-64 h-64 bg-gray-100 rounded-full overflow-hidden border-2 flex items-center justify-center">
            <div v-if="irisState === 'idle'" class="text-center text-gray-500">
              <svg class="w-16 h-16 mx-auto opacity-50" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"></path></svg>
            </div>
            <video v-show="irisState === 'streaming'" ref="irisVideo" autoplay playsinline class="w-full h-full object-cover transform -scale-x-100"></video>
            <img v-if="irisState === 'captured'" :src="irisPreview" class="w-full h-full object-cover">
          </div>
          <div class="flex gap-2 mt-4">
            <button v-if="irisState === 'idle'" @click="startWebcam('iris')" class="bg-blue-600 text-white px-5 py-2 rounded-lg font-semibold hover:bg-blue-700 transition shadow-sm">Start Iris Cam</button>
            <button v-if="irisState === 'streaming'" @click="capturePhoto('iris')" class="bg-green-600 text-white px-5 py-2 rounded-lg font-semibold hover:bg-green-700 transition shadow-sm">Capture Iris</button>
            <button v-if="irisState === 'captured'" @click="startWebcam('iris')" class="bg-gray-200 text-gray-700 px-5 py-2 rounded-lg font-semibold hover:bg-gray-300 transition">Retake</button>
          </div>
        </div>
      </div>

      <p v-if="errorMessage" class="text-red-600 bg-red-100 text-center p-3 rounded-lg mt-6 text-sm">{{ errorMessage }}</p>

      <div class="flex justify-center mt-8">
        <button @click="submitBiometrics" :disabled="isSubmitDisabled" class="bg-green-600 hover:bg-green-700 text-white font-bold text-lg px-16 py-3 rounded-full shadow-lg transition-transform transform hover:scale-105 disabled:bg-gray-400 disabled:cursor-not-allowed">
          <span v-if="isLoading">Submitting...</span>
          <span v-else>Finish Registration</span>
        </button>
      </div>

    </div>
  </div>
</template>