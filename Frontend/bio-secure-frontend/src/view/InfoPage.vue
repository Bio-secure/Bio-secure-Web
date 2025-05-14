<script lang="ts">
import { defineComponent, ref, onMounted, computed } from 'vue';

export default defineComponent({
  name: 'AccountDashboard',
  setup() {
    const user = ref({
      name: '',
      phone: '',
      id: '',
      balance: 0
    });

    const transactions = ref([
      { id: 1, date: '20/04/2568', description: 'Withdraw', amount: -40000 },
      { id: 2, date: '16/04/2568', description: 'Deposit', amount: 40000 },
      { id: 3, date: '12/04/2568', description: 'Safe deposit box', amount: 0 }
    ]);

    const transaction = ref({
      amount: null,
      note: ''
    });

    const isDepositMode = ref(false);

    const formattedBalance = computed(() =>
      user.value.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })
    );

    const formatAmount = (amount: number) => {
      if (amount === 0) return '-';
      return `${amount > 0 ? '+' : ''}${amount.toLocaleString()}`;
    };

    const submitTransaction = () => {
      const mode = isDepositMode.value ? 'Deposit' : 'Withdraw';
      console.log(`${mode} Submitted:`, transaction.value);

      // Example transaction mutation
      const newTx = {
        id: Date.now(),
        date: new Date().toLocaleDateString('th-TH'),
        description: mode,
        amount: isDepositMode.value
        ? (transaction.value.amount || 0)
        : -(transaction.value.amount || 0)
      };

      transactions.value.unshift(newTx);

      user.value.balance += newTx.amount;

      // Reset form
      transaction.value.amount = null;
      transaction.value.note = '';
    };

    onMounted(() => {
      // Simulate fetch
      user.value = {
        name: 'PHILIP HOUSDEN',
        phone: '062-2222222',
        id: '13/05/2004',
        balance: 1502090.9
      };
    });

    return {
      user,
      transactions,
      transaction,
      isDepositMode,
      formattedBalance,
      formatAmount,
      submitTransaction
    };
  }
});
</script>

<template>
  <div class="flex flex-col lg:flex-row gap-6 p-6 min-h-screen">
    <!-- Left Panel -->
    <div class="flex-1 bg-white rounded-xl shadow p-6">
      <!-- Profile & Balance -->
      <div class="flex items-center gap-6 mb-6">
        <img
          src="../assets/pawat.png"
          alt="Profile"
          class="w-24 h-24 rounded-full object-cover border"
        />
        <div>
          <h2 class="text-xl font-bold">{{ user.name }}</h2>
          <p class="text-sm text-gray-600">{{ user.phone }}</p>
          <p class="text-sm text-gray-600">{{ user.id }}</p>
        </div>

        <div class="ml-auto bg-gray-100 rounded-lg p-4 text-center">
          <p class="text-sm text-gray-500 font-semibold">Account Balance</p>
          <p class="text-2xl font-bold text-gray-800">{{ formattedBalance }}</p>
        </div>
      </div>

      <!-- Transactions -->
      <h3 class="text-lg font-semibold mb-3">Recent Transaction</h3>
      <table class="w-full text-sm border">
        <thead class="bg-gray-200">
          <tr>
            <th class="text-left p-2">Date</th>
            <th class="text-left p-2">Description</th>
            <th class="text-right p-2">Amount</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="tx in transactions" :key="tx.id" class="border-t">
            <td class="p-2">{{ tx.date }}</td>
            <td class="p-2">{{ tx.description }}</td>
            <td
              class="p-2 text-right font-semibold"
              :class="{
                'text-green-600': tx.amount > 0,
                'text-red-500': tx.amount < 0
              }"
            >
              {{ formatAmount(tx.amount) }}
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Right Panel -->
    <div class="w-full lg:w-80 bg-white rounded-xl shadow p-6">
      <div class="flex justify-between items-center mb-4">
        <h3 class="text-lg font-bold">
          {{ isDepositMode ? 'Deposit' : 'Withdrawal' }}
        </h3>
        <button
          @click="isDepositMode = !isDepositMode"
          class="text-gray-600 text-lg hover:text-black transition"
          title="Toggle Mode"
        >
          ☰
        </button>
      </div>

      <form @submit.prevent="submitTransaction">
        <label class="block text-sm mb-1">Amount</label>
        <div class="flex items-center border rounded px-2 mb-4">
          <span class="text-gray-500">฿</span>
          <input
            v-model.number="transaction.amount"
            type="number"
            placeholder="0.00"
            class="flex-1 border-none outline-none p-2"
          />
        </div>

        <label class="block text-sm mb-1">Note</label>
        <textarea
          v-model="transaction.note"
          rows="3"
          placeholder="Optional..."
          class="w-full border rounded p-2 mb-4"
        ></textarea>

        <button
          type="submit"
          :class="[
            'w-full py-2 text-white rounded font-medium transition',
            isDepositMode ? 'bg-green-600 hover:bg-green-700' : 'bg-red-500 hover:bg-red-600'
          ]"
        >
          {{ isDepositMode ? 'Deposit' : 'Withdraw' }}
        </button>
      </form>
    </div>
  </div>
</template>

<style scoped>
input[type="number"]::-webkit-outer-spin-button,
input[type="number"]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
</style>