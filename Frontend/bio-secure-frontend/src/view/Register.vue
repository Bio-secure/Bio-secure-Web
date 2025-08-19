<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';

// 1. Create reactive variables to store the data from the form inputs.
const nationalId = ref('');
const firstName = ref('');
const lastName = ref('');
const birthDate = ref('');
const phoneNo = ref('');
const email = ref('');
const balance = ref(0);
const gender = ref('Other');

// 2. Initialize the Vue router.
const router = useRouter();

// 3. This is the main function that runs when the form is submitted.
async function handleRegisterUser() {
  // Gather all the form data into one object.
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
      // Handle errors from the backend.
      alert(data.detail || "Failed to register user.");
      return;
    }

    // On success, get the new customer's ID and redirect.
    const newCustomerId = data.data[0].National_ID;
    if (newCustomerId) {
      alert("User details registered successfully! Now proceeding to biometric registration.");
      router.push(`/register-biometric/${newCustomerId}`);
    }

  } catch (err) {
    console.error("Registration failed:", err);
    alert("An error occurred during registration.");
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 flex items-center justify-center p-4">
    <div class="max-w-2xl w-full bg-white p-8 rounded-2xl shadow-lg">
      <h1 class="text-3xl font-bold text-gray-800 text-center mb-8">Register New Customer</h1>
      
      <form @submit.prevent="handleRegisterUser" class="grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
        
        <div class="md:col-span-2">
          <label for="nationalId" class="block text-sm font-medium text-gray-700">National ID</label>
          <input type="text" id="nationalId" v-model="nationalId" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm" required>
        </div>
        
        <div>
          <label for="firstName" class="block text-sm font-medium text-gray-700">First Name</label>
          <input type="text" id="firstName" v-model="firstName" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm" required>
        </div>
        
        <div>
          <label for="lastName" class="block text-sm font-medium text-gray-700">Last Name</label>
          <input type="text" id="lastName" v-model="lastName" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm" required>
        </div>

        <div>
          <label for="birthDate" class="block text-sm font-medium text-gray-700">Birth Date</label>
          <input type="date" id="birthDate" v-model="birthDate" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm" required>
        </div>

        <div>
          <label for="gender" class="block text-sm font-medium text-gray-700">Gender</label>
           <select id="gender" v-model="gender" class="mt-1 block w-full px-3 py-2 border border-gray-300 bg-white rounded-md shadow-sm">
            <option>Male</option>
            <option>Female</option>
            <option>Other</option>
          </select>
        </div>

        <div class="md:col-span-2">
          <label for="email" class="block text-sm font-medium text-gray-700">Email Address</label>
          <input type="email" id="email" v-model="email" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm">
        </div>

        <div>
          <label for="phoneNo" class="block text-sm font-medium text-gray-700">Phone Number</label>
          <input type="tel" id="phoneNo" v-model="phoneNo" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm">
        </div>

        <div>
          <label for="balance" class="block text-sm font-medium text-gray-700">Initial Balance</label>
          <input type="number" id="balance" v-model.number="balance" step="0.01" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm">
        </div>

        <div class="md:col-span-2 pt-4">
          <button type="submit" class="w-full bg-blue-600 hover:bg-blue-700 text-white font-bold py-3 px-4 rounded-lg transition-transform transform hover:scale-105">
            Next: Register Biometrics
          </button>
        </div>
      </form>
    </div>
  </div>
</template>