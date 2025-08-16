<script>
import EmployeeRegistrationModal from '../components/EmRegis.vue'; 
import authState from '../services/authService'; 

export default {
  name: 'MonitoringDashboard',
  components: {
    EmployeeRegistrationModal 
  },
  data() {
    return {
      authState: authState,
      showEmployeeRegistrationModal: false, 
      showAccouneManagerModal: false,
      
      customerEvents: [],
      employeeLogins: [],
      
      customerSummary: { success: 0, denied: 0 },

      // State to hold the current filter for customer events
      customerEventFilter: 'all', // 'all', 'success', or 'denied'

      registrations: [],
      registrationStats: { today: 0, week: 0, month: 0 },

      loading: {
        customerEvents: true,
        employeeLogins: true,
        registrations: true,
        registrationStats: true,
      },
      error: {
        customerEvents: null,
        employeeLogins: null,
        registrations: null,
        registrationStats: null,
      }
    };
  },
  computed: {
    // Computed property to filter the customer events list
    filteredCustomerEvents() {
      if (this.customerEventFilter === 'success') {
        return this.customerEvents.filter(event => event.result === 'Access Granted');
      }
      if (this.customerEventFilter === 'denied') {
        return this.customerEvents.filter(event => event.result === 'Access Denied');
      }
      return this.customerEvents;
    }
  },
  mounted() {
    this.fetchDashboardData();
  },
  methods: {
    async fetchDashboardData() {
      await Promise.all([
        this.fetchCustomerEvents(),
        this.fetchEmployeeLogins(),
        this.fetchRegistrations(),
        this.fetchRegistrationStats(),
      ]);
    },

    async fetchCustomerEvents() {
      this.loading.customerEvents = true;
      this.error.customerEvents = null;
      try {
        const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${API_BASE_URL}/customer-logs`);
        if (!response.ok) throw new Error('Failed to fetch customer logs');
        
        const logs = await response.json();
        let successCount = 0;
        let deniedCount = 0;

        this.customerEvents = logs.map(log => {
          if (log.Result) {
            successCount++;
          } else {
            deniedCount++;
          }
          return {
            id: 'cust-' + log.LogID,
            date: this.formatDate(log.Transaction_Timestamp),
            time: this.formatTime(log.Transaction_Timestamp),
            name: `${log.Name} ${log.SurName}`,
            result: log.Result ? 'Access Granted' : 'Access Denied',
          };
        });
        this.customerSummary = { success: successCount, denied: deniedCount };

      } catch (err) {
        console.error('Error fetching customer events:', err);
        this.error.customerEvents = 'Failed to load customer access events.';
      } finally {
        this.loading.customerEvents = false;
      }
    },

    async fetchEmployeeLogins() {
      this.loading.employeeLogins = true;
      this.error.employeeLogins = null;
      try {
        const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${API_BASE_URL}/employee-logs`);
        if (!response.ok) throw new Error('Failed to fetch employee logins');
        
        const logs = await response.json();
        this.employeeLogins = logs.map(log => {
          return {
            id: 'emp-' + log.LogID,
            date: this.formatDate(log.Log_Timestamp),
            time: this.formatTime(log.Log_Timestamp),
            name: `${log.EmName} ${log.EmSurName}`,
          };
        });
      } catch (err) {
        console.error('Error fetching employee logins:', err);
        this.error.employeeLogins = 'Failed to load employee logins.';
      } finally {
        this.loading.employeeLogins = false;
      }
    },

    async fetchRegistrations() {
      this.loading.registrations = true;
      this.error.registrations = null;
      try {
        const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${API_BASE_URL}/registration-records`);
        if (!response.ok) throw new Error('Failed to fetch registration records');
        this.registrations = await response.json();
      } catch (err) {
        this.error.registrations = 'Failed to load registrations.';
      } finally {
        this.loading.registrations = false;
      }
    },

    async fetchRegistrationStats() {
      this.loading.registrationStats = true;
      this.error.registrationStats = null;
      try {
        const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${API_BASE_URL}/registration-stats`);
        if (!response.ok) throw new Error('Failed to fetch registration stats');
        this.registrationStats = await response.json();
      } catch (err) {
        this.error.registrationStats = 'Failed to load registration stats.';
      } finally {
        this.loading.registrationStats = false;
      }
    },

    formatDate(isoString) {
      if (!isoString) return '';
      const date = new Date(isoString);
      const options = {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        timeZone: 'Asia/Bangkok'
      };
      const formatter = new Intl.DateTimeFormat('en-GB', options);
      const parts = formatter.formatToParts(date);
      let day = parts.find(p => p.type === 'day').value;
      let month = parts.find(p => p.type === 'month').value;
      let year = parseInt(parts.find(p => p.type === 'year').value);
      const yearBE = year + 543;
      return `${day}/${month}/${yearBE}`;
    },

    formatTime(isoString) {
      if (!isoString) return '';
      const date = new Date(isoString);
      const options = {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
        timeZone: 'Asia/Bangkok'
      };
      const formatter = new Intl.DateTimeFormat('en-US', options);
      return formatter.format(date);
    },
    
    openEmployeeRegistrationModal() {
      this.showEmployeeRegistrationModal = true;
    },
    closeEmployeeRegistrationModal() {
      this.showEmployeeRegistrationModal = false;
    },

    openAccountManagerModal() {
      this.showAccouneManagerModal = true;
    },
    closeAccountManagerModal() {
      this.showAccouneManagerModal = false;
    }

  }
};
</script>

<template>
  <div class="flex h-screen text-gray-800 bg-gray-100">
    <div class="flex-1 p-6 grid grid-cols-1 lg:grid-cols-2 gap-6 overflow-auto">

      <div class="bg-white rounded-2xl shadow p-6 flex flex-col">
        <h2 class="text-2xl font-semibold mb-2">Customer Access Events</h2>
        <div class="text-sm mb-2 text-gray-600">
          Successful: <span class="font-bold text-green-600">{{ customerSummary.success }}</span> | 
          Denied: <span class="font-bold text-red-500">{{ customerSummary.denied }}</span>
        </div>

        <div class="flex items-center gap-2 mb-4">
          <button 
            @click="customerEventFilter = 'all'"
            :class="[
              'px-3 py-1 text-sm font-medium rounded-full transition',
              customerEventFilter === 'all' ? 'bg-blue-600 text-white shadow' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            ]"
          >
            All
          </button>
          <button 
            @click="customerEventFilter = 'success'"
            :class="[
              'px-3 py-1 text-sm font-medium rounded-full transition',
              customerEventFilter === 'success' ? 'bg-green-600 text-white shadow' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            ]"
          >
            Granted
          </button>
          <button 
            @click="customerEventFilter = 'denied'"
            :class="[
              'px-3 py-1 text-sm font-medium rounded-full transition',
              customerEventFilter === 'denied' ? 'bg-red-500 text-white shadow' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            ]"
          >
            Denied
          </button>
        </div>

        <div v-if="loading.customerEvents" class="flex-1 flex items-center justify-center text-blue-700">Loading customer events...</div>
        <div v-else-if="error.customerEvents" class="flex-1 flex items-center justify-center text-red-500">{{ error.customerEvents }}</div>
        <div v-else-if="filteredCustomerEvents.length === 0" class="flex-1 flex items-center justify-center text-gray-500">No matching access events found.</div>
        <div v-else class="overflow-y-auto max-h-64 border rounded-lg">
          <table class="w-full text-sm">
            <thead class="sticky top-0 bg-blue-50 z-10">
              <tr class="border-b text-gray-500">
                <th class="text-left py-2 px-2">Date & Time</th>
                <th class="text-left py-2 px-2">Name</th>
                <th class="text-left py-2 px-2">Result</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="event in filteredCustomerEvents" :key="event.id" class="border-b hover:bg-gray-50 transition">
                <td class="py-2 px-2 whitespace-nowrap">{{ event.date }} {{ event.time }}</td>
                <td class="py-2 px-2">{{ event.name }}</td>
                <td :class="event.result === 'Access Granted' ? 'text-green-600' : 'text-red-500'" class="py-2 px-2 font-semibold">{{ event.result }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="bg-white rounded-2xl shadow p-6 flex flex-col">
        <h2 class="text-2xl font-semibold mb-4">Recent Employee Logins</h2>
        <div v-if="loading.employeeLogins" class="flex-1 flex items-center justify-center text-blue-700">Loading employee logins...</div>
        <div v-else-if="error.employeeLogins" class="flex-1 flex items-center justify-center text-red-500">{{ error.employeeLogins }}</div>
        <div v-else-if="employeeLogins.length === 0" class="flex-1 flex items-center justify-center text-gray-500">No recent employee logins.</div>
        <div v-else class="overflow-y-auto max-h-72 border rounded-lg">
          <table class="w-full text-sm">
            <thead class="sticky top-0 bg-blue-50 z-10">
              <tr class="border-b text-gray-500">
                <th class="text-left py-2 px-2">Date & Time</th>
                <th class="text-left py-2 px-2">Name</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="event in employeeLogins" :key="event.id" class="border-b hover:bg-gray-50 transition">
                <td class="py-2 px-2 whitespace-nowrap">{{ event.date }} {{ event.time }}</td>
                <td class="py-2 px-2">{{ event.name }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="bg-white rounded-2xl shadow p-6 flex flex-col">
        <h2 class="text-2xl font-semibold mb-4">Registration Records</h2>
        <div v-if="loading.registrations" class="flex-1 flex items-center justify-center text-blue-700">Loading registrations...</div>
        <div v-else-if="error.registrations" class="flex-1 flex items-center justify-center text-red-500">{{ error.registrations }}</div>
        <div v-else-if="registrations.length === 0" class="flex-1 flex items-center justify-center text-gray-500">No registration records found.</div>
        <div v-else class="overflow-y-auto max-h-72 border rounded-lg">
          <table class="w-full text-sm">
            <thead class="sticky top-0 bg-blue-50 z-10">
              <tr class="border-b text-gray-500">
                <th class="text-left py-2 px-2">Date</th>
                <th class="text-left py-2 px-2">Name</th>
                <th class="text-left py-2 px-2">National ID</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="reg in registrations" :key="reg.National_ID" class="border-b hover:bg-gray-50 transition">
                <td class="py-2 px-2 whitespace-nowrap">{{ formatDate(reg.DOR) }} {{ formatTime(reg.DOR) }}</td>
                <td class="py-2 px-2">{{ reg.Name }} {{ reg.SurName }}</td>
                <td class="py-2 px-2">{{ reg.National_ID }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="bg-white rounded-2xl shadow p-6">
        <h2 class="text-2xl font-semibold mb-4">Registration Stats</h2>
        <div v-if="loading.registrationStats" class="text-center text-blue-700">Loading stats...</div>
        <div v-else-if="error.registrationStats" class="text-center text-red-500">{{ error.registrationStats }}</div>
        <template v-else>
          <div class="space-y-2 text-lg">
            <div>Today: <strong>{{ registrationStats.today }}</strong></div>
            <div>This Week: <strong>{{ registrationStats.week }}</strong></div>
            <div>This Month: <strong>{{ registrationStats.month }}</strong></div>
          </div>
        </template>
      </div>
    </div>

    <aside class="w-72 bg-white shadow-md flex flex-col items-center px-6 py-8">
      <div class="w-28 h-28 rounded-full bg-blue-200 flex items-center justify-center text-blue-800 text-5xl font-bold mb-4">
        {{ authState.name ? authState.name.charAt(0) : '?' }}{{ authState.surname ? authState.surname.charAt(0) : '' }}
      </div>
      <span class="bg-blue-500 text-white text-xs px-3 py-1 rounded-full mb-2">
        {{ authState.isAdmin ? 'Admin' : 'Employee' }}
      </span>
      <p class="text-lg font-semibold text-center mb-6">
        <template v-if="authState.isLoggedIn && authState.name && authState.surname">
          {{ authState.name }} {{ authState.surname }}
        </template>
        <template v-else-if="authState.isLoggedIn">
          Logged-in Employee
        </template>
        <template v-else>
          Not Logged In
        </template>
      </p>
      <div class="w-full mt-auto space-y-3">
        <RouterLink 
          to="/monitor/account" 
          class="w-full block text-center py-2 text-white text-sm bg-blue-600 hover:bg-blue-700 rounded-xl shadow transition"
        >
          Account Manager
        </RouterLink>
        <button
          @click="openEmployeeRegistrationModal"
          class="w-full py-2 text-white text-sm bg-blue-600 hover:bg-blue-700 rounded-xl shadow transition"
        >
          Register Employee
        </button>
      </div>
    </aside>

    <EmployeeRegistrationModal 
      v-if="showEmployeeRegistrationModal" 
      @close="closeEmployeeRegistrationModal" 
    />
  </div>
</template>