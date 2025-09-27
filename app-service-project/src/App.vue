<script setup>
import { onMounted, onUnmounted } from 'vue';
import { onAuthStateChanged } from 'firebase/auth';
import { auth } from './firebase/config';
import { useAuth } from './composables/useAuth';

// Get auth state update functions
const { updateAuthState, updateAuthError } = useAuth();

let unsubscribeAuth = null;

onMounted(() => {
  // Initialize auth state listener once for the entire app
  unsubscribeAuth = onAuthStateChanged(
    auth,
    updateAuthState,
    updateAuthError
  );
});

onUnmounted(() => {
  // Cleanup auth listener when app unmounts
  if (unsubscribeAuth) {
    unsubscribeAuth();
    unsubscribeAuth = null;
  }
});
</script>

<template>
  <router-view />
</template>
