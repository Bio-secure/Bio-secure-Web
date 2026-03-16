<script>
import EmployeeRegistrationModal from '../components/EmRegis.vue'; 
import authState from '../services/authService'; 
import { RouterLink } from 'vue-router';
import { Menu, MenuButton, MenuItems, MenuItem } from '@headlessui/vue'
import { ChevronDownIcon } from '@heroicons/vue/20/solid'
import { 
  UserPlusIcon, 
  UsersIcon, 
  CalendarDaysIcon, 
  CheckCircleIcon,
  XCircleIcon
} from '@heroicons/vue/24/outline';


export default {
  name: 'MonitoringDashboard',
  components: {
    Menu,
    MenuButton,
    MenuItems,
    MenuItem,
    ChevronDownIcon,
    EmployeeRegistrationModal,
    RouterLink,
    UserPlusIcon,
    UsersIcon,
    CalendarDaysIcon,
    CheckCircleIcon,
    XCircleIcon
  },
  data() {
    return {
      authState: authState,
      showEmployeeRegistrationModal: false, 
      
      customerEvents: [],
      employeeLogins: [],
      
      customerSummary: { success: 0, denied: 0 },
      customerEventFilter: 'all',
      customerLogPeriod: 'Recent 15',

      employeeLogPeriod: 'Recent 10', 

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
        this.fetchCustomerEvents('Recent 15'),
        this.fetchEmployeeLogins('Recent 10'),
        this.fetchRegistrations(),
        this.fetchRegistrationStats(),
      ]);
    },

    async fetchCustomerEvents(period) {
      this.customerLogPeriod = period;
      let url = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/customer-logs`;

      if (period === 'All Time') {
        url += '?show_all=true';
      } else if (period === 'Today') {
        url += '?period=today';
      } else if (period === 'This Week') {
        url += '?period=week';
      } else if (period === 'This Month') {
        url += '?period=month';
      }

      this.loading.customerEvents = true;
      this.error.customerEvents = null;
      try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch customer logs');
        
        const logs = await response.json();
        let successCount = 0;
        let deniedCount = 0;

        this.customerEvents = logs.map(log => {
          if (log.Result) successCount++;
          else deniedCount++;
          return {
            id: 'cust-' + log.LogID,
            date: this.formatDate(log.Transaction_Timestamp),
            time: this.formatTime(log.Transaction_Timestamp),
            name: `${log.Name} ${log.SurName}`.trim(),
            result: log.Result ? 'Access Granted' : 'Access Denied',
          };
        });
        this.customerSummary = { success: successCount, denied: deniedCount };
      } catch (err) {
        this.error.customerEvents = 'Failed to load customer access events.';
      } finally {
        this.loading.customerEvents = false;
      }
    },

    async fetchEmployeeLogins(period) {
      this.employeeLogPeriod = period;
      let url = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/employee-logs`;

      if (period === 'Today') {
        url += '?period=today';
      } else if (period === 'This Week') {
        url += '?period=week';
      } else if (period === 'This Month') {
        url += '?period=month';
      }

      this.loading.employeeLogins = true;
      this.error.employeeLogins = null;
      try {
        const response = await fetch(url);
        if (!response.ok) throw new Error('Failed to fetch employee logins');
        
        const logs = await response.json();
        this.employeeLogins = logs.map(log => {
          return {
            id: 'emp-' + log.LogID,
            date: this.formatDate(log.Log_Timestamp),
            time: this.formatTime(log.Log_Timestamp),
            name: `${log.EmName || ''} ${log.EmSurName || ''}`.trim() || 'Unknown',
            result: log.EmResult === 'Success' ? 'Success' : 'Failed' 
          };
        });
      } catch (err) {
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
      const options = { year: 'numeric', month: '2-digit', day: '2-digit', timeZone: 'Asia/Bangkok' };
      const formatter = new Intl.DateTimeFormat('en-GB', options);
      const parts = formatter.formatToParts(date);
      const day = parts.find(p => p.type === 'day').value;
      const month = parts.find(p => p.type === 'month').value;
      const year = parseInt(parts.find(p => p.type === 'year').value) + 543;
      return `${day}/${month}/${year}`;
    },

    formatTime(isoString) {
      if (!isoString) return '';
      const date = new Date(isoString);
      const options = { hour: '2-digit', minute: '2-digit', hour12: true, timeZone: 'Asia/Bangkok' };
      return new Intl.DateTimeFormat('en-US', options).format(date);
    },
    
    openEmployeeRegistrationModal() {
      this.showEmployeeRegistrationModal = true;
    },
    closeEmployeeRegistrationModal() {
      this.showEmployeeRegistrationModal = false;
    },
  }
};
</script>

<template>
  <div class="flex  font-sans">
    <main class="flex-1 p-6 lg:p-8 overflow-y-auto">
      <div class="mx-auto">
        <div class="mb-8">
          <h1 class="text-3xl font-bold text-gray-800">Monitoring Dashboard</h1>
        </div>

        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          <div class="bg-white p-6 rounded-2xl shadow-md flex items-center gap-5">
            <div class="bg-blue-100 text-blue-600 p-3 rounded-full">
              <UserPlusIcon class="h-7 w-7"/>
            </div>
            <div>
              <p class="text-sm font-medium text-gray-500">Registrations Today</p>
              <p class="text-3xl font-bold text-gray-800">{{ loading.registrationStats ? '...' : registrationStats.today }}</p>
            </div>
          </div>
          <div class="bg-white p-6 rounded-2xl shadow-md flex items-center gap-5">
            <div class="bg-indigo-100 text-indigo-600 p-3 rounded-full">
              <UsersIcon class="h-7 w-7"/>
            </div>
            <div>
              <p class="text-sm font-medium text-gray-500">This Week</p>
              <p class="text-3xl font-bold text-gray-800">{{ loading.registrationStats ? '...' : registrationStats.week }}</p>
            </div>
          </div>
          <div class="bg-white p-6 rounded-2xl shadow-md flex items-center gap-5">
            <div class="bg-pink-100 text-pink-600 p-3 rounded-full">
              <CalendarDaysIcon class="h-7 w-7"/>
            </div>
            <div>
              <p class="text-sm font-medium text-gray-500">This Month</p>
              <p class="text-3xl font-bold text-gray-800">{{ loading.registrationStats ? '...' : registrationStats.month }}</p>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          <div class="lg:col-span-2 bg-white rounded-2xl shadow-md p-6 flex flex-col">
            <div class="flex justify-between items-start mb-4">
                <div>
                  <h2 class="text-xl font-semibold text-gray-800">Customer Access Events</h2>
                  <p class="text-sm text-gray-500">Showing: <span class="font-medium text-gray-700">{{ customerLogPeriod }}</span></p>
                </div>
                <Menu as="div" class="relative inline-block text-left">
                  <div>
                    <MenuButton class="inline-flex w-full justify-center gap-x-1.5 rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50">
                      Filter by Time
                      <ChevronDownIcon class="-mr-1 h-5 w-5 text-gray-400" aria-hidden="true" />
                    </MenuButton>
                  </div>
                  <transition enter-active-class="transition ease-out duration-100" enter-from-class="transform opacity-0 scale-95" enter-to-class="transform opacity-100 scale-100" leave-active-class="transition ease-in duration-75" leave-from-class="transform opacity-100 scale-100" leave-to-class="transform opacity-0 scale-95">
                    <MenuItems class="absolute right-0 z-10 mt-2 w-40 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                      <div class="py-1">
                        <MenuItem v-slot="{ active }"><a href="#" @click.prevent="fetchCustomerEvents('Recent 15')" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700']">Recent 15</a></MenuItem>
                        <MenuItem v-slot="{ active }"><a href="#" @click.prevent="fetchCustomerEvents('Today')" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700']">Today</a></MenuItem>
                        <MenuItem v-slot="{ active }"><a href="#" @click.prevent="fetchCustomerEvents('This Week')" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700']">This Week</a></MenuItem>
                        <MenuItem v-slot="{ active }"><a href="#" @click.prevent="fetchCustomerEvents('This Month')" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700']">This Month</a></MenuItem>
                        <MenuItem v-slot="{ active }"><a href="#" @click.prevent="fetchCustomerEvents('All Time')" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700']">All Time</a></MenuItem>
                      </div>
                    </MenuItems>
                  </transition>
                </Menu>
            </div>

            <div class="flex items-center gap-2 mb-4">
              <button @click="customerEventFilter = 'all'" :class="['px-3 py-1 text-sm font-medium rounded-full transition', customerEventFilter === 'all' ? 'bg-blue-600 text-white shadow-sm' : 'bg-gray-200 text-gray-700 hover:bg-gray-300']">All ({{customerSummary.success + customerSummary.denied}})</button>
              <button @click="customerEventFilter = 'success'" :class="['px-3 py-1 text-sm font-medium rounded-full transition', customerEventFilter === 'success' ? 'bg-green-600 text-white shadow-sm' : 'bg-gray-200 text-gray-700 hover:bg-gray-300']">Granted ({{customerSummary.success}})</button>
              <button @click="customerEventFilter = 'denied'" :class="['px-3 py-1 text-sm font-medium rounded-full transition', customerEventFilter === 'denied' ? 'bg-red-500 text-white shadow-sm' : 'bg-gray-200 text-gray-700 hover:bg-gray-300']">Denied ({{customerSummary.denied}})</button>
            </div>

            <div v-if="loading.customerEvents" class="flex-1 flex items-center justify-center text-gray-500 h-96">Loading events...</div>
            <div v-else-if="error.customerEvents" class="flex-1 flex items-center justify-center text-red-500 h-96">{{ error.customerEvents }}</div>
            <div v-else class="overflow-y-auto -mx-6 h-96 border-t border-gray-100">
              <table class="w-full text-sm">
                <tbody>
                  <tr v-for="event in filteredCustomerEvents" :key="event.id" class="border-b border-gray-100 hover:bg-gray-50">
                    <td class="py-3 px-6 text-gray-500 whitespace-nowrap">{{ event.date }} {{ event.time }}</td>
                    <td class="py-3 px-6 text-gray-800 font-medium">{{ event.name }}</td>
                    <td class="py-3 px-6">
                      <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold" :class="event.result === 'Access Granted' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'">
                        <CheckCircleIcon v-if="event.result === 'Access Granted'" class="h-4 w-4" />
                        <XCircleIcon v-else class="h-4 w-4" />
                        {{ event.result }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-if="filteredCustomerEvents.length === 0" class="text-center py-10 text-gray-500">No matching access events found.</div>
            </div>
          </div>

          <div class="bg-white rounded-2xl shadow-md p-6 flex flex-col">
            <h2 class="text-xl font-semibold text-gray-800 mb-4">Newest Registrations</h2>
            <div v-if="loading.registrations" class="flex-1 flex items-center justify-center text-gray-500">Loading records...</div>
            <div v-else-if="error.registrations" class="flex-1 flex items-center justify-center text-red-500">{{ error.registrations }}</div>
            <div v-else class="space-y-4 overflow-y-auto -mx-6 px-6">
              <div v-for="reg in registrations" :key="reg.National_ID" class="flex items-center gap-4">
                <div class="w-10 h-10 rounded-full bg-slate-200 flex-shrink-0 flex items-center justify-center font-bold text-slate-600">
                  {{ reg.Name ? reg.Name.charAt(0) : '' }}{{ reg.SurName ? reg.SurName.charAt(0) : '' }}
                </div>
                <div>
                  <p class="font-semibold text-gray-800">{{ reg.Name }} {{ reg.SurName }}</p>
                  <p class="text-xs text-gray-500">ID: {{ reg.National_ID }}</p>
                </div>
                <div class="ml-auto text-right">
                    <p class="text-xs text-gray-400">{{ formatDate(reg.DOR) }}</p>
                    <p class="text-xs text-gray-400">{{ formatTime(reg.DOR) }}</p>
                </div>
              </div>
               <div v-if="registrations.length === 0" class="text-center py-10 text-gray-500">No registration records found.</div>
            </div>
          </div>

          <div class="lg:col-span-3 bg-white rounded-2xl shadow-md p-6 flex flex-col">
            <div class="flex justify-between items-start mb-4">
                <div>
                  <h2 class="text-xl font-semibold text-gray-800">Recent Employee Logins</h2>
                  <p class="text-sm text-gray-500">Showing: <span class="font-medium text-gray-700">{{ employeeLogPeriod }}</span></p>
                </div>
                <Menu as="div" class="relative inline-block text-left">
                  <div>
                    <MenuButton class="inline-flex w-full justify-center gap-x-1.5 rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50">
                      Filter by Time
                      <ChevronDownIcon class="-mr-1 h-5 w-5 text-gray-400" aria-hidden="true" />
                    </MenuButton>
                  </div>
                  <transition enter-active-class="transition ease-out duration-100" enter-from-class="transform opacity-0 scale-95" enter-to-class="transform opacity-100 scale-100" leave-active-class="transition ease-in duration-75" leave-from-class="transform opacity-100 scale-100" leave-to-class="transform opacity-0 scale-95">
                    <MenuItems class="absolute right-0 z-10 mt-2 w-40 origin-top-right rounded-md bg-white shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                      <div class="py-1">
                        <MenuItem v-slot="{ active }"><a href="#" @click.prevent="fetchEmployeeLogins('Recent 10')" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700']">Recent 10</a></MenuItem>
                        <MenuItem v-slot="{ active }"><a href="#" @click.prevent="fetchEmployeeLogins('Today')" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700']">Today</a></MenuItem>
                        <MenuItem v-slot="{ active }"><a href="#" @click.prevent="fetchEmployeeLogins('This Week')" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700']">This Week</a></MenuItem>
                        <MenuItem v-slot="{ active }"><a href="#" @click.prevent="fetchEmployeeLogins('This Month')" :class="[active ? 'bg-gray-100' : '', 'block px-4 py-2 text-sm text-gray-700']">This Month</a></MenuItem>
                      </div>
                    </MenuItems>
                  </transition>
                </Menu>
            </div>

            <div v-if="loading.employeeLogins" class="flex-1 flex items-center justify-center text-gray-500 h-72">Loading logins...</div>
            <div v-else-if="error.employeeLogins" class="flex-1 flex items-center justify-center text-red-500 h-72">{{ error.employeeLogins }}</div>
            <div v-else class="overflow-y-auto -mx-6 h-72 border-t border-gray-100">
              <table class="w-full text-sm">
                <tbody>
                  <tr v-for="event in employeeLogins" :key="event.id" class="border-b border-gray-100 hover:bg-gray-50">
                    <td class="py-3 px-6 text-gray-500 whitespace-nowrap">{{ event.date }} {{ event.time }}</td>
                    <td class="py-3 px-6 text-gray-800 font-medium">{{ event.name }}</td>
                    <td class="py-3 px-6">
                      <span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold" :class="event.result === 'Success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'">
                        <CheckCircleIcon v-if="event.result === 'Success'" class="h-4 w-4" />
                        <XCircleIcon v-else class="h-4 w-4" />
                        {{ event.result }}
                      </span>
                    </td>
                  </tr>
                </tbody>
              </table>
              <div v-if="employeeLogins.length === 0" class="text-center py-10 text-gray-500">No matching employee logins found.</div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <aside class=" right-0 w-80 bg-white shadow-lg flex-shrink-0 p-6 overflow-y-auto">
      <div class="flex flex-col items-center text-center">
        <div class="w-28 h-28 rounded-full bg-blue-200 flex items-center justify-center text-blue-800 text-5xl font-bold mb-4 ring-4 ring-white shadow-md">
          {{ authState.name ? authState.name.charAt(0) : '?' }}{{ authState.surname ? authState.surname.charAt(0) : '' }}
        </div>
        <p class="text-xl font-semibold text-gray-800">
          <template v-if="authState.isLoggedIn && authState.name && authState.surname">
            {{ authState.name }} {{ authState.surname }}
          </template>
          <template v-else>Not Logged In</template>
        </p>
        <span class="mt-1 bg-blue-100 text-blue-800 text-xs font-semibold px-3 py-1 rounded-full">
          {{ authState.isAdmin ? 'Administrator' : 'Employee' }}
        </span>
      </div>
      <div class="w-full mt-10 space-y-3">
        <RouterLink 
          to="/monitor/account" 
          class="w-full block text-center py-2.5 px-4 text-sm font-semibold bg-gray-200 text-gray-700 hover:bg-gray-300 rounded-lg transition"
        >
          Account Manager
        </RouterLink>
        <button
          @click="openEmployeeRegistrationModal"
          class="w-full py-2.5 px-4 text-sm font-semibold bg-blue-600 text-white hover:bg-blue-700 rounded-lg shadow-sm transition"
        >
          Register New Employee
        </button>
      </div>
    </aside>

    <EmployeeRegistrationModal 
      v-if="showEmployeeRegistrationModal" 
      @close="closeEmployeeRegistrationModal" 
    />
  </div>
</template>