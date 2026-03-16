<template>
  <div class="fixed inset-0 bg-gray-800 bg-opacity-75 flex items-center justify-center z-50 p-4">
    <div class="bg-white rounded-xl shadow-xl w-full max-w-lg p-6 relative">
      <button 
        @click="$emit('close')"
        class="absolute top-4 right-4 text-gray-500 hover:text-gray-700 text-2xl font-semibold"
      >
        &times;
      </button>

      <h2 class="text-2xl font-semibold mb-6 text-gray-800 text-center">Register New Employee</h2>

      <form @submit.prevent="handleEmployeeRegistration">
        <div class="mb-4">
          <label for="employeeName" class="block text-gray-700 text-sm font-bold mb-2">Name:</label>
          <input 
            type="text" 
            id="employeeName" 
            v-model="employee.name" 
            class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" 
            required 
          />
        </div>
        <div class="mb-4">
          <label for="employeeSurname" class="block text-gray-700 text-sm font-bold mb-2">Surname:</label>
          <input 
            type="text" 
            id="employeeSurname" 
            v-model="employee.surname" 
            class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" 
            required 
          />
        </div>
        <div class="mb-4">
          <label for="employeeID" class="block text-gray-700 text-sm font-bold mb-2">Employee ID:</label>
          <input 
            type="text" 
            id="employeeID" 
            v-model="employee.employeeId" 
            class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" 
            required 
          />
        </div>
        
        <div class="mb-4">
          <label for="employeePassword" class="block text-gray-700 text-sm font-bold mb-2">Password:</label>
          <input 
            type="password" 
            id="employeePassword" 
            v-model="employee.password" 
            class="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline" 
            required 
          />
        </div>

        <div class="mb-6 flex items-center">
          <input 
            type="checkbox" 
            id="isAdmin" 
            v-model="employee.isAdmin" 
            class="form-checkbox h-5 w-5 text-blue-600 rounded"
          />
          <label for="isAdmin" class="ml-2 text-gray-700 text-sm font-bold">Is Admin?</label>
        </div>
        
        <div class="flex items-center justify-between mt-6">
          <button 
            type="submit" 
            class="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
          >
            Register Employee
          </button>
          <button 
            type="button" 
            @click="$emit('close')"
            class="bg-gray-300 hover:bg-gray-400 text-gray-800 font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
          >
            Cancel
          </button>
        </div>
      </form>

      <p v-if="message" :class="messageType === 'success' ? 'text-green-600' : 'text-red-600'" class="mt-4 text-center">{{ message }}</p>

    </div>
  </div>
</template>

<script>
export default {
  name: 'EmployeeRegistrationModal',
  emits: ['close'],
  data() {
    return {
      employee: {
        name: '',
        surname: '',
        employeeId: '',
        password: '',
        isAdmin: false,
      },
      message: '',
      messageType: ''
    };
  },
  methods: {
    async handleEmployeeRegistration() {
      this.message = '';
      this.messageType = '';
      // Basic validation
      if (!this.employee.name || !this.employee.surname || !this.employee.employeeId || !this.employee.password) {
        this.message = 'Please fill in all required fields.';
        this.messageType = 'error';
        return;
      }

      console.log('Attempting to register employee with data:', {
        name: this.employee.name,
        surname: this.employee.surname,
        employeeId: this.employee.employeeId,
        password: this.employee.password, // Password is sent from frontend
        isAdmin: this.employee.isAdmin
      });
      
      const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
      try {
        const response = await fetch(`${API_BASE_URL}/register-employee`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(this.employee) // Send the entire employee object
        });
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to register employee');
        }
        this.message = 'Employee registered successfully!';
        this.messageType = 'success';
        this.employee = { name: '', surname: '', employeeId: '', password: '', isAdmin: false }; // Reset form
        this.$emit('close'); // Close modal after successful registration
      } catch (error) {
        this.message = `Registration failed: ${error.message}`;
        this.messageType = 'error';
        console.error('Employee registration error:', error);
      }

      // Placeholder for now
      this.message = 'Employee registration logic goes here (backend integration pending).';
      this.messageType = 'info';

      setTimeout(() => {
        this.$emit('close');
      }, 1500); 
    }
  }
};
</script>

<style scoped>
/* Your existing styles */
</style>