<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
import {
  Combobox,
  ComboboxInput,
  ComboboxButton,
  ComboboxOptions,
  ComboboxOption,
} from '@headlessui/vue';
import { CheckIcon, ChevronUpDownIcon } from '@heroicons/vue/20/solid';

const customers = ref([]);
const selectedCustomer = ref(null);
const query = ref('');
const router = useRouter(); // Import and use the router

// Fetch Customers on Component Load
onMounted(async () => {
  try {
    const res = await fetch("http://localhost:8000/customers");
    if (!res.ok) throw new Error("Failed to fetch customers");
    const data = await res.json();
    customers.value = data.map(c => ({ ...c, displayName: `${c.Name} ${c.SurName} (ID: ${c.National_ID})` }));
  } catch (err) {
    console.error("Error fetching customers:", err);
    alert("Could not load customer list from the server.");
  }
});

// Filter customers based on search query
const filteredCustomers = computed(() => {
  if (query.value === '') {
    return customers.value;
  }
  const searchTerm = query.value.toLowerCase();
  return customers.value.filter((customer) => {
    const nameMatch = customer.displayName.toLowerCase().includes(searchTerm);
    const idMatch = String(customer.National_ID).includes(query.value);
    return nameMatch || idMatch;
  });
});

// --- NEW: Navigation Logic ---
function viewAccountDetails() {
// --- File Handling Functions ---
function triggerFaceUpload() {
  document.getElementById("faceFileInput").click();
}

function triggerIrisUpload() {
  document.getElementById("irisFileInput").click();
}

function handleFileChange(event, type) {
  const file = event.target.files[0];
  if (!file) return;

  // Clear previous results when a new file is selected
  result.value = null;
  matchFaceImageUrl.value = null;

  if (type === 'face') {
    verificationType.value = 'face';
    selectedFaceFile.value = file;
    facePreview.value = URL.createObjectURL(file);
    // Clear iris selection if face is chosen
    selectedIrisFile.value = null;
    irisPreview.value = null;
  } else if (type === 'iris') {
    verificationType.value = 'iris';
    selectedIrisFile.value = file;
    irisPreview.value = URL.createObjectURL(file);
    // Clear face selection if iris is chosen
    selectedFaceFile.value = null;
    facePreview.value = null;
  }
}

// Helper function to convert File to Base64
function fileToBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onloadend = () => {
      // Get base64 string without the "data:image/jpeg;base64," prefix
      if (reader.result) {
        resolve(reader.result.split(',')[1]);
      } else {
        reject(new Error("Failed to read file as Data URL."));
      }
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// --- Main Verification Logic ---
async function verifyIdentity() {
  if (!selectedCustomer.value) {
    alert("Please select a customer first.");
    return;
  }
  // Navigate to the InfoPage with the customer's ID as a parameter
  router.push(`/info/${selectedCustomer.value.National_ID}`);
}

const isButtonDisabled = computed(() => {
  return !selectedCustomer.value;
  if (!verificationType.value) {
    alert("Please provide a face or iris scan to verify.");
    return;
  }

  isLoading.value = true;
  result.value = null; // Clear previous results
  matchFaceImageUrl.value = null; // Clear previous face match image (if any)

  try {
    if (verificationType.value === 'face') {
      if (!selectedFaceFile.value) {
        alert("No face image selected for verification.");
        isLoading.value = false;
        return;
      }

      const formData = new FormData();
      formData.append("image", selectedFaceFile.value);
      formData.append("customer_id", selectedCustomer.value.National_ID);

      const res = await fetch("http://localhost:8000/verify", {
        method: "POST",
        body: formData
      });
      const data = await res.json();
      result.value = data; // DeepFace verification response
      matchFaceImageUrl.value = data.image_url || null; // This is for face
      if (!res.ok) {
        alert(`Error: ${data.detail || res.statusText}`);
      }

    } else if (verificationType.value === 'iris') {
      if (!selectedIrisFile.value) {
        alert("No iris image selected for verification.");
        isLoading.value = false;
        return;
      }

      const base64ImageData = await fileToBase64(selectedIrisFile.value);

      const requestBody = {
        user_id: selectedCustomer.value.National_ID.toString(), // Ensure user_id is a string for the backend Pydantic model
        image_data: base64ImageData
      };

      const res = await fetch("http://localhost:8000/authenticate-iris", {
        method: "POST",
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(requestBody)
      });

      const data = await res.json();
      result.value = data; // IrisAuthResponse structure
      
      if (!res.ok) {
        alert(`Error: ${data.detail || res.statusText}`);
      }
    }
  } catch (err) {
    console.error("Network or unexpected error:", err);
    result.value = { message: "Error during verification.", is_authenticated: false, verified: false }; // Ensure properties for template
  } finally {
    isLoading.value = false;
  }
}

// Computed property to determine if verification was successful from the `result` object
const isVerificationSuccessful = computed(() => {
  if (!result.value) return false;
  // Check for both facial recognition's `verified` and iris's `is_authenticated`
  return result.value.verified === true || result.value.is_authenticated === true;
});

// Computed property to dynamically disable the verify button
const isVerifyDisabled = computed(() => {
  return !selectedCustomer.value || !verificationType.value || isLoading.value;
});
</script>

<template>
  <div class="min-h-screen bg-slate-50 py-12 px-4 flex flex-col items-center space-y-8 font-sans">
    <h1 class="text-4xl font-bold text-gray-800">Customer Account Lookup</h1>
    <p class="text-lg text-gray-600">Select a customer to view their account details.</p>

    <div class="w-full max-w-md">
      <label class="block text-lg font-medium text-gray-700 mb-2 text-center">1. Select or Search for a Customer</label>
      <Combobox v-model="selectedCustomer">
        <div class="relative mt-1">
          <div class="relative w-full cursor-default overflow-hidden rounded-lg bg-white text-left shadow-md focus:outline-none focus-visible:ring-2 focus-visible:ring-white/75 focus-visible:ring-offset-2 focus-visible:ring-offset-blue-300 sm:text-sm">
            <ComboboxInput
              class="w-full border-none py-3 pl-3 pr-10 text-base leading-5 text-gray-900 focus:ring-0"
              :displayValue="(customer) => customer ? customer.displayName : ''"
              @change="query = $event.target.value"
              placeholder="Search by Name or National ID..."
            />
            <ComboboxButton class="absolute inset-y-0 right-0 flex items-center pr-2">
              <ChevronUpDownIcon class="h-5 w-5 text-gray-400" aria-hidden="true" />
            </ComboboxButton>
          </div>
          <transition leave-active-class="transition duration-100 ease-in" leave-from-class="opacity-100" leave-to-class="opacity-0">
            <ComboboxOptions class="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black/5 focus:outline-none sm:text-sm">
              <div v-if="filteredCustomers.length === 0 && query !== ''" class="relative cursor-default select-none px-4 py-2 text-gray-700">
                Nothing found.
              </div>
              <ComboboxOption v-for="customer in filteredCustomers" :key="customer.National_ID" :value="customer" as="template" v-slot="{ selected, active }">
                <li class="relative cursor-default select-none py-2 pl-10 pr-4" :class="{ 'bg-blue-600 text-white': active, 'text-gray-900': !active }">
                  <span class="block truncate" :class="{ 'font-medium': selected, 'font-normal': !selected }">{{ customer.displayName }}</span>
                  <span v-if="selected" class="absolute inset-y-0 left-0 flex items-center pl-3" :class="{ 'text-white': active, 'text-blue-600': !active }">
                    <CheckIcon class="h-5 w-5" aria-hidden="true" />
                  </span>
                </li>
              </ComboboxOption>
            </ComboboxOptions>
          </transition>
        </div>
      </Combobox>
    </div>

    <button @click="viewAccountDetails" :disabled="isButtonDisabled" class="bg-green-600 hover:bg-green-700 text-white font-bold text-lg px-16 py-3 rounded-full shadow-lg transition-transform transform hover:scale-105 disabled:bg-gray-400 disabled:cursor-not-allowed disabled:transform-none mt-4">
      View Account Details
    </button>

    <div v-if="result" class="w-full max-w-2xl mt-6">
        <h3 class="text-xl font-semibold text-gray-800 text-center">Verification Result</h3>
        <div class="mt-4 px-6 py-4 rounded-lg text-xl font-semibold text-center shadow-md"
             :class="{ 'bg-green-100 text-green-800': isVerificationSuccessful, 'bg-red-100 text-red-800': !isVerificationSuccessful }">
          {{ result.message }}
          <!-- Display relevant score/distance based on verification type -->
          <p v-if="verificationType === 'face' && typeof result.distance === 'number'" class="text-sm font-normal mt-1">
            (Distance: {{ result.distance.toFixed(4) }})
          </p>
          <p v-else-if="verificationType === 'iris' && (typeof result.similarity === 'number' || typeof result.best_similarity === 'number')" class="text-sm font-normal mt-1">
            (Similarity: {{ (result.similarity || result.best_similarity || 0).toFixed(4) }})
            <span v-if="result.matched_user_id && result.matched_user_id !== selectedCustomer.National_ID">(Matched ID: {{ result.matched_user_id }})</span>
          </p>
          <p v-if="result.detail && verificationType === 'iris'" class="text-sm font-normal mt-1 text-gray-600">
             ({{ result.detail }})
          </p>
        </div>
        <!-- Display matched face image only for face verification -->
        <div v-if="verificationType === 'face' && matchFaceImageUrl" class="flex justify-center items-start gap-16 mt-6">
            <div class="text-center">
                <p class="text-lg font-medium text-gray-700">Your Upload</p>
                <img :src="facePreview" alt="Uploaded Face" class="w-48 h-48 object-cover rounded-lg shadow-md mt-2 border-2 border-gray-300" />
            </div>
            <div class="text-center">
                <p class="text-lg font-medium text-gray-700">Customer's Stored Photo</p>
                <img :src="matchFaceImageUrl" alt="Matched Face" class="w-48 h-48 object-cover rounded-lg shadow-md mt-2 border-2" :class="isVerificationSuccessful ? 'border-green-500' : 'border-red-500'" />
            </div>
        </div>
        <!-- For iris, no specific matched image display in this example, but you could add if you store iris images -->
    </div>
  </div>
</template>
