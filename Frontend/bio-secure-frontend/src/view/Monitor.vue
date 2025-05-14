<script>
export default {
  data() {
    return {
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
      }
    };
  },
  mounted() {
    this.fetchAccessEvents();
    this.fetchRegistrations();
    this.fetchRegistrationStats();
  },
  methods: {
    async fetchAccessEvents() {
      // Replace this with real API call
      this.accessEvents = [
        { id: 1, date: '20/04/2568', time: '3:00 PM', name: 'Anuphat manotam', result: 'Access Grand' },
        { id: 2, date: '20/04/2568', time: '10:00 AM', name: 'Anuphat manotam', result: 'Access Grand' },
        { id: 3, date: '19/04/2568', time: '11:00 AM', name: 'Philip Housden', result: 'Access Denied' },
      ];
      this.accessSummary = {
        success: 155,
        denied: 3
      };
    },
    async fetchRegistrations() {
      // Replace this with real API call
      this.registrations = [
        { id: 1, date: '20/04/2568', time: '3:00 PM', name: 'Anuphat manotam', balance: 1000000 },
        { id: 2, date: '20/04/2568', time: '10:00 AM', name: 'Anuphat manotam', balance: 1000000 },
        { id: 3, date: '19/04/2568', time: '11:00 AM', name: 'Philip Housden', balance: 1000000 },
      ];
    },
    async fetchRegistrationStats() {
      // Replace this with real API call
      this.registrationStats = {
        today: 12,
        week: 52,
        month: 120
      };
    }
  }
};
</script>

<template>
  <div class="flex h-screen bg-gray-50 text-gray-800">
    <!-- Main Dashboard Content -->
    <div class="flex-1 p-6 grid grid-cols-1 lg:grid-cols-2 gap-6 overflow-auto">
      <!-- Access Event Table -->
      <div class="bg-white rounded-2xl shadow p-6">
        <h2 class="text-2xl font-semibold mb-4">Access Events</h2>
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b text-gray-500">
              <th class="text-left py-2">Date</th>
              <th class="text-left py-2">Time</th>
              <th class="text-left py-2">Name</th>
              <th class="text-left py-2">Result</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="event in accessEvents"
              :key="event.id"
              class="border-b hover:bg-gray-50 transition"
            >
              <td class="py-2">{{ event.date }}</td>
              <td class="py-2">{{ event.time }}</td>
              <td class="py-2">{{ event.name }}</td>
              <td
                :class="event.result === 'Access Grand' ? 'text-green-600 font-semibold' : 'text-red-500 font-semibold'"
              >
                {{ event.result }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Access Summary -->
      <div class="bg-white rounded-2xl shadow p-6">
        <h2 class="text-2xl font-semibold mb-4">Access Summary</h2>
        <div class="text-xl mb-2">Successful: <span class="font-bold text-green-600">{{ accessSummary.success }}</span></div>
        <div class="text-xl">Denied: <span class="font-bold text-red-500">{{ accessSummary.denied }}</span></div>
        <div class="mt-6 h-28 bg-gray-100 rounded-xl flex items-center justify-center text-gray-400">
          [Chart Placeholder]
        </div>
      </div>

      <!-- Registration Table -->
      <div class="bg-white rounded-2xl shadow p-6">
        <h2 class="text-2xl font-semibold mb-4">Registration Records</h2>
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b text-gray-500">
              <th class="text-left py-2">Date</th>
              <th class="text-left py-2">Time</th>
              <th class="text-left py-2">Name</th>
              <th class="text-left py-2">Balance</th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="reg in registrations"
              :key="reg.id"
              class="border-b hover:bg-gray-50 transition"
            >
              <td class="py-2">{{ reg.date }}</td>
              <td class="py-2">{{ reg.time }}</td>
              <td class="py-2">{{ reg.name }}</td>
              <td class="py-2 text-green-600 font-medium">{{ reg.balance.toLocaleString() }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- User Registration Stats -->
      <div class="bg-white rounded-2xl shadow p-6">
        <h2 class="text-2xl font-semibold mb-4">Registration Stats</h2>
        <div class="space-y-2 text-lg">
          <div>Today: <strong>{{ registrationStats.today }}</strong></div>
          <div>This Week: <strong>{{ registrationStats.week }}</strong></div>
          <div>This Month: <strong>{{ registrationStats.month }}</strong></div>
        </div>
      </div>
    </div>

    <!-- Right Sidebar with White Background -->
    <aside class="w-72 bg-white shadow-md flex flex-col items-center px-6 py-8">
      <img
        src="../assets/pawat.png"
        alt="User"
        class="w-28 h-28 rounded-full object-cover border-2 border-black shadow mb-4"
      />
      <span class="bg-blue-500 text-white text-xs px-3 py-1 rounded-full mb-2">Manager</span>
      <p class="text-lg font-semibold text-center mb-6">Pawat MungMueng</p>

      <div class="w-full mt-auto">
        <button
          class="w-full py-2 text-white text-sm bg-red-500 hover:bg-red-600 rounded-xl shadow transition"
        >
          Log Out
        </button>
      </div>
    </aside>
  </div>
</template>