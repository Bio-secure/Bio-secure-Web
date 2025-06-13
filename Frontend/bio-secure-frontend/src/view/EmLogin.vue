<script>
import authState, { login } from '../services/authService';

export default {
  name: 'EmployeeLoginPage',
  data() {
    return {
      employeeId: '',
      password: '',
      errorMessage: '',
      loading: false,
    };
  },
  methods: {
    async handleLogin() {
      this.errorMessage = '';
      this.loading = true;

      if (!this.employeeId || !this.password) {
        this.errorMessage = 'Please enter both Employee ID and Password.';
        this.loading = false;
        return;
      }

      try {
        const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${API_BASE_URL}/login-employee`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            emId: parseInt(this.employeeId),
            password: this.password,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Login failed.');
        }

        const data = await response.json();
        
        if (data.success) {
          login(data.emId, data.isAdmin, data.name, data.surname);
          this.$router.push('/main'); 
        } else {
          this.errorMessage = data.message || 'Login failed: Invalid credentials.';
        }
      } catch (error) {
        console.error('Login error:', error);
        this.errorMessage = error.message || 'An unexpected error occurred during login.';
      } finally {
        this.loading = false;
      }
    },
  },
};
</script>

<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-100">
    <div class="bg-white p-8 rounded-xl shadow-lg w-full max-w-md">
      <h2 class="text-3xl font-bold text-center text-gray-800 mb-6">Employee Login</h2>
      <form @submit.prevent="handleLogin">
        <div class="mb-4">
          <label for="employeeId" class="block text-gray-700 text-sm font-bold mb-2">Employee ID:</label>
          <input
            type="text"
            id="employeeId"
            v-model="employeeId"
            class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
            required
            autocomplete="username"
          />
        </div>
        <div class="mb-6">
          <label for="password" class="block text-gray-700 text-sm font-bold mb-2">Password:</label>
          <input
            type="password"
            id="password"
            v-model="password"
            class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 mb-3 leading-tight focus:outline-none focus:shadow-outline"
            required
            autocomplete="current-password"
          />
        </div>
        <p v-if="errorMessage" class="text-red-500 text-sm mb-4 text-center">{{ errorMessage }}</p>
        <div class="flex items-center justify-between">
          <button
            type="submit"
            :disabled="loading"
            class="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline w-full"
          >
            <span v-if="!loading">Login</span>
            <span v-else>Logging in...</span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>