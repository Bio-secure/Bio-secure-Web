<script lang="ts">
import { defineComponent, ref, onMounted, computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
// @ts-ignore
import authState from '../services/authService';
// @ts-ignore
import VerificationModal from '../components/VerificationModal.vue';

interface Transaction {
  id: number;
  date: string;
  description: string;
  amount: number;
  employeeName?: string;
}

export default defineComponent({
  name: 'AccountDashboard',
  components: {
    VerificationModal
  },
  setup() {
    const route = useRoute();
    const router = useRouter();
    const user = ref({
      name: '',
      surname: '',
      phone: '',
      id: '',
      balance: 0,
      face_image_url: ''
    });

    const transactions = ref<Transaction[]>([]); 
    const transaction = ref({
      amount: null as number | null,
      note: ''
    });

    const isDepositMode = ref(true);
    const isLoading = ref(true);
    const errorMessage = ref('');
    const isVerificationModalVisible = ref(false);
    const pendingTransaction = ref(null as any);
    const verificationModeRequired = ref('face');

    // Computed property to format the amount with commas for display
    const formattedAmount = computed({
      get: () => {
        if (transaction.value.amount === null || transaction.value.amount === 0) {
          return '';
        }
        return transaction.value.amount.toLocaleString('en-US');
      },
      set: (newValue: string) => {
        const numericValue = Number(newValue.replace(/[^0-9.]/g, ''));
        transaction.value.amount = isNaN(numericValue) || numericValue === 0 ? null : numericValue;
      }
    });

    onMounted(async () => {
      const customerId = route.params.id;
      if (!customerId) {
        errorMessage.value = "No customer ID provided.";
        isLoading.value = false;
        return;
      }
      try {
        const res = await fetch(`http://localhost:8000/customer-details/${customerId}`);
        if (!res.ok) {
          const errorData = await res.json();
          throw new Error(errorData.detail || 'Failed to fetch customer data.');
        }
        const data = await res.json();
        
        user.value = {
          name: data.Name,
          surname: data.SurName,
          phone: data.phone_no,
          id: data.BirthDate,
          balance: data.Balance,
          face_image_url: data.face_image_url
        };

        if (data.transactions && data.transactions.length > 0) {
          transactions.value = data.transactions.map((tx: any) => ({
            id: tx.id,
            date: new Date(tx.created_at).toLocaleDateString('en-GB'),
            description: tx.transaction_type.charAt(0).toUpperCase() + tx.transaction_type.slice(1),
            amount: tx.transaction_type === 'deposit' ? tx.amount : -tx.amount,
            employeeName: tx.employee_name || 'N/A'
          }));
        }

      } catch (err: any) {
        errorMessage.value = err.message;
      } finally {
        isLoading.value = false;
      }
    });

    const processTransaction = async (details: any) => {
      try {
        const response = await fetch("http://localhost:8000/transaction", {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(details)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.detail);

        alert(`${details.transaction_type} successful!`);
        user.value.balance = data.new_balance;

        const newTx: Transaction = {
            id: Date.now(),
            date: new Date().toLocaleDateString('en-GB'),
            description: details.transaction_type.charAt(0).toUpperCase() + details.transaction_type.slice(1),
            amount: details.transaction_type === 'deposit' ? details.amount : -details.amount,
            employeeName: `${authState.name} ${authState.surname}`
        };
        transactions.value.unshift(newTx);
        
        transaction.value.amount = null;
        transaction.value.note = '';

      } catch (err: any) {
        alert(`Error: ${err.message}`);
      }
    };

    const submitTransaction = async () => {
      if (!transaction.value.amount || transaction.value.amount <= 0) {
        alert("Please enter a valid, positive amount.");
        return;
      }
      
      const transactionDetails = {
        customer_id: Number(route.params.id),
        employee_id: authState.employeeId,
        transaction_type: isDepositMode.value ? 'deposit' : 'withdrawal',
        amount: transaction.value.amount,
        note: transaction.value.note
      };
      
      if (transactionDetails.amount >= 1000000) {
        verificationModeRequired.value = 'full';
      } 
      else {
        verificationModeRequired.value = 'face';
      }

      pendingTransaction.value = transactionDetails;
      isVerificationModalVisible.value = true;
    };

    const handleVerificationSuccess = () => {
      processTransaction(pendingTransaction.value);
      isVerificationModalVisible.value = false;
      pendingTransaction.value = null;
    };

    const handleVerificationFail = (failMessage: string) => {
      alert(`Identity verification failed: ${failMessage}. The transaction has been cancelled.`);
      isVerificationModalVisible.value = false;
      pendingTransaction.value = null;
    };

    const formattedBalance = computed(() =>
      user.value.balance.toLocaleString(undefined, { minimumFractionDigits: 2 })
    );

    const formatAmount = (amount: number) => {
      if (amount === 0) return '-';
      return `${amount > 0 ? '+' : ''}${amount.toLocaleString()}`;
    };
    
    const fullName = computed(() => `${user.value.name} ${user.value.surname}`);

    return {
      user,
      fullName,
      transactions,
      transaction,
      isDepositMode,
      isLoading,
      errorMessage,
      formattedBalance,
      formatAmount,
      submitTransaction,
      isVerificationModalVisible,
      pendingTransaction,
      verificationModeRequired,
      handleVerificationSuccess,
      handleVerificationFail,
      formattedAmount
    };
  }
});
</script>

<template>
  <div>
    <VerificationModal
      v-if="isVerificationModalVisible"
      :customer-id="$route.params.id" 
      :verification-mode="verificationModeRequired"
      @close="isVerificationModalVisible = false"
      @verification-success="handleVerificationSuccess"
      @verification-fail="handleVerificationFail"
    />

    <div class="flex flex-col lg:flex-row gap-6 p-6 min-h-screen">
      <div v-if="isLoading" class="w-full text-center text-lg font-semibold text-gray-600">Loading customer data...</div>
      <div v-else-if="errorMessage" class="w-full text-center text-red-500 text-lg font-semibold p-4 bg-red-50 rounded-lg">{{ errorMessage }}</div>
      
      <template v-else>
        <div class="flex-1 bg-white rounded-xl shadow p-6">
          <div class="flex items-center gap-6 mb-6">
            <img
              v-if="user.face_image_url"
              :src="user.face_image_url"
              alt="Profile"
              class="w-24 h-24 rounded-full object-cover border-2 border-gray-200"
            />
            <img
              v-else
              src="../assets/default-profile.png"
              alt="Default Profile"
              class="w-24 h-24 rounded-full object-cover border-2 border-gray-200"
            />
            
            <div>
              <h2 class="text-xl font-bold">{{ fullName }}</h2>
              <p class="text-sm text-gray-600">{{ user.phone }}</p>
              <p class="text-sm text-gray-600">{{ user.id }}</p>
            </div>

            <div class="ml-auto bg-gray-100 rounded-lg p-4 text-center">
              <p class="text-sm text-gray-500 font-semibold">Account Balance</p>
              <p class="text-2xl font-bold text-gray-800">{{ formattedBalance }} ฿</p>
            </div>
          </div>

          <h3 class="text-lg font-semibold mb-3">Recent Transaction</h3>
          <table class="w-full text-sm border">
            <thead class="bg-gray-200">
              <tr>
                <th class="text-left p-2">Date</th>
                <th class="text-left p-2">Description</th>
                <th class="text-left p-2">Performed By</th>
                <th class="text-right p-2">Amount</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="transactions.length === 0">
                <td colspan="4" class="text-center p-4 text-gray-500">No transaction history found.</td>
              </tr>
              <tr v-for="tx in transactions" :key="tx.id" class="border-t">
                <td class="p-2">{{ tx.date }}</td>
                <td class="p-2">{{ tx.description }}</td>
                <td class="p-2 text-gray-600">{{ tx.employeeName }}</td>
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
                v-model="formattedAmount"
                type="text"
                inputmode="decimal"
                placeholder="0.00"
                class="flex-1 border-none outline-none p-2 text-right"
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
      </template>
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