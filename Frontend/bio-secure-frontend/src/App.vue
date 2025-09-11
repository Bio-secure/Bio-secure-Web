<script setup lang="ts">
import NavBar from './components/NavBar.vue';
import { RouterView } from 'vue-router';
</script>

<template>
  <div class="app-container min-h-screen">
    <div class="background-pattern"></div>

    <div class="content">
      <header v-if="$route.name !== 'login'" class="absolute top-0 left-0 w-full z-20">
        <NavBar />
      </header>
      <main class="relative w-full max-w-7xl mx-auto px-4">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-container {
  position: relative;
  min-height: 100vh;
  background-color: #f7f9fc; 
  overflow-x: hidden; 
}

.background-pattern {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  
  background-color: #f7f9fc;
  background-image: 
    radial-gradient(circle at 15% 20%, rgba(200, 220, 255, 0.4), transparent 50%),
    radial-gradient(circle at 85% 80%, rgba(220, 240, 255, 0.5), transparent 60%);
  background-repeat: no-repeat;
  background-size: cover;
}


.content {
  /* Content is positioned on top of the background pattern */
  position: relative;
  z-index: 1; 
  background-color: transparent;
}
</style>