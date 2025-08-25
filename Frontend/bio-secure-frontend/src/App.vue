<script setup lang="ts">
import NavBar from './components/NavBar.vue';
import { RouterView } from 'vue-router';
</script>

<template>
  <div class="app-container">
    <div class="background-pattern"></div>

    <div class="content">
      <header>
        <NavBar />
      </header>
      <div class="h-full">
        <RouterView />
      </div>
      
      <main>
        <RouterView />
      </main>
    </div>
  </div>
</template>

<style scoped>
.app-container {
  position: relative;
  min-height: 100vh;
  /* A very light, clean off-white or light gray for the base */
  background-color: #f7f9fc; 
}

.background-pattern {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 0;
  overflow: hidden;
  
  /* The base background color */
  background-color: #f7f9fc;
  
  /*
    Modern corporate look using large, soft, and subtle radial gradients.
    This creates a gentle "glow" effect in the corners, which feels
    professional and clean without being distracting.
  */
  background-image: 
    radial-gradient(circle at 15% 20%, rgba(200, 220, 255, 0.4), transparent 50%),
    radial-gradient(circle at 85% 80%, rgba(220, 240, 255, 0.5), transparent 60%);
  
  /* Ensure the gradients cover the whole area and don't repeat */
  background-repeat: no-repeat;
  background-size: cover;
}

.content {
  /* Content is positioned on top of the background pattern */
  position: relative;
  z-index: 1; 
  background-color: transparent; /* Makes the content area see-through to the pattern below */
}
</style>