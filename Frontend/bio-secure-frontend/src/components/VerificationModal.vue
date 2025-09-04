<script setup>
import { ref, computed, onBeforeUnmount,watch } from "vue";

const currentStep = ref(1);

function nextStep() {
  currentStep.value = 2;
}

// --- Props & Emits ---
const props = defineProps({
  isOpen: { type: Boolean, default: false },
  customerId: { type: [String, Number], required: true },
  verificationMode: { type: String, default: "face" }
});
const emit = defineEmits(["close", "verification-success", "verification-fail"]);

// --- Face states ---
const faceState = ref("idle");
const faceStream = ref(null);
const faceVideo = ref(null);
const selectedFaceFile = ref(null);
const facePreview = ref(null);

// --- Iris states ---
const irisState = ref("idle");
const irisPreview = ref(null);
const lFile = ref(null);
const rFile = ref(null);
let websocket = null;

// --- Global states ---
const errorMessage = ref("");
const isLoading = ref(false);

// --- Backend URL ---
const MAIN_BACKEND_URL = "http://localhost:8000";

// Stop stream helper
function stopStream(stream) {
  websocket?.send("stop");
  setTimeout(() => websocket?.close(), 100);
  if (stream) {
    const tracks = stream.getTracks();
    tracks.forEach((track) => track.stop());
  }
}

// FACE CAMERA
async function startFaceWebcam() {
  stopStream(faceStream.value);
  try {
    faceStream.value = await navigator.mediaDevices.getUserMedia({ video: true });
    if (faceVideo.value) {
      faceVideo.value.srcObject = faceStream.value;
    }
    faceState.value = "streaming";
  } catch (err) {
    errorMessage.value = `Unable to access webcam: ${err.message}`;
  }
}

function captureFace() {
  const video = faceVideo.value;
  if (!video) return;
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  canvas.toBlob(
    (blob) => {
      selectedFaceFile.value = new File([blob], "face.jpg", {
        type: "image/jpeg",
      });
      facePreview.value = URL.createObjectURL(blob);
      faceState.value = "captured";
      stopStream(faceStream.value);
    },
    "image/jpeg"
  );
}

// IRIS CAPTURE (via WebSocket)
function initWebSocket() {
  websocket = new WebSocket("ws://127.0.0.1:5000/Iris");

  websocket.onopen = () => {
    irisState.value = "streaming";
    websocket.send("connect");
  };

  websocket.onmessage = (evt) => {
    const parts = evt.data.split(",");
    if (parts[0] === "irises") {
      const leyeData = `data:image/bmp;base64,${parts[1]}`;
      const reyeData = `data:image/bmp;base64,${parts[2]}`;

      lFile.value = new File([dataURItoBlob(leyeData)], "left_iris.bmp", {
        type: "image/bmp",
      });
      rFile.value = new File([dataURItoBlob(reyeData)], "right_iris.bmp", {
        type: "image/bmp",
      });
      irisPreview.value = leyeData || reyeData;

      irisState.value = "captured";
      websocket?.send("stop");
      setTimeout(() => websocket?.close(), 100);
    }
  };

  websocket.onerror = () => {
    errorMessage.value = "Failed to connect to NIR scanner.";
    irisState.value = "idle";
  };
}

function captureIris() {
  if (websocket) websocket.send("BOTH_EYES");
}

const dataURItoBlob = (dataURI) => {
  const byteString = atob(dataURI.split(",")[1]);
  const mimeString = dataURI.split(",")[0].split(":")[1].split(";")[0];
  const ab = new ArrayBuffer(byteString.length);
  const ia = new Uint8Array(ab);
  for (let i = 0; i < byteString.length; i++) ia[i] = byteString.charCodeAt(i);
  return new Blob([ab], { type: mimeString });
};

// VERIFICATION
async function verifyIdentity() {
  if (props.verificationMode === "face") {
    if (!selectedFaceFile.value) {
      errorMessage.value = "Please capture face before verifying.";
      return;
    }
  } else if (props.verificationMode === "full") {
    if (!selectedFaceFile.value || (!lFile.value && !rFile.value)) {
      errorMessage.value = "Please capture both face and iris before verifying.";
      return;
    }
  }

  isLoading.value = true;
  errorMessage.value = "";
  const formData = new FormData();
  formData.append("national_id", props.customerId);
  formData.append("face_image", selectedFaceFile.value);

  if (lFile.value) {
    formData.append("left_image", lFile.value);
  }
  if (rFile.value) {
    formData.append("right_image", rFile.value);
  }

  try {
    const res = await fetch(`${MAIN_BACKEND_URL}/verify`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Verification failed");

    if (data.verified) emit("verification-success");
    else emit("verification-fail", data.message || "Biometrics did not match.");
  } catch (err) {
    errorMessage.value = err.message;
  } finally {
    isLoading.value = false;
  }
}

const isVerifyDisabled = computed(() => {
  if (props.verificationMode === "face") {
    return faceState.value !== "captured";
  }
  return !(faceState.value === "captured" && irisState.value === "captured");
});

function resetVerification() {
  faceState.value = "idle";
  facePreview.value = null;
  selectedFaceFile.value = null;
  stopStream(faceStream.value);

  irisState.value = "idle";
  irisPreview.value = null;
  lFile.value = null;
  rFile.value = null;

  errorMessage.value = "";
  isLoading.value = false;
  currentStep.value = 1;
}

watch(
  () => props.isOpen,
  (newVal) => {
    if (newVal) {
      // modal opened → fresh start
      resetVerification();
    } else {
      // modal closed → cleanup resources
      stopStream(faceStream.value);
      websocket?.close();
    }
  }
);

onBeforeUnmount(() => {
  stopStream(faceStream.value);
  websocket?.close();
});
</script>

<template>
  <!-- BACKDROP -->
  <div
    v-if="isOpen"
    class="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
  >
    <!-- POPUP CARD -->
    <div
      class="p-6 bg-white rounded-2xl shadow-2xl w-full max-w-md relative"
    >
      <!-- CLOSE BUTTON -->
      <button
        @click="$emit('close')"
        class="absolute top-3 right-3 text-gray-500 hover:text-gray-800"
      >
        ✕
      </button>

      <h2 class="text-xl font-bold mb-4">Identity Verification</h2>

      <!-- FACE STEP -->
      <div v-if="currentStep === 1" class="mb-6">
        <h3 class="font-semibold mb-2">Step 1: Face Scan</h3>
        <div
          class="w-full aspect-square bg-gray-200 flex items-center justify-center rounded-lg overflow-hidden"
        >
          <video
            ref="faceVideo"
            autoplay
            playsinline
            v-show="faceState === 'streaming'"
            class="w-full h-full"
          ></video>
          <img
            v-if="faceState === 'captured'"
            :src="facePreview"
            class="w-full h-full object-cover"
          />
          <p v-if="faceState === 'idle'" class="text-gray-500">
            Camera is off
          </p>
        </div>

        <div class="mt-3 flex gap-2">
          <button
            v-if="faceState === 'idle'"
            @click="startFaceWebcam"
            class="btn"
          >
            Start Camera
          </button>
          <button
            v-if="faceState === 'streaming'"
            @click="captureFace"
            class="btn btn-green"
          >
            Capture Face
          </button>
          <button
            v-if="faceState === 'captured'"
            @click="nextStep"
            class="btn btn-blue"
          >
            Continue
          </button>
        </div>
      </div>

      <!-- IRIS STEP -->
      <div v-if="currentStep === 2" class="mb-6">
        <h3 class="font-semibold mb-2">Step 2: Iris Scan</h3>
        <div
          class="w-full aspect-square bg-gray-200 flex items-center justify-center rounded-lg overflow-hidden"
        >
          <img
            v-if="irisState === 'captured'"
            :src="irisPreview"
            class="object-contain w-full h-full"
          />
          <p v-if="irisState === 'streaming'" class="text-gray-500">
            Streaming from NIR...
          </p>
          <p v-if="irisState === 'idle'" class="text-gray-500">
            Click connect to begin
          </p>
        </div>

        <div class="mt-3 flex gap-2">
          <button
            v-if="irisState === 'idle'"
            @click="initWebSocket"
            class="btn"
          >
            Connect
          </button>
          <button
            v-if="irisState === 'streaming'"
            @click="captureIris"
            class="btn btn-green"
          >
            Capture Iris
          </button>
          <button
            v-if="irisState === 'captured'"
            @click="verifyIdentity"
            :disabled="isLoading"
            class="btn btn-blue"
          >
            {{ isLoading ? "Verifying..." : "Verify" }}
          </button>
        </div>
      </div>

      <!-- ERRORS -->
      <p v-if="errorMessage" class="text-red-600">{{ errorMessage }}</p>

      <!-- FOOTER BUTTONS -->
      <div class="mt-4 flex justify-end gap-2">
        <button @click="$emit('close')" class="btn btn-gray">Cancel</button>
      </div>
    </div>
  </div>
</template>
