<template>
  <div class="min-h-screen flex items-center justify-center">
    <div class="grid grid-cols-3 gap-28">
      <!-- Register -->
      <div class="p-10 flex flex-col items-center">
        <img src="../assets/Register.png" alt="Register" class="w-60 h-60 mb-8" />
        <RouterLink to="/register">
          <button class="mt-6 bg-blue-300 text-black font-bold text-2xl px-8 py-4 rounded-2xl shadow-md hover:bg-blue-400">
            REGISTER
          </button>
        </RouterLink>
      </div>

      <!-- Identify -->
      <div class="p-10 flex flex-col items-center">
        <img src="../assets/Identify.png" alt="Identify" class="w-60 h-60 mb-8" />
        <RouterLink to="/identify">
          <button class="mt-6 bg-blue-300 text-black font-bold text-2xl px-8 py-4 rounded-2xl shadow-md hover:bg-blue-400">
            IDENTIFY
          </button>
        </RouterLink>
      </div>

      <!-- Dashboard -->
      <div class="p-10 flex flex-col items-center">
        <img src="../assets/Monitor.png" alt="Dashboard" class="w-60 h-60 mb-8" />
        <RouterLink to="/monitor">
          <button class="mt-6 bg-blue-300 text-black font-bold text-2xl px-8 py-4 rounded-2xl shadow-md hover:bg-blue-400">
            DASHBOARD
          </button>
        </RouterLink>
      </div>
    </div>
  </div>
</template>
