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
      accessEvents: [],
      accessSummary: {
        success: 0,
        denied: 0,
      },
      registrations: [],
      registrationStats: {
        today: 0,
        week: 0,
        month: 0,
      },
      loading: {
        accessEvents: true,
        registrations: true,
        registrationStats: true,
      },
      error: {
        accessEvents: null,
        registrations: null,
        registrationStats: null,
      }
    };
  },
  mounted() {
    this.fetchDashboardData();
  },
  methods: {
    async fetchDashboardData() {
      await Promise.all([
        this.fetchAccessEvents(),
        this.fetchRegistrations(),
        this.fetchRegistrationStats(),
      ]);
    },

    async fetchData(endpoint, targetArray, loadingKey, errorKey) {
      this.loading[loadingKey] = true;
      this.error[errorKey] = null;
      try {
        const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${API_BASE_URL}/${endpoint}`);
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || `Failed to fetch data from ${endpoint}`);
        }
        this[targetArray] = await response.json();
      } catch (err) {
        console.error(`Error fetching from ${endpoint}:`, err);
        this.error[errorKey] = `Failed to load ${endpoint.replace('-', ' ')}.`;
      } finally {
        this.loading[loadingKey] = false;
      }
    },

    async fetchAccessEvents() {
      this.loading.accessEvents = true;
      this.error.accessEvents = null;
      try {
        const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

        const customerLogsResponse = await fetch(`${API_BASE_URL}/customer-logs`);
        if (!customerLogsResponse.ok) throw new Error(`Failed to fetch customer logs: ${customerLogsResponse.statusText}`);
        const customerLogs = await customerLogsResponse.json();

        const employeeLogsResponse = await fetch(`${API_BASE_URL}/employee-logs`);
        if (!employeeLogsResponse.ok) throw new Error(`Failed to fetch employee logs: ${employeeLogsResponse.statusText}`);
        const employeeLogs = await employeeLogsResponse.json();

        let combinedEvents = [];
        let successCount = 0;
        let deniedCount = 0;
        let idCounter = 0;

        customerLogs.forEach(log => {
          const resultText = log.Result ? 'Access Granted' : 'Access Denied';
          if (log.Result) {
            successCount++;
          } else {
            deniedCount++;
          }
          combinedEvents.push({
            id: 'cust-' + idCounter++,
            date: this.formatDate(log.Transaction_Timestamp),
            time: this.formatTime(log.Transaction_Timestamp),
            name: `${log.Name} ${log.SurName}`,
            result: resultText,
            originalType: 'customer',
            logDetails: log
          });
        });

        employeeLogs.forEach(log => {
          const resultText = log.EmResult === 'Success' ? 'Access Granted' : 'Access Denied';
          if (log.EmResult === 'Success') {
            successCount++;
          } else {
            deniedCount++;
          }
          combinedEvents.push({
            id: 'emp-' + idCounter++,
            date: this.formatDate(log.Log_Timestamp),
            time: this.formatTime(log.Log_Timestamp),
            name: `${log.EmName} ${log.EmSurName}`,
            result: resultText,
            originalType: 'employee',
            logDetails: log
          });
        });

        combinedEvents.sort((a, b) => {
            const dateA = new Date(a.logDetails.Transaction_Timestamp || a.logDetails.Log_Timestamp);
            const dateB = new Date(b.logDetails.Transaction_Timestamp || b.logDetails.Log_Timestamp);
            return dateB - dateA;
        });

        this.accessEvents = combinedEvents;
        this.accessSummary = {
          success: successCount,
          denied: deniedCount
        };

      } catch (err) {
        console.error('Error fetching access events:', err);
        this.error.accessEvents = 'Failed to load access events. Please check server logs.';
      } finally {
        this.loading.accessEvents = false;
      }
    },

    async fetchRegistrations() {
      await this.fetchData('registration-records', 'registrations', 'registrations', 'registrations');
    },

    async fetchRegistrationStats() {
      this.loading.registrationStats = true;
      this.error.registrationStats = null;
      try {
        const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
        const response = await fetch(`${API_BASE_URL}/registration-stats`);
        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to fetch registration stats');
        }
        this.registrationStats = await response.json();
      } catch (err) {
        console.error('Error fetching registration stats:', err);
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

      const yearBE = year + 543; // Convert to Buddhist Era

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
    }
  }
};
</script>

<template>
  <div class="flex h-screen text-gray-800 bg-gray-100">
    <div class="flex-1 p-6 grid grid-cols-1 lg:grid-cols-2 gap-6 overflow-auto">

      <div class="bg-white rounded-2xl shadow p-6">
        <h2 class="text-2xl font-semibold mb-4">Access Events</h2>
        <div v-if="loading.accessEvents" class="text-center text-blue-700">Loading access events...</div>
        <div v-else-if="error.accessEvents" class="text-center text-red-500">{{ error.accessEvents }}</div>
        <div v-else-if="accessEvents.length === 0" class="text-center text-gray-500">No recent access events.</div>
        <table v-else class="w-full text-sm">
          <thead>
            <tr class="border-b text-gray-500 bg-blue-50">
              <th class="text-left py-2 px-2">Date</th>
              <th class="text-left py-2 px-2">Time</th>
              <th class="text-left py-2 px-2">Name</th>
              <th class="text-left py-2 px-2">Result</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="event in accessEvents"
              :key="event.id"
              class="border-b hover:bg-gray-50 transition"
            >
              <td class="py-2 px-2">{{ event.date }}</td>
              <td class="py-2 px-2">{{ event.time }}</td>
              <td class="py-2 px-2">{{ event.name }}</td>
              <td
                :class="event.result === 'Access Granted' ? 'text-green-600 font-semibold' : 'text-red-500 font-semibold'"
                class="py-2 px-2"
              >
                {{ event.result }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="bg-white rounded-2xl shadow p-6">
        <h2 class="text-2xl font-semibold mb-4">Access Summary</h2>
        <div v-if="loading.accessEvents" class="text-center text-blue-700">Calculating summary...</div>
        <div v-else-if="error.accessEvents" class="text-center text-red-500">{{ error.accessEvents }}</div>
        <template v-else>
          <div class="text-xl mb-2">Successful: <span class="font-bold text-green-600">{{ accessSummary.success }}</span></div>
          <div class="text-xl">Denied: <span class="font-bold text-red-500">{{ accessSummary.denied }}</span></div>
        </template>
        <div class="mt-6 h-28 bg-gray-100 rounded-xl flex items-center justify-center text-gray-400">
          [Chart Placeholder - Requires a charting library like Chart.js or Echarts]
        </div>
      </div>

      <div class="bg-white rounded-2xl shadow p-6">
        <h2 class="text-2xl font-semibold mb-4">Registration Records</h2>
        <div v-if="loading.registrations" class="text-center text-blue-700">Loading registrations...</div>
        <div v-else-if="error.registrations" class="text-center text-red-500">{{ error.registrations }}</div>
        <div v-else-if="registrations.length === 0" class="text-center text-gray-500">No registration records found.</div>
        <table v-else class="w-full text-sm">
          <thead>
            <tr class="border-b text-gray-500 bg-blue-50">
              <th class="text-left py-2 px-2">Date</th>
              <th class="text-left py-2 px-2">Time</th>
              <th class="text-left py-2 px-2">Name</th>
              <th class="text-left py-2 px-2">National ID</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="reg in registrations"
              :key="reg.National_ID"
              class="border-b hover:bg-gray-50 transition"
            >
              <td class="py-2 px-2">{{ formatDate(reg.DOR) }}</td>
              <td class="py-2 px-2">{{ formatTime(reg.DOR) }}</td>
              <td class="py-2 px-2">{{ reg.Name }} {{ reg.SurName }}</td>
              <td class="py-2 px-2">{{ reg.National_ID }}</td>
            </tr>
          </tbody>
        </table>
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