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
  if (!selectedCustomer.value) {
    alert("Please select a customer first.");
    return;
  }
  // Navigate to the InfoPage with the customer's ID as a parameter
  router.push(`/info/${selectedCustomer.value.National_ID}`);
}

const isButtonDisabled = computed(() => {
  return !selectedCustomer.value;
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
  </div>
</template>