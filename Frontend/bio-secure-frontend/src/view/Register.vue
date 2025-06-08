<script>
import { supabase } from '../main'; // adjust path as needed

export default {
  name: 'UserInfoForm',
  data() {
    return {
      formData: {
        firstName: '',
        lastName: '',
        gender: '',
        birthDate: '',
        nationalId: '',
        phoneNo: '',
        email: '',
        balance: ''
      }
    };
  },
  methods: {
    async handleSubmit() {
      const payload = {
        "National ID": this.formData.nationalId ? parseInt(this.formData.nationalId) : undefined,
        "Name": this.formData.firstName,
        "SurName": this.formData.lastName,
        "BirthDate": this.formData.birthDate,
        "PhoneNo": this.formData.phoneNo ? parseInt(this.formData.phoneNo) : null,
        "Gender": this.formData.gender,
        "DOR": new Date().toISOString(),
        "Email": this.formData.email || null,
        "Balance": this.formData.balance
      };

      const { data, error } = await supabase.from('Customer').insert([payload]);

      if (error) {
        console.error('Supabase error:', error);
        alert('Failed to save data: ' + error.message);
      } else {
        console.log('Inserted:', data);
        alert('User registered successfully!');
        this.resetForm();
      }
    },
    resetForm() {
      this.formData = {
        firstName: '',
        lastName: '',
        gender: '',
        birthDate: '',
        nationalId: '',
        phoneNo: '',
        email: ''
      };
    }
  }
};
</script>

<template>
  <div class="flex items-center justify-center min-h-screen">
    <div class="w-full max-w-4xl p-12 rounded-2xl bg-white shadow-2xl">
      <h2 class="text-3xl font-bold text-center text-blue-900 mb-10">User Registration</h2>

      <!-- Form Starts -->
      <div>
        <!-- Name -->
        <div class="mb-8">
          <div class="flex items-center">
            <label class="w-32 text-base text-gray-800 font-semibold">Name</label>
            <div class="flex flex-1 gap-6">
              <input
                type="text"
                v-model="formData.firstName"
                placeholder="First Name"
                class="w-1/2 px-4 py-3 border border-gray-300 bg-white shadow-sm rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
              />
              <input
                type="text"
                v-model="formData.lastName"
                placeholder="Last Name"
                class="w-1/2 px-4 py-3 border border-gray-300 bg-white shadow-sm rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
              />
            </div>
          </div>
        </div>

        <!-- Gender and Birth Date -->
        <div class="mb-8">
          <div class="flex items-center">
            <label class="w-32 text-base text-gray-800 font-semibold">Gender</label>
            <select
              v-model="formData.gender"
              class="w-40 px-4 py-3 border border-gray-300 bg-white shadow-sm rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
            >
              <option value="">Gender</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>

            <label class="ml-10 mr-4 text-base text-gray-800 font-semibold">Birth Date</label>
            <input
              type="date"
              v-model="formData.birthDate"
              class="w-44 px-4 py-3 border border-gray-300 bg-white shadow-sm rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
          </div>
        </div>

        <!-- National ID -->
        <div class="mb-8">
          <div class="flex items-center">
            <label class="w-32 text-base text-gray-800 font-semibold">National ID</label>
            <input
              type="text"
              v-model="formData.nationalId"
              class="flex-1 px-4 py-3 border border-gray-300 bg-white shadow-sm rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
          </div>
        </div>

        <!-- Phone Number -->
        <div class="mb-8">
          <div class="flex items-center">
            <label class="w-32 text-base text-gray-800 font-semibold">Phone No.</label>
            <input
              type="tel"
              v-model="formData.phoneNo"
              class="flex-1 px-4 py-3 border border-gray-300 bg-white shadow-sm rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
          </div>
        </div>

        <!-- Email -->
        <div class="mb-8">
          <div class="flex items-center">
            <label class="w-32 text-base text-gray-800 font-semibold">Email</label>
            <input
              type="email"
              v-model="formData.email"
              class="flex-1 px-4 py-3 border border-gray-300 bg-white shadow-sm rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
          </div>
        </div>

        <div class="mb-8">
          <div class="flex items-center">
            <label class="w-32 text-base text-gray-800 font-semibold">Balance</label>
            <input
              type="text"
              v-model="formData.balance"
              class="flex-1 px-4 py-3 border border-gray-300 bg-white shadow-sm rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-300"
            />
          </div>
        </div>

        <!-- Submit Button -->
        <div class="flex justify-center mt-10">
          <button
            @click="handleSubmit"
            class="px-14 py-3 bg-blue-900 text-white text-lg font-semibold rounded-lg hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-400 shadow-md"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  </div>
</template>



