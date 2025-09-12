<script>
import axios from "axios";

export default {
  props: {
    show: Boolean,
    title: {
      type: String,
      default: "Modal"
    },
    entityType: {
      type: String, // "customer" or "employee"
      required: true
    },
    entity: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      localEntity: { ...this.entity }
    };
  },
  methods: {
    // Update customer or employee
    async updateEntity() {
      try {
        let payload;
        if (this.entityType === "employee") {
          const { EmID, ...rest } = this.localEntity;
          payload = rest;
          await axios.put(`http://localhost:8000/employees/${EmID}`, payload);
        } else if (this.entityType === "customer") {
          const { National_ID, ...rest } = this.localEntity;
          payload = rest;
          await axios.put(`http://localhost:8000/customers/${National_ID}`, payload);
        }
        this.$emit("updated", this.localEntity);
        this.$emit("close");
      } catch (err) {
        console.error(err);
        alert(`Failed to update ${this.entityType}`);
      }
    },

    // Delete customer or employee
    async deleteEntity() {
      try {
        if (this.entityType === "employee") {
          await axios.delete(`http://localhost:8000/employees/${this.localEntity.EmID}`);
          this.$emit("deleted", this.localEntity.EmID);
        } else if (this.entityType === "customer") {
          await axios.delete(`http://localhost:8000/customers/${this.localEntity.National_ID}`);
          this.$emit("deleted", this.localEntity.National_ID);
        }
        this.$emit("close");
      } catch (err) {
        console.error(err);
        alert(`Failed to delete ${this.entityType}`);
      }
    },

    // Toggle employee role
    async toggleRole() {
      try {
        this.localEntity.IsAdmin = !this.localEntity.IsAdmin;
        const { EmID, ...payload } = this.localEntity; // Remove ID
        await axios.put(`http://localhost:8000/employees/${EmID}`, payload);
        this.$emit("updated", this.localEntity);
      } catch (err) {
        console.error(err);
        alert("Failed to toggle role");
      }
    }
  },
  watch: {
    entity(newVal) {
      this.localEntity = { ...newVal };
    }
  }
};
</script>

<template>
  <div v-if="show" class="fixed inset-0 flex items-center justify-center bg-black bg-opacity-50">
    <div class="bg-white p-6 rounded-2xl shadow-xl w-96">
      <header class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-semibold">{{ title }}</h3>
        <button @click="$emit('close')" class="text-gray-500 hover:text-black">✖</button>
      </header>

      <!-- Customer Form -->
      <div v-if="entityType === 'customer'">
        <h2 class="mb-2 font-semibold">Update Customer</h2>
        <form @submit.prevent="updateEntity">
          <input v-model="localEntity.Name" placeholder="First Name" class="border p-2 w-full mb-2" />
          <input v-model="localEntity.SurName" placeholder="Last Name" class="border p-2 w-full mb-2" />
          <input v-model="localEntity.phone_no" placeholder="Phone" class="border p-2 w-full mb-2" />
          <input v-model="localEntity.Email" placeholder="Email" class="border p-2 w-full mb-2" />

          <div class="flex justify-between mt-4">
            <button type="submit" class="bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600">Update</button>
            <button type="button" @click="deleteEntity" class="bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600">Delete</button>
          </div>
        </form>
      </div>

      <!-- Employee Form -->
      <div v-else-if="entityType === 'employee'">
        <h2 class="mb-2 font-semibold">Update Employee</h2>
        <form @submit.prevent="updateEntity">
          <input v-model="localEntity.EmName" placeholder="First Name" class="border p-2 w-full mb-2" />
          <input v-model="localEntity.EmSurName" placeholder="Last Name" class="border p-2 w-full mb-2" />
          <p>Reset the password</p>
          <input type="password" v-model="localEntity.EmPass" placeholder="Password" class="border p-2 w-full mb-2"/>

          <div class="my-2">
            <label class="block font-semibold mb-1">Role</label>
            <div class="flex items-center justify-between">
              <span :class="localEntity.IsAdmin ? 'text-green-600 font-bold' : 'text-gray-600'">
                <p class="text-lg">
                 <strong>{{ localEntity.IsAdmin ? "Admin" : "Employee" }}</strong> 
                </p>
              </span>
              <div class="flex justify-center">
                <button @click="toggleRole" class="bg-blue-500 text-white px-4 text-sm py-2 rounded-lg hover:bg-blue-600">Change</button>
              </div>
            </div>
          </div>

          <div class="flex justify-between mt-10">
            <button type="submit" class="bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600">Update</button>
            <button type="button" @click="deleteEntity" class="bg-red-500 text-white px-4 py-2 rounded-lg hover:bg-red-600">Delete</button>
          </div>
        </form>

        
      </div>
    </div>
  </div>
</template>
