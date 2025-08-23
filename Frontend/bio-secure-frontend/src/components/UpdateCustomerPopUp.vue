
<script>
import axios from "axios";

export default {
  props: {
    show: Boolean,
    title: {
      type: String,
      default: "Modal"
    },
    customer: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      localCustomer: { ...this.customer } // copy so we don’t mutate prop directly
    };
  },
  methods: {
    async updateCustomer() {
      try {
        await axios.put(
          `http://localhost:8000/customers/${this.localCustomer.National_ID}`,
          this.localCustomer
        );
        this.$emit("updated", this.localCustomer); // notify parent
        this.$emit("close");
      } catch (err) {
        console.error(err);
        alert("Failed to update customer");
      }
    },
    async deleteCustomer() {
      if (!confirm("Are you sure you want to delete this customer?")) return;
      try {
        await axios.delete(`http://localhost:8000/customers/${this.localCustomer.National_ID}`);
        this.$emit("deleted", this.localCustomer.National_ID); // notify parent
        this.$emit("close");
      } catch (err) {
        console.error(err);
        alert("Failed to delete customer");
      }
    }
  },
  watch: {
    // update form if customer prop changes
    customer(newVal) {
      this.localCustomer = { ...newVal };
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

      <div>
        <h2 class="mb-2 font-semibold">Update Customer</h2>
        <form @submit.prevent="updateCustomer">
          <input v-model="localCustomer.Name" placeholder="First Name" class="border p-2 w-full mb-2"/>
          <input v-model="localCustomer.SurName" placeholder="Last Name" class="border p-2 w-full mb-2"/>
          <input v-model="localCustomer.phone_no" placeholder="Phone" class="border p-2 w-full mb-2"/>
          <input v-model="localCustomer.Email" placeholder="Email" class="border p-2 w-full mb-2"/>
          <div class="flex justify-between mt-4">
            <!-- Update -->
            <button type="submit" class="bg-green-500 text-white px-4 py-2 rounded-lg">
              Update
            </button>

            <!-- Delete -->
            <button 
              type="button" 
              @click="deleteCustomer"
              class="bg-red-500 text-white px-4 py-2 rounded-lg"
            >
              Delete
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>
