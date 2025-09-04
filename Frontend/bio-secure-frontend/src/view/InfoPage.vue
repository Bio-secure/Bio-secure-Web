<script lang="ts">
import { defineComponent, ref, onMounted, computed } from 'vue';
import { useRoute } from 'vue-router';
// @ts-ignore
import authState from '../services/authService';
// @ts-ignore
import VerificationModal from '../components/VerificationModal.vue';

// Importing icons for the improved UI
import { 
  ArrowUpCircleIcon, 
  ArrowDownCircleIcon,
  PhoneIcon,
  EnvelopeIcon,
  CakeIcon,
} from '@heroicons/vue/24/outline';

interface Transaction {
  id: number;
  date: string;
  description: string;
  amount: number;
  employeeName?: string;
  note?: string;
}

export default defineComponent({
  name: 'AccountDashboard',
  components: {
    VerificationModal,
    ArrowUpCircleIcon,
    ArrowDownCircleIcon,
    PhoneIcon,
    EnvelopeIcon,
    CakeIcon,
  },
  setup() {
    const route = useRoute();
    const user = ref({
      name: '',
      surname: '',
      phone: '',
      id: '',
      balance: 0,
      face_image_url: '',
      email: '',
      birthDate: '',
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

    const formattedAmount = computed({
      get: () => {
        if (transaction.value.amount === null || transaction.value.amount === 0) return '';
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
          id: data.National_ID,
          balance: data.Balance,
          face_image_url: data.face_image_url,
          email: data.Email,
          birthDate: data.BirthDate,
        };

        if (data.transactions && data.transactions.length > 0) {
          transactions.value = data.transactions.map((tx: any) => ({
            id: tx.id,
            date: new Date(tx.created_at).toLocaleDateString('en-GB'),
            description: tx.transaction_type.charAt(0).toUpperCase() + tx.transaction_type.slice(1),
            amount: tx.transaction_type === 'deposit' ? tx.amount : -tx.amount,
            employeeName: tx.employee_name || 'N/A',
            note: tx.note
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
            employeeName: `${authState.name} ${authState.surname}`,
            note: details.note,
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
      } else {
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

    const formattedBirthDate = computed(() => {
      if (!user.value.birthDate) return 'N/A';
      return new Date(user.value.birthDate).toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'long',
        year: 'numeric'
      });
    });

    const formattedBalance = computed(() =>
      user.value.balance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
    );

    const formatAmount = (amount: number) => {
      if (amount === 0) return '-';
      const formatted = Math.abs(amount).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
      return `${amount > 0 ? '+' : '−'} ${formatted}`;
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
      formattedAmount,
      formattedBirthDate,
    };
  }
});
</script>

<template>
  <div class="min-h-screen">
    <VerificationModal
    :is-open="isVerificationModalVisible"
    :customer-id="user.id" 
    :verification-mode="verificationModeRequired"
    @close="isVerificationModalVisible = false"
    @verification-success="handleVerificationSuccess"
    @verification-fail="handleVerificationFail"
  />

    <div class="flex flex-col lg:flex-row gap-8 p-6 lg:p-8 max-w-7xl mx-auto">
      <div v-if="isLoading" class="w-full flex items-center justify-center h-96 text-lg font-semibold text-gray-600">Loading customer data...</div>
      <div v-else-if="errorMessage" class="w-full text-center text-red-600 text-lg font-semibold p-6 bg-red-50 rounded-lg">{{ errorMessage }}</div>
      
      <template v-else>
        <div class="flex-1 space-y-8">
          <div class="bg-white rounded-2xl shadow-md p-6">
            <div class="flex flex-col sm:flex-row items-center gap-6">
              <img
                v-if="user.face_image_url"
                :src="user.face_image_url"
                alt="Profile"
                class="w-28 h-28 rounded-full object-cover ring-4 ring-white shadow-lg"
              />
              <div v-else class="w-28 h-28 rounded-full bg-gray-200 flex items-center justify-center ring-4 ring-white shadow-lg">
                <span class="text-4xl text-gray-500">{{ user.name.charAt(0) }}{{ user.surname.charAt(0) }}</span>
              </div>
              
              <div class="flex-grow text-center sm:text-left">
                <h1 class="text-3xl font-bold text-gray-800">{{ fullName }}</h1>
                <p class="text-md text-gray-500 mt-1">ID: {{ user.id }}</p>

                <div class="mt-3 pt-3 border-t border-gray-100 space-y-1 text-sm text-gray-600">
                  <p class="flex items-center justify-center sm:justify-start gap-2">
                    <EnvelopeIcon class="h-4 w-4 text-gray-400" />
                    <span>{{ user.email || 'No email provided' }}</span>
                  </p>
                  <p class="flex items-center justify-center sm:justify-start gap-2">
                    <PhoneIcon class="h-4 w-4 text-gray-400" />
                    <span>{{ user.phone || 'No phone provided' }}</span>
                  </p>
                  <p class="flex items-center justify-center sm:justify-start gap-2">
                    <CakeIcon class="h-4 w-4 text-gray-400" />
                    <span>Born on {{ formattedBirthDate }}</span>
                  </p>
                </div>
              </div>

              <div class="ml-auto bg-blue-50 rounded-xl p-4 text-center border border-blue-100">
                <p class="text-sm text-blue-800 font-semibold">Account Balance</p>
                <p class="text-3xl font-bold text-blue-900">{{ formattedBalance }} ฿</p>
              </div>
            </div>
          </div>

          <div class="bg-white rounded-2xl shadow-md p-6">
            <h3 class="text-xl font-semibold mb-4 text-gray-800">Transaction History</h3>
            <div class="overflow-y-auto h-[50vh] pr-2">
              <ul v-if="transactions.length > 0" class="space-y-4">
                <li v-for="tx in transactions" :key="tx.id" class="flex items-center gap-4 p-3 rounded-lg hover:bg-gray-50">
                  <div class="flex-shrink-0">
                    <ArrowUpCircleIcon v-if="tx.amount > 0" class="h-8 w-8 text-green-500"/>
                    <ArrowDownCircleIcon v-else class="h-8 w-8 text-red-500"/>
                  </div>
                  <div class="flex-grow">
                    <p class="font-semibold text-gray-800">{{ tx.description }}</p>
                    <p class="text-sm text-gray-500">
                      By {{ tx.employeeName }} <span v-if="tx.note"> - {{ tx.note }}</span>
                    </p>
                  </div>
                  <div class="text-right flex-shrink-0">
                    <p
                      class="text-lg font-semibold"
                      :class="tx.amount > 0 ? 'text-green-600' : 'text-red-600'"
                    >
                      {{ formatAmount(tx.amount) }} ฿
                    </p>
                    <p class="text-sm text-gray-400">{{ tx.date }}</p>
                  </div>
                </li>
              </ul>
              <div v-else class="text-center py-10 text-gray-500">No transaction history found.</div>
            </div>
          </div>
        </div>

        <div class="w-full lg:w-96 bg-white rounded-2xl shadow-md p-6 h-fit">
          <h3 class="text-xl font-bold text-gray-800 mb-4">New Transaction</h3>
          
          <div class="grid grid-cols-2 gap-2 mb-6">
            <button
              type="button"
              @click="isDepositMode = true"
              :class="[
                'py-3 rounded-lg font-semibold transition',
                isDepositMode ? 'bg-green-600 text-white shadow' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              ]"
            >
              Deposit
            </button>

            <button
              type="button"
              @click="isDepositMode = false"
              :class="[
                'py-3 rounded-lg font-semibold transition',
                !isDepositMode ? 'bg-red-500 text-white shadow' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              ]"
            >
              Withdrawal
            </button>
          </div>

          <form @submit.prevent="submitTransaction">
            <label for="amount" class="block text-sm font-medium text-gray-700 mb-1">Amount</label>
            <div class="relative mb-4">
              <span class="absolute inset-y-0 left-0 pl-4 flex items-center text-2xl text-gray-500">฿</span>
              <input
                id="amount"
                v-model="formattedAmount"
                type="text"
                inputmode="decimal"
                placeholder="0.00"
                class="w-full border border-gray-300 rounded-lg p-3 pl-10 text-right text-2xl font-semibold text-gray-800 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
            </div>

            <label for="note" class="block text-sm font-medium text-gray-700 mb-1">Note (Optional)</label>
            <textarea
              id="note"
              v-model="transaction.note"
              rows="4"
              placeholder="e.g., Cash deposit"
              class="w-full border border-gray-300 rounded-lg p-3 text-base focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            ></textarea>

            <button
              type="submit"
              :class="[
                'w-full py-3 mt-4 text-white rounded-lg font-semibold text-lg transition flex items-center justify-center gap-2',
                isDepositMode ? 'bg-green-600 hover:bg-green-700' : 'bg-red-500 hover:bg-red-600'
              ]"
            >
              <ArrowUpCircleIcon v-if="isDepositMode" class="h-6 w-6"/>
              <ArrowDownCircleIcon v-else class="h-6 w-6"/>
              Submit {{ isDepositMode ? 'Deposit' : 'Withdrawal' }}
            </button>
          </form>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
/* Hides the number input spinners in Webkit browsers */
input[type="number"]::-webkit-outer-spin-button,
input[type="number"]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}
</style>