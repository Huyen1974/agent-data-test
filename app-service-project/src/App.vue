<template>
  <v-app>
    <v-app-bar app color="primary" dark>
      <v-toolbar-title>Knowledge Hub</v-toolbar-title>
      <v-spacer></v-spacer>
      <div v-if="isReady">
        <div v-if="user">
          <span class="mr-4">{{ user.displayName }}</span>
          <v-btn @click="signOut">Đăng xuất</v-btn>
        </div>
        <v-btn v-else @click="signInWithGoogle">Đăng nhập bằng Google</v-btn>
      </div>
    </v-app-bar>

    <v-main>
      <v-container fluid class="pa-4">
        <v-alert
          v-if="authError"
          type="error"
          density="compact"
          variant="tonal"
          class="mb-4"
          closable
        >
          {{ authError }}
        </v-alert>

        <router-view v-if="isReady" />
        <v-container v-else class="fill-height" fluid>
          <v-row align="center" justify="center">
            <v-progress-circular indeterminate color="primary"></v-progress-circular>
          </v-row>
        </v-container>
      </v-container>
    </v-main>
  </v-app>
</template>

<script setup>
import { useAuth } from '@/firebase/authService';

const { user, signInWithGoogle, signOut, isReady, authError } = useAuth();
</script>

<style>
.fill-height {
  height: 100vh;
}
</style>
