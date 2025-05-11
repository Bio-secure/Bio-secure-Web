<script setup lang="ts">
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()

const isLinkPage = computed(() => route.name === 'Link')
</script>

<template>
  <nav class="bg-[#1b2d3d] border-b-2 px-6 py-3">
    <router-link
      to="/"
      class="text-white font-bold text-xl tracking-wide hover:underline"
    >
      {{ isLinkPage ? 'Link' : 'Bio-secure' }}
    </router-link>
  </nav>
</template>
