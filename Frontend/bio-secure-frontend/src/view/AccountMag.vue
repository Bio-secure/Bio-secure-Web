<script setup lang="ts">
import { ref, onMounted } from "vue";
import axios from "axios";
import UpdateCustomerPopUp from "../components/UpdateCustomerPopUp.vue";

const customers = ref<any[]>([]);
const employees = ref<any[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// popup state
const showUpdatePopup = ref(false);
const selectedCustomer = ref<any | null>(null);

function openUpdatePopup(customer: any) {
  selectedCustomer.value = { ...customer };
  showUpdatePopup.value = true;
}
function closeUpdatePopup() {
  showUpdatePopup.value = false;
}
function handleUpdated(updatedCustomer: any) {
  const index = customers.value.findIndex(c => c.National_ID === updatedCustomer.National_ID);
  if (index !== -1) {
    customers.value[index] = updatedCustomer; // update table row
  }
}

onMounted(async () => {
  try {
    const response = await axios.get("http://localhost:8000/customers");
    customers.value = response.data;
  } catch (err: any) {
    error.value = err.response?.data?.detail || "Failed to fetch customers";
  } finally {
    loading.value = false;
  }

  try {
    const response = await axios.get("http://localhost:8000/employees");
    employees.value = response.data;
  } catch (err: any) {
    error.value = err.response?.data?.detail || "Failed to fetch employees";
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="p-6 h-screen bg-slate-100 font-sans">
    <!-- Loading -->
    <div v-if="loading" class="text-gray-500">Loading customers...</div>

    <!-- Error -->
    <div v-else-if="error" class="text-red-600 font-semibold">
      {{ error }}
    </div>

    <!-- Customer Table -->
    
    <div v-else>
        <div class="w-[80%] lg:col-span-2 mx-auto bg-white rounded-2xl shadow-md p-6 flex flex-col">
            <h2 class="text-2xl font-semibold text-gray-800 pb-5">Customer List</h2>
            <div class=" overflow-y-auto h-auto border-t border-gray-100 ">
                <table class=" w-full text-sm">
                    <thead class="bg-gray-100 text-gray-700">
                            <tr>
                                <th class="py-2 px-4 text-left">ID</th>
                                <th class="py-2 px-4 text-left">First Name</th>
                                <th class="py-2 px-4 text-left">Last Name</th>
                                <th class="py-2 px-4 text-left">Phone No.</th>
                                <th class="py-2 px-4 text-left">Email</th>
                                <th class="py-2 px-4 text-left">Edit</th>
                            </tr>
                    </thead>
                    <tbody>
                        <tr
                        v-for="c in customers"
                        :key="c.National_ID"
                        class="border-b border-gray-100 hover:bg-gray-50"
                        >
                            <td class="py-2 px-4">{{ c.National_ID }}</td>
                            <td class="py-2 px-4">{{ c.Name }}</td>
                            <td class="py-2 px-4">{{ c.SurName }}</td>
                            <td class="py-2 px-4">{{ c.phone_no }}</td>
                            <td class="py-2 px-4">{{ c.Email }}</td>
                            <td class="py-2 px-4">
                                <button
                                    @click="openUpdatePopup(c)"
                                    class="text-blue-600 hover:text-blue-800"
                                >
                                    Edit
                                </button>
                            </td>
                        </tr>
                    </tbody>
                </table>
                <UpdateCustomerPopUp
                    v-if="showUpdatePopup"
                    :show="showUpdatePopup"
                    title="Edit Customer"
                    :customer="selectedCustomer"
                    @close="closeUpdatePopup"
                    @updated="handleUpdated"
                />
            </div>
        </div>
      
      <br>
        <!-- Employee Table -->
      <div class="w-[80%] lg:col-span-2 mx-auto bg-white rounded-2xl shadow-md p-6 flex flex-col">
        <h2 class="text-2xl font-semibold text-gray-800 pb-5">
            Employee List
        </h2>
        <div class=" overflow-y-auto h-auto border-t border-gray-100 ">
            <table class=" w-full text-sm">
                <thead class="bg-gray-100 text-gray-700">
                    <tr>
                    <th class="py-2 px-4 text-left">ID</th>
                    <th class="py-2 px-4 text-left">First Name</th>
                    <th class="py-2 px-4 text-left">Last Name</th>
                    <th class="py-2 px-4 text-left">Is Admin</th>
                    </tr>
                </thead>
                <tbody>
                        <tr
                        v-for="e in employees"
                        :key="e.EmID"
                        class="border-b border-gray-100 hover:bg-gray-50"
                        >
                            <td class="py-2 px-4">{{ e.EmID }}</td>
                            <td class="py-2 px-4">{{ e.EmName }}</td>
                            <td class="py-2 px-4">{{ e.EmSurName }}</td>
                            <td class="py-2 px-4">{{ e.IsAdmin }}</td>
                        </tr>
                </tbody>
            </table>
        </div>
      </div>
    </div>
  </div>
</template>
