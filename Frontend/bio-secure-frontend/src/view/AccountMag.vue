<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import axios from "axios";
// @ts-ignore
import UpdateEntityPopUp from "../components/UpdateCustomerPopUp.vue";

const customers = ref<any[]>([]);
const employees = ref<any[]>([]);
const loading = ref(true);
const error = ref<string | null>(null);

// popup state
const showUpdatePopup = ref(false);
const selectedEntity = ref<any | null>(null);
const selectedType = ref<"customer" | "employee" | null>(null);

const currentPage = ref(1);
const pageSize = 5;
const totalCustomers = ref(0);

function openCustomerUpdatePopup(customer: any) {
  selectedEntity.value = { ...customer };
  selectedType.value = "customer";
  showUpdatePopup.value = true;
}

function openEmployeeUpdatePopup(employee: any) {
  selectedEntity.value = { ...employee };
  selectedType.value = "employee";
  showUpdatePopup.value = true;
}

function closeUpdatePopup() {
  showUpdatePopup.value = false;
  selectedEntity.value = null;
  selectedType.value = null;
}

const totalCustomerPages = computed(() =>
  Math.ceil(totalCustomers.value / pageSize)
);

function goToCustomerPage(page: number) {
  if (page >= 1 && page <= totalCustomerPages.value) {
    currentPage.value = page;
    fetchCustomers();
  }
}


function handleCustomerUpdated(updatedCustomer: any) {
  const index = customers.value.findIndex(c => c.National_ID === updatedCustomer.National_ID);
  if (index !== -1) {
    customers.value[index] = updatedCustomer; // update table row
  }
}
function handleCustoemerDeleted(id: number) {
  customers.value = customers.value.filter(c => c.National_ID !== id);
}

async function fetchCustomers() {
    loading.value = true;
    try {
      const response = await axios.get("http://localhost:8000/customers-page", {
        params: { page: currentPage.value, page_size: pageSize },
      });
      customers.value = response.data.data;
      totalCustomers.value = response.data.total;
    } catch (err: any) {
      error.value = err.response?.data?.detail || "Failed to fetch customers";
    } finally {
      loading.value = false;
    }
  }
const empCurrentPage = ref(1);
const empPageSize = 10;
const empTotal = ref(0);

const empTotalPages = computed(() =>
  Math.ceil(empTotal.value / empPageSize)
);

async function fetchEmployees() {
  try {
    const response = await axios.get("http://localhost:8000/employees", {
      params: { page: empCurrentPage.value, page_size: empPageSize },
    });
    employees.value = response.data.data;
    empTotal.value = response.data.total;
  } catch (err: any) {
    error.value = err.response?.data?.detail || "Failed to fetch employees";
  }
}

function goToEmpPage(page: number) {
  if (page >= 1 && page <= empTotalPages.value) {
    empCurrentPage.value = page;
    fetchEmployees();
  }
}

onMounted(async () => {
  fetchCustomers(),
  fetchEmployees()
});

function nextPage() {
  if (currentPage.value * pageSize < totalCustomers.value) {
    currentPage.value++;
    fetchCustomers();
  }
}
function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--;
    fetchCustomers();
  }
}

</script>

<template>
  <div class="p-6 h-full bg-slate-100 font-sans">
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
                                    @click="openCustomerUpdatePopup(c)"
                                    class="text-blue-600 hover:text-blue-800"
                                >
                                    Edit
                                </button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
            <div class="flex justify-center items-center mt-4 space-x-2">
              <button
                @click="goToCustomerPage(currentPage - 1)"
                :disabled="currentPage === 1"
                class="px-3 py-1 rounded-lg bg-gray-200 disabled:opacity-50"
              >
                Prev
              </button>

              <button
                v-for="page in totalCustomerPages"
                :key="page"
                @click="goToCustomerPage(page)"
                class="px-3 py-1 rounded-lg"
                :class="page === currentPage ? 'bg-blue-600 text-white' : 'bg-gray-100 hover:bg-gray-200'"
              >
                {{ page }}
              </button>

              <button
                @click="goToCustomerPage(currentPage + 1)"
                :disabled="currentPage === totalCustomerPages"
                class="px-3 py-1 rounded-lg bg-gray-200 disabled:opacity-50"
              >
                Next
              </button>
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
                      <th class="py-2 px-4 text-left">Edit</th>
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
                            <td class="py-2 px-4">
                                <button
                                    @click="openEmployeeUpdatePopup(e)"
                                    class="text-blue-600 hover:text-blue-800"
                                >
                                    Edit
                                </button>
                            </td>
                        </tr>
                </tbody>
            </table>
        </div>
        <div class="flex justify-center items-center mt-4 space-x-2">
          <button
            @click="goToEmpPage(empCurrentPage - 1)"
            :disabled="empCurrentPage === 1"
            class="px-3 py-1 rounded-lg bg-gray-200 disabled:opacity-50"
          >
            Prev
          </button>

          <button
            v-for="page in empTotalPages"
            :key="page"
            @click="goToEmpPage(page)"
            class="px-3 py-1 rounded-lg"
            :class="page === empCurrentPage ? 'bg-blue-600 text-white' : 'bg-gray-100 hover:bg-gray-200'"
          >
            {{ page }}
          </button>

          <button
            @click="goToEmpPage(empCurrentPage + 1)"
            :disabled="empCurrentPage === empTotalPages"
            class="px-3 py-1 rounded-lg bg-gray-200 disabled:opacity-50"
          >
            Next
          </button>
        </div>

        <UpdateEntityPopUp
          v-if="showUpdatePopup"
          :show="showUpdatePopup"
          :entityType="selectedType"
          :title="selectedType === 'customer' ? 'Edit Customer' : 'Edit Employee'"
          :entity="selectedEntity"
          @close="closeUpdatePopup"
          @updated="selectedType === 'customer' ? handleCustomerUpdated : fetchEmployees"
          @deleted="selectedType === 'customer' ? handleCustoemerDeleted : fetchEmployees"
        />

      </div>
    </div>
  </div>
</template>
