<template>
  <v-app>
    <v-app-bar app color="primary" dark>
      <v-toolbar-title>Knowledge Hub</v-toolbar-title>
      <v-spacer></v-spacer>
      <div v-if="isReady">
        <div v-if="user" class="d-flex align-center">
          <span class="mr-4">{{ user.displayName }}</span>
          <v-btn @click="signOut">Đăng xuất</v-btn>
        </div>
        <v-btn v-else @click="signInWithGoogle" :loading="isSigningIn">
          Đăng nhập bằng Google
        </v-btn>
      </div>
      <div v-else>
        <span>Loading...</span>
      </div>
    </v-app-bar>

    <v-main>
      <v-container fluid class="pa-4">
        <h1>Test Page</h1>
        <p>isReady: {{ isReady }}</p>
        <p>user: {{ user }}</p>
        <p>authError: {{ authError }}</p>

        <router-view />
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { useAuth } from '@/firebase/authService';
import { onMounted } from 'vue';

const { user, signInWithGoogle, signOut, isReady, isSigningIn, authError } = useAuth();

// Debug logging
onMounted(() => {
  console.log('[App.vue] Component mounted');
  console.log('[App.vue] isReady:', isReady.value);
  console.log('[App.vue] user:', user.value);
  console.log('[App.vue] authError:', authError.value);
});

console.log('[App.vue] Script setup executed');
console.log('[App.vue] useAuth returned:', { user, isReady, authError });
</script>

<style>
.fill-height {
  height: 100vh;
}
</style>
