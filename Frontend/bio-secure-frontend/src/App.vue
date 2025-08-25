<script setup lang="ts">
import NavBar from './components/NavBar.vue';
</script>

<template>
  <div class="app-container">
    <!-- Faint background image layer -->
    <div class="background-image"></div>

    <!-- Foreground content -->
    <div class="content">
      <header>
        <NavBar />
      </header>
      <div class="h-full">
        <RouterView />
      </div>
      
    </div>
  </div>
</template>

<style scoped>
.app-container {
  position: relative;
  min-height: 100vh;
  overflow: hidden;
}

.background-image {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-image: url('./assets/bank.jpg');
  background-size: cover;
  background-position: center;
  opacity: 0.15; /* Faint effect */
  z-index: 0;
  pointer-events: none;
}

.content {
  position: relative;
  z-index: 1; /* Places it above the image */
}
</style>