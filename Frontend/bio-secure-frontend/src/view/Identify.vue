<script setup>
function connectWebcam() {
  alert("Preparing webcam for facial recognition...");
  // TODO: Add actual webcam connection logic
}

function connectIrisCamera() {
  alert("Preparing iris camera...");
  // TODO: Add iris camera logic
}

function verify() {
  alert("Verifying...");
  // TODO: Add verification logic
}
</script>

<template>
  <div class="flex flex-col items-center justify-center min-h-screen space-y-12">
    <!-- Scan options -->
    <div class="flex space-x-16">
      <!-- Face recognition -->
      <div
        class="w-60 h-60 bg-white rounded-xl flex items-center justify-center border-2 border-black shadow-md hover:shadow-xl cursor-pointer"
        @click="connectWebcam"
      >
        <img src="../assets/FaceScan.png" alt="Face Recognition" class="w-52 h-52" />
      </div>

      <!-- Iris recognition -->
      <div
        class="w-60 h-60 bg-white rounded-xl flex items-center justify-center border-2 border-black shadow-md hover:shadow-xl cursor-pointer"
        @click="connectIrisCamera"
      >
        <img src="../assets/IrisScan.png" alt="Iris Recognition" class="w-52 h-52" />
      </div>
    </div>

    <!-- Verify button -->
    <button
      @click="verify"
      class="bg-blue-400 hover:bg-blue-500 text-black font-bold text-xl px-12 py-4 rounded-lg shadow-md"
    >
      VERIFY
    </button>
  </div>
</template>