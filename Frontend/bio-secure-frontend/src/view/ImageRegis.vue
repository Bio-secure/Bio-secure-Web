<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRouter } from 'vue-router';
// Import Headless UI and Heroicons components for the searchable dropdown
import {
  Combobox,
  ComboboxInput,
  ComboboxButton,
  ComboboxOptions,
  ComboboxOption,
} from '@headlessui/vue';
import { CheckIcon, ChevronUpDownIcon } from '@heroicons/vue/20/solid';

const router = useRouter();

// --- State Management ---
const customers = ref([]);
const selectedCustomer = ref(null);
const query = ref('');

// File state
const faceFile = ref(null);
const facePreview = ref(null);
const irisFile = ref(null);
const irisPreview = ref(null);

const errorMessage = ref('');
const successMessage = ref('');
const isLoading = ref(false);

// --- Fetch Customers on Component Load ---
onMounted(async () => {
  try {
    const res = await fetch("http://localhost:8000/customers");
    if (!res.ok) throw new Error("Failed to fetch customers");
    const data = await res.json();
    customers.value = data.map(c => ({...c, displayName: `${c.Name} ${c.SurName} (ID: ${c.National_ID})`}));
  } catch (err) {
    console.error("Error fetching customers:", err);
    errorMessage.value = "Could not load customer list.";
  }
});

// --- Computed property for filtering customers ---
const filteredCustomers = computed(() => {
  if (query.value === '') return customers.value;
  const searchTerm = query.value.toLowerCase();
  return customers.value.filter(customer => 
    customer.displayName.toLowerCase().includes(searchTerm) || 
    String(customer.National_ID).includes(query.value)
  );
});

// --- Functions to trigger file inputs ---
function triggerFaceUpload() {
  document.getElementById('faceFile').click();
}

function triggerIrisUpload() {
  document.getElementById('irisFile').click();
}

function handleFileChange(event, type) {
  const file = event.target.files[0];
  if (!file) return;
  if (type === 'face') {
    faceFile.value = file;
    facePreview.value = URL.createObjectURL(file);
  } else if (type === 'iris') {
    irisFile.value = file;
    irisPreview.value = URL.createObjectURL(file);
  }
}

async function registerBiometrics() {
  if (!selectedCustomer.value || !faceFile.value) {
    errorMessage.value = "Please select a customer and provide at least a face scan.";
    return;
  }

  isLoading.value = true;
  errorMessage.value = '';
  successMessage.value = '';

  const formData = new FormData();
  formData.append('national_id', selectedCustomer.value.National_ID);
  formData.append('face_image', faceFile.value);
  if (irisFile.value) {
    formData.append('iris_image', irisFile.value);
  }

  try {
    const res = await fetch("http://localhost:8000/register-biometric", {
      method: 'POST',
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Registration failed due to a server error.");
    }
    successMessage.value = data.message;
    
    // Clear form on success
    selectedCustomer.value = null;
    faceFile.value = null;
    facePreview.value = null;
    irisFile.value = null;
    irisPreview.value = null;
    query.value = ''; // also clear search query

  } catch (err) {
    errorMessage.value = err.message;
  } finally {
    isLoading.value = false;
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 py-12 px-4 flex flex-col items-center space-y-8 font-sans">
    <h1 class="text-4xl font-bold text-gray-800">Register Biometric Data</h1>
    <p class="text-lg text-gray-600 max-w-2xl text-center">Select an existing customer, upload their biometric images, and submit to create their identity record.</p>

    <div class="w-full max-w-2xl bg-white p-8 rounded-xl shadow-lg space-y-8">
      <div class="w-full">
        <label class="block text-lg font-medium text-gray-700 mb-2">1. Find Existing Customer</label>
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
                <div v-if="filteredCustomers.length === 0 && query !== ''" class="relative cursor-default select-none px-4 py-2 text-gray-700">Nothing found.</div>
                <ComboboxOption v-for="customer in filteredCustomers" :key="customer.National_ID" :value="customer" as="template" v-slot="{ selected, active }">
                  <li class="relative cursor-default select-none py-2 pl-10 pr-4" :class="{'bg-blue-600 text-white': active, 'text-gray-900': !active}">
                    <span class="block truncate" :class="{'font-medium': selected, 'font-normal': !selected}">{{ customer.displayName }}</span>
                    <span v-if="selected" class="absolute inset-y-0 left-0 flex items-center pl-3" :class="{'text-white': active, 'text-blue-600': !active}"><CheckIcon class="h-5 w-5" aria-hidden="true" /></span>
                  </li>
                </ComboboxOption>
              </ComboboxOptions>
            </transition>
          </div>
        </Combobox>
      </div>

      <div>
        <label class="block text-lg font-medium text-gray-700 mb-2">2. Upload Biometric Images</label>
        <div class="flex flex-wrap justify-center gap-8 mt-4">
          <div class="flex flex-col items-center">
            <p class="font-semibold text-gray-700 mb-2">Face Scan (Required)</p>
            <div @click="triggerFaceUpload" class="w-48 h-48 bg-gray-100 rounded-lg border-2 border-dashed flex items-center justify-center cursor-pointer hover:border-blue-500 transition-colors">
              <img v-if="facePreview" :src="facePreview" class="w-full h-full object-cover rounded-lg">
              <span v-else class="text-gray-500 text-center p-2">Click to upload image</span>
            </div>
            <input type="file" id="faceFile" @change="handleFileChange($event, 'face')" class="hidden" accept="image/*">
          </div>
          <div class="flex flex-col items-center">
            <p class="font-semibold text-gray-700 mb-2">Iris Scan (Optional)</p>
            <div @click="triggerIrisUpload" class="w-48 h-48 bg-gray-100 rounded-lg border-2 border-dashed flex items-center justify-center cursor-pointer hover:border-blue-500 transition-colors">
              <img v-if="irisPreview" :src="irisPreview" class="w-full h-full object-cover rounded-lg">
              <span v-else class="text-gray-500 text-center p-2">Click to upload image</span>
            </div>
            <input type="file" id="irisFile" @change="handleFileChange($event, 'iris')" class="hidden" accept="image/*">
          </div>
        </div>
      </div>
      
      <div class="pt-4 text-center">
        <button @click="registerBiometrics" :disabled="isLoading || !selectedCustomer || !faceFile" class="bg-blue-600 hover:bg-blue-700 text-white font-bold text-lg px-12 py-3 rounded-full shadow-lg transition-transform transform hover:scale-105 disabled:bg-gray-400 disabled:cursor-not-allowed disabled:transform-none">
          <span v-if="isLoading">Processing...</span>
          <span v-else>Register Biometric Data</span>
        </button>
      </div>

      <div v-if="errorMessage" class="mt-4 text-center p-3 bg-red-100 text-red-700 rounded-md shadow-sm">{{ errorMessage }}</div>
      <div v-if="successMessage" class="mt-4 text-center p-3 bg-green-100 text-green-700 rounded-md shadow-sm">{{ successMessage }}</div>
    </div>
  </div>
</template>