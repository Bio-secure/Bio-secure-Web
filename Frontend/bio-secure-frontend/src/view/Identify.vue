<script setup>
import { ref } from 'vue';

const selectedFile = ref(null);
const preview = ref(null);
const result = ref(null);
const matchImageUrl = ref(null);

function connectWebcam() {
  document.getElementById("fileInput").click();
}

function handleFileChange(event) {
  const file = event.target.files[0];
  if (file) {
    selectedFile.value = file;
    preview.value = URL.createObjectURL(file);
    result.value = null;
    matchImageUrl.value = null;
  }
}

async function verify() {
  if (!selectedFile.value) {
    alert("Please upload a face image first.");
    return;
  }

  const formData = new FormData();
  formData.append("image", selectedFile.value);

  try {
    const res = await fetch("http://localhost:8000/identify", {
      method: "POST",
      body: formData
    });

    if (!res.ok) {
      if (res.status === 500) {
        result.value = "Error: Something went wrong. Status 500."
      } else {
        result.value = `Error: ${res.status} ${res.statusText}`
      }
      return
    }

    const data = await res.json();
    result.value = data.identity || "No match found";
    matchImageUrl.value = data.image_url || null;
  } catch (err) {
    console.error("Network or unexpected error:", err);
    result.value = "Error during verification.";
  }
}

function connectIrisCamera() {
  alert("Iris recognition is not implemented yet.");
}
</script>

<template>
  <div class="min-h-screen from-slate-100 to-slate-200 py-12 px-4 flex flex-col items-center space-y-10">
    <h1 class="text-3xl font-bold text-gray-800">Personal identify</h1>

    <!-- Hidden file input -->
    <input id="fileInput" type="file" accept="image/*" class="hidden" @change="handleFileChange" />

    <!-- Scan options -->
    <div class="flex gap-12">
      <!-- Face recognition -->
      <div
        class="w-60 h-60 bg-white rounded-2xl flex items-center justify-center border border-gray-300 shadow-lg hover:shadow-2xl transition cursor-pointer"
        @click="connectWebcam"
      >
        <img src="../assets/FaceScan.png" alt="Face Recognition" class="w-48 h-48" />
      </div>

      <!-- Iris recognition -->
      <div
        class="w-60 h-60 bg-white rounded-2xl flex items-center justify-center border border-gray-300 shadow-lg hover:shadow-2xl transition cursor-pointer"
        @click="connectIrisCamera"
      >
        <img src="../assets/IrisScan.png" alt="Iris Recognition" class="w-48 h-48" />
      </div>
    </div>

    <!-- Preview images side-by-side -->
    <div v-if="preview || matchImageUrl" class="flex justify-center items-start gap-16 mt-8">
      <div v-if="preview" class="text-center">
        <p class="text-lg font-medium text-gray-700">Uploaded Image</p>
        <img :src="preview" alt="Uploaded" class="w-48 h-48 object-cover rounded-lg shadow-md mt-2 border" />
      </div>

      <div v-if="matchImageUrl" class="text-center">
        <p class="text-lg font-medium text-green-700">Matched Image</p>
        <img :src="matchImageUrl" alt="Matched" class="w-48 h-48 object-cover rounded-lg shadow-md mt-2 border border-green-400" />
      </div>
    </div>

    <!-- Verify button -->
    <button
      @click="verify"
      class="bg-blue-500 hover:bg-blue-600 text-white font-semibold text-lg px-8 py-3 rounded-full shadow-md transition mt-6"
    >
      VERIFY
    </button>

    <!-- Result Message -->
    <div v-if="result" class="mt-4 px-6 py-2 rounded-lg text-lg font-semibold"
      :class="{
        'bg-green-100 text-green-700': result !== 'No match found' && !result.startsWith('Error'),
        'bg-red-100 text-red-700': result === 'No match found' || result.startsWith('Error')
      }">
      {{ result }}
    </div>
  </div>
</template>
