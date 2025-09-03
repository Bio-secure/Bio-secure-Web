<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';

// State for the multi-step form
const currentStep = ref(1);

// All form data is stored in refs
const nationalId = ref('');
const firstName = ref('');
const lastName = ref('');
const birthDate = ref('');
const phoneNo = ref('');
const email = ref('');
const balance = ref(0); // This will store the raw number (e.g., 1000000)
const gender = ref('Other');

const router = useRouter();

// Computed property for comma formatting the balance input
const formattedBalance = computed({
  // This 'get' function formats the number for display
  get: () => {
    if (balance.value === null || balance.value === 0) {
      return '';
    }
    return balance.value.toLocaleString('en-US');
  },
  // This 'set' function reads the user's input and updates the raw number
  set: (newValue) => {
    const numericValue = Number(newValue.replace(/[^0-9.]/g, ''));
    balance.value = isNaN(numericValue) ? 0 : numericValue;
  }
});

// Computed properties to validate each step
const isStep1Valid = computed(() => {
  return nationalId.value && firstName.value && lastName.value && birthDate.value;
});

// Navigation methods for the stepper
const nextStep = () => {
  if (currentStep.value < 3) {
    currentStep.value++;
  }
};

const prevStep = () => {
  if (currentStep.value > 1) {
    currentStep.value--;
  }
};

// The final submission function, called only at the last step
async function handleRegisterUser() {
  const userData = {
    nationalId: nationalId.value,
    firstName: firstName.value,
    lastName: lastName.value,
    birthDate: birthDate.value,
    phoneNo: phoneNo.value,
    email: email.value,
    balance: balance.value,
    gender: gender.value,
  };

  try {
    const res = await fetch("http://localhost:8000/register-user", {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userData)
    });

    const data = await res.json();

    if (!res.ok) {
      alert(data.detail || "Failed to register user.");
      return;
    }

    const newCustomerId = data.data[0].National_ID;
    if (newCustomerId) {
      alert("User details registered successfully! Now proceeding to biometric registration.");
      router.push(`/register-biometric-face/${newCustomerId}`);
    }

  } catch (err) {
    console.error("Registration failed:", err);
    alert("An error occurred during registration.");
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-4">
    <div class="max-w-2xl w-full bg-white p-8 rounded-2xl shadow-xl">
      <h1 class="text-3xl font-bold text-gray-800 text-center mb-2">Register New Customer</h1>
      <p class="text-center text-gray-500 mb-8">Follow the steps to create a new account.</p>

      <div class="flex items-center justify-center mb-8">
        <div class="flex items-center">
          <div :class="['w-10 h-10 rounded-full flex items-center justify-center font-bold', currentStep >= 1 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500']">1</div>
          <div :class="['w-20 h-1 mx-2', currentStep > 1 ? 'bg-blue-600' : 'bg-gray-200']"></div>
        </div>
        <div class="flex items-center">
          <div :class="['w-10 h-10 rounded-full flex items-center justify-center font-bold', currentStep >= 2 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500']">2</div>
          <div :class="['w-20 h-1 mx-2', currentStep > 2 ? 'bg-blue-600' : 'bg-gray-200']"></div>
        </div>
        <div class="flex items-center">
          <div :class="['w-10 h-10 rounded-full flex items-center justify-center font-bold', currentStep === 3 ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-500']">3</div>
        </div>
      </div>

      <form @submit.prevent="handleRegisterUser">
        <div v-if="currentStep === 1" class="space-y-4">
          <h2 class="text-xl font-semibold text-gray-700 text-center">Personal Details</h2>
          <div class="md:col-span-2">
            <label for="nationalId" class="block text-sm font-medium text-gray-700">National ID</label>
            <input type="text" id="nationalId" v-model="nationalId" class="mt-1 block w-full px-4 py-2.5 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500" required>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label for="firstName" class="block text-sm font-medium text-gray-700">First Name</label>
              <input type="text" id="firstName" v-model="firstName" class="mt-1 block w-full px-4 py-2.5 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500" required>
            </div>
            <div>
              <label for="lastName" class="block text-sm font-medium text-gray-700">Last Name</label>
              <input type="text" id="lastName" v-model="lastName" class="mt-1 block w-full px-4 py-2.5 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500" required>
            </div>
            <div>
              <label for="birthDate" class="block text-sm font-medium text-gray-700">Birth Date</label>
              <input type="date" id="birthDate" v-model="birthDate" class="mt-1 block w-full px-4 py-2.5 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500" required>
            </div>
            <div>
              <label for="gender" class="block text-sm font-medium text-gray-700">Gender</label>
              <select id="gender" v-model="gender" class="mt-1 block w-full px-3 py-2.5 border border-gray-300 bg-white rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500">
                <option>Male</option>
                <option>Female</option>
                <option>Other</option>
              </select>
            </div>
          </div>
        </div>

        <div v-if="currentStep === 2" class="space-y-4">
          <h2 class="text-xl font-semibold text-gray-700 text-center">Contact Information</h2>
          <div>
            <label for="email" class="block text-sm font-medium text-gray-700">Email Address (Optional)</label>
            <input type="email" id="email" v-model="email" class="mt-1 block w-full px-4 py-2.5 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500">
          </div>
          <div>
            <label for="phoneNo" class="block text-sm font-medium text-gray-700">Phone Number (Optional)</label>
            <input type="tel" id="phoneNo" v-model="phoneNo" class="mt-1 block w-full px-4 py-2.5 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500">
          </div>
        </div>

        <div v-if="currentStep === 3" class="space-y-4">
          <h2 class="text-xl font-semibold text-gray-700 text-center">Account Setup</h2>
          <div>
            <label for="balance" class="block text-sm font-medium text-gray-700">Initial Balance</label>
            <input 
              type="text" 
              inputmode="decimal" 
              id="balance" 
              v-model="formattedBalance" 
              placeholder="0.00"
              class="mt-1 block w-full px-4 py-2.5 border border-gray-300 rounded-lg shadow-sm focus:ring-blue-500 focus:border-blue-500 text-right"
            >
          </div>
        </div>
        
        <div class="md:col-span-2 pt-6 mt-6 border-t flex justify-between items-center">
          <button 
            type="button" 
            @click="prevStep" 
            v-if="currentStep > 1"
            class="bg-gray-200 hover:bg-gray-300 text-gray-800 font-bold py-3 px-6 rounded-lg transition"
          >
            Back
          </button>
          
          <div v-else></div> <button 
            type="button" 
            @click="nextStep" 
            v-if="currentStep < 3"
            :disabled="!isStep1Valid && currentStep === 1"
            class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-6 rounded-lg transition disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            Next
          </button>
          
          <button 
            type="submit" 
            v-if="currentStep === 3"
            class="bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-lg transition"
          >
            Finish Registration
          </button>
        </div>
      </form>
    </div>
  </div>
</template>