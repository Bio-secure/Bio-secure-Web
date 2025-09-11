<script setup>
import { ref, onMounted, computed, watch } from 'vue';
import { useRouter } from 'vue-router';
import {
  Combobox,
  ComboboxInput,
  ComboboxButton,
  ComboboxOptions,
  ComboboxOption,
} from '@headlessui/vue';
import { CheckIcon, ChevronUpDownIcon, MagnifyingGlassIcon } from '@heroicons/vue/20/solid';

const customers = ref([]);
const selectedCustomer = ref(null);
const query = ref('');
const isLoading = ref(true); // Start in a loading state
const router = useRouter();

// Fetch ALL customers when the component loads
onMounted(async () => {
  isLoading.value = true;
  try {
    const res = await fetch("http://localhost:8000/customers");
    if (!res.ok) throw new Error("Failed to fetch customers");
    const data = await res.json();
    customers.value = data.map(c => ({ ...c, displayName: `${c.Name || ''} ${c.SurName || ''} (ID: ${c.National_ID})`.trim() }));
  } catch (err) {
    console.error("Error fetching customers:", err);
    alert("Could not load customer list from the server.");
  } finally {
    isLoading.value = false;
  }
});

// Filter the already-loaded customers list based on the search query
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

// Watch for when a customer is selected from the list
watch(selectedCustomer, (newSelection) => {
  if (newSelection) {
    // Navigate immediately upon selection
    router.push(`/info/${newSelection.National_ID}`);
  }
});
</script>

<template>
  <div class="pt-20 px-4 flex flex-col items-center font-sans">
    <div class="w-full max-w-lg text-center">
      <h1 class="text-4xl font-bold text-gray-800">Customer Account Lookup</h1>
      <p class="text-lg text-gray-600 mt-2">Select a customer from the list to view their details.</p>
    </div>

    <div class="w-full max-w-md mt-8">
      <Combobox v-model="selectedCustomer">
        <div class="relative">
          <div class="relative w-full cursor-default overflow-hidden rounded-lg bg-white text-left shadow-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500/75">
            <MagnifyingGlassIcon class="pointer-events-none absolute left-3 top-3.5 h-5 w-5 text-gray-400" aria-hidden="true" />
            <ComboboxInput
              class="w-full border-none py-3 pl-10 pr-10 text-base leading-5 text-gray-900 focus:ring-0"
              :displayValue="(customer) => customer ? customer.displayName : ''"
              @change="query = $event.target.value"
              placeholder="Search by Name or National ID..."
              autocomplete="off"
            />
            <ComboboxButton class="absolute inset-y-0 right-0 flex items-center pr-2">
              <ChevronUpDownIcon class="h-5 w-5 text-gray-400" aria-hidden="true" />
            </ComboboxButton>
          </div>
          <transition leave-active-class="transition duration-100 ease-in" leave-from-class="opacity-100" leave-to-class="opacity-0">
            <ComboboxOptions class="absolute z-10 mt-1 max-h-60 w-full overflow-auto rounded-md bg-white py-1 text-base shadow-lg ring-1 ring-black/5 focus:outline-none sm:text-sm">
              
              <div v-if="isLoading" class="relative cursor-default select-none px-4 py-2 text-gray-500">
                Loading customer list...
              </div>

              <div v-else-if="filteredCustomers.length === 0 && query !== ''" class="relative cursor-default select-none px-4 py-2 text-gray-700">
                Nothing found.
              </div>

              <ComboboxOption v-for="customer in filteredCustomers" :key="customer.National_ID" :value="customer" as="template" v-slot="{ selected, active }">
                <li class="relative cursor-default select-none py-2 pl-10 pr-4" :class="{ 'bg-blue-600 text-white': active, 'text-gray-900': !active }">
                  <span class="block truncate" :class="{ 'font-medium': selected, 'font-normal': !selected }">
                    {{ customer.Name }} {{ customer.SurName }}
                  </span>
                  <span class="block truncate text-xs" :class="{ 'text-blue-100': active, 'text-gray-500': !active }">
                    ID: {{ customer.National_ID }}
                  </span>
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
    </div>
</template>