<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { CheckCircleIcon } from '@heroicons/vue/24/solid';

const route = useRoute();
const router = useRouter();

const customerId = ref<string | string[]>(route.params.id);
const isLoading = ref(false);
const errorMessage = ref('');
const isSubmitted = ref(false);

// --- WebSocket State ---
const wsUri = "ws://127.0.0.1:5000/Iris";
let websocket: WebSocket | null = null;

const leye = ref<string>("");
const reye = ref<string>("");
const checkL = ref<boolean>(true);
const checkR = ref<boolean>(true);

// Files to be submitted
const lFile = ref<File | null>(null);
const rFile = ref<File | null>(null);

// --- Helper function to convert base64 to File object ---
const dataURItoBlob = (dataURI: string) => {
    const byteString = atob(dataURI.split(',')[1]);
    const mimeString = dataURI.split(',')[0].split(':')[1].split(';')[0];
    const ab = new ArrayBuffer(byteString.length);
    const ia = new Uint8Array(ab);
    for (let i = 0; i < byteString.length; i++) {
        ia[i] = byteString.charCodeAt(i);
    }
    return new Blob([ab], { type: mimeString });
};

// --- WebSocket Logic ---
const initWebSocket = () => {
    try {
        if (websocket && websocket.readyState === 1) {
            websocket.close();
        }
        websocket = new WebSocket(wsUri);

        websocket.onopen = () => {
            console.log("CONNECTED");
            websocket?.send("connect");
        };

        websocket.onclose = () => {
            console.log("DISCONNECTED");
        };

        websocket.onmessage = (evt: MessageEvent) => {
            const parts = evt.data.split(",");
            const msg_type = parts[0];

            if (msg_type === "irises") {
                leye.value = `data:image/bmp;base64,${parts[1]}`;
                reye.value = `data:image/bmp;base64,${parts[2]}`;
                lFile.value = new File([dataURItoBlob(leye.value)], 'left_iris.bmp', { type: 'image/bmp' });
                rFile.value = new File([dataURItoBlob(reye.value)], 'right_iris.bmp', { type: 'image/bmp' });
            } else if (msg_type === "irise_L") {
                leye.value = `data:image/bmp;base64,${parts[1]}`;
                reye.value = "";
                lFile.value = new File([dataURItoBlob(leye.value)], 'left_iris.bmp', { type: 'image/bmp' });
                rFile.value = null;
            } else if (msg_type === "irise_R") {
                reye.value = `data:image/bmp;base64,${parts[1]}`;
                leye.value = "";
                rFile.value = new File([dataURItoBlob(reye.value)], 'right_iris.bmp', { type: 'image/bmp' });
                lFile.value = null;
            } else {
                console.log("Unknown message:", evt.data);
            }
        };

        websocket.onerror = (evt) => {
            console.error("ERROR:", evt);
            errorMessage.value = 'Websocket connection failed.';
        };
    } catch (exception) {
        console.error("EXCEPTION:", exception);
        errorMessage.value = 'An error occurred with the websocket.';
    }
};

const capture = () => {
    leye.value = "";
    reye.value = "";
    lFile.value = null;
    rFile.value = null;
    errorMessage.value = '';

    if (websocket) {
        if (checkL.value && checkR.value) {
            websocket.send("BOTH_EYES");
            console.log(">>> Sent: BOTH_EYES");
        } else if (checkL.value && !checkR.value) {
            websocket.send("LEFT_EYE");
            console.log(">>> Sent: LEFT_EYE");
        } else if (checkR.value && !checkL.value) {
            websocket.send("RIGHT_EYE");
            console.log(">>> Sent: RIGHT_EYE");
        } else {
            errorMessage.value = 'Please select at least one eye to capture.';
        }
    }
};

const stopCapture = () => {
    websocket?.send("stop");
};

const stopWebSocket = () => {
    if (websocket) {
        websocket.send("close");
        websocket.close();
    }
};

onMounted(() => {
    initWebSocket();
});

onUnmounted(() => {
    stopWebSocket();
});

// --- Submission Logic ---
const isSubmitDisabled = computed(() => {
    const hasCapturedImage = lFile.value || rFile.value;
    return isLoading.value || !hasCapturedImage;
});

async function submitBiometrics() {
    if (isSubmitDisabled.value) return;
    isLoading.value = true;
    errorMessage.value = '';

    const formData = new FormData();
    formData.append('national_id', Array.isArray(customerId.value) ? customerId.value[0] : customerId.value);
    if (lFile.value) {
        formData.append('left_image', lFile.value);
    }
    if (rFile.value) {
        formData.append('right_image', rFile.value);
    }

    try {
        const res = await fetch('http://localhost:8000/register-biometric-iris', {
            method: 'POST',
            body: formData,
        });
        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || 'Failed to submit biometrics.');
        }

        isSubmitted.value = true;
        console.log('Iris biometrics registered successfully!');
        setTimeout(() => {
            router.push(`/info/${customerId.value}`);
        }, 2000);
    } catch (err: any) {
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
        <h1 class="text-3xl font-bold text-gray-800">Iris Registration</h1>
        <p class="text-lg text-gray-600 mt-2 mb-8">Scan your irises to securely register your identity.</p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-8 bg-white p-8 rounded-2xl shadow-xl">
        <div class="flex flex-col items-center">
          <h3 class="font-semibold text-gray-700 mb-3 text-xl">Right Iris</h3>
          <div class="relative w-full h-80 bg-gray-200 overflow-hidden border-4 border-white shadow-inner flex items-center justify-center rounded-xl">
            <img v-if="reye" :src="reye" alt="Right Eye" class="w-full h-full object-contain">
            <div v-else class="text-center text-gray-500">
              <p>Waiting for capture...</p>
            </div>
          </div>
          <p v-if="reye" class="text-green-600 font-semibold mt-2">Captured!</p>
          <label class="flex items-center space-x-2 cursor-pointer mt-4">
            <input type="checkbox" v-model="checkR" class="form-checkbox h-5 w-5 text-blue-600">
            <span class="text-gray-700 font-semibold">Include Right Eye</span>
          </label>
        </div>

        <div class="flex flex-col items-center">
          <h3 class="font-semibold text-gray-700 mb-3 text-xl">Left Iris</h3>
          <div class="relative w-full h-80 bg-gray-200 overflow-hidden border-4 border-white shadow-inner flex items-center justify-center rounded-xl">
            <img v-if="leye" :src="leye" alt="Left Eye" class="w-full h-full object-contain">
            <div v-else class="text-center text-gray-500">
              <p>Waiting for capture...</p>
            </div>
          </div>
          <p v-if="leye" class="text-green-600 font-semibold mt-2">Captured!</p>
          <label class="flex items-center space-x-2 cursor-pointer mt-4">
            <input type="checkbox" v-model="checkL" class="form-checkbox h-5 w-5 text-blue-600">
            <span class="text-gray-700 font-semibold">Include Left Eye</span>
          </label>
        </div>
      </div>

      <div class="flex flex-col items-center mt-8">
        <div class="flex gap-4">
          <button @click="capture" :disabled="!checkL && !checkR" class="bg-blue-600 text-white px-8 py-3 rounded-lg font-bold text-lg hover:bg-blue-700 transition shadow-md disabled:bg-gray-400">
            Capture Iris
          </button>
          <button @click="stopCapture" class="bg-red-500 text-white px-8 py-3 rounded-lg font-bold text-lg hover:bg-red-600 transition shadow-md">
            Stop Capture
          </button>
        </div>
      </div>

      <p v-if="errorMessage" class="text-red-600 bg-red-100 text-center p-3 rounded-lg mt-6 text-sm">{{ errorMessage }}</p>

      <div class="flex justify-center mt-8">
        <button @click="submitBiometrics" :disabled="isSubmitDisabled" class="bg-green-600 hover:bg-green-700 text-white font-bold text-lg px-16 py-3 rounded-full shadow-lg transition-transform transform hover:scale-105 disabled:bg-gray-400 disabled:cursor-not-allowed">
          <span v-if="isLoading">Submitting...</span>
          <span v-else-if="isSubmitted">✅ Done! Redirecting...</span>
          <span v-else>Finish Facial Registration</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.row {
    display: flex;
}
.column {
    flex: 33.33%;
    padding: 5px;
}
</style>
