<script setup lang="ts">
import { ref, onMounted } from "vue";
import axios from "axios";

const customers = ref<any[]>([]);
const employees = ref<any[]>([])
const loading = ref(true);
const error = ref<string | null>(null);

onMounted(async () => {
 // Fetch all customer
  try {
    const response = await axios.get("http://localhost:8000/customers");
    customers.value = response.data;
    console.log(customers.value)
  } catch (err: any) {
    error.value = err.response?.data?.detail || "Failed to fetch customers";
  } finally {
    loading.value = false;
  }

 // Fetch all employees 
  try {
    const response = await axios.get("http://localhost:8000/employees");
    employees.value = response.data
  } catch (err: any) {
    error.value = err.response?.data?.detail || "Failed to fetch employees"
  } finally {
    loading.value = false;
  }
});
</script>

<template>
  <div class="p-6">
    <!-- Loading -->
    <div v-if="loading" class="text-gray-500">Loading customers...</div>

    <!-- Error -->
    <div v-else-if="error" class="text-red-600 font-semibold">
      {{ error }}
    </div>

    <!-- Customer Table -->
    <div v-else>
      <h2 class="text-2xl font-bold mb-4">Customer List</h2>
      <div class="overflow-x-auto">
        <table class="min-w-full bg-white border border-gray-200 rounded-lg shadow">
          <thead class="bg-gray-100 text-gray-700">
            <tr>
              <th class="py-2 px-4 text-left">ID</th>
              <th class="py-2 px-4 text-left">First Name</th>
              <th class="py-2 px-4 text-left">Last Name</th>
              <th class="py-2 px-4 text-left">Phone No.</th>
              <th class="py-2 px-4 text-left">Email</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="c in customers"
              :key="c.National_ID"
              class="border-t hover:bg-gray-50"
            >
              <td class="py-2 px-4">{{ c.National_ID }}</td>
              <td class="py-2 px-4">{{ c.Name }}</td>
              <td class="py-2 px-4">{{ c.SurName }}</td>
              <td class="py-2 px-4">{{ c.phone_no }}</td>
              <td class="py-2 px-4">{{ c.Email }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <br>
      <h2 class="text-2xl font-bold mb-4">
        Employee List
      </h2>
      <div class="overflow-x-auto">
        <table class="min-w-full bg-white border border-gray-200 rounded-lg shadow">
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
              class="border-t hover:bg-gray-50"
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
</template>
