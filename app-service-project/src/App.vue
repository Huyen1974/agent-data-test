<template>
  <v-app>
    <v-app-bar app color="primary" dark>
      <v-toolbar-title>Knowledge Hub</v-toolbar-title>
      <v-spacer></v-spacer>
      <div v-if="isReady">
        <div v-if="user" class="d-flex align-center">
          <v-avatar size="36" class="mr-3" color="primary">
            <v-img
              v-if="user.photoURL"
              :src="user.photoURL"
              :alt="user.displayName"
            ></v-img>
            <span v-else class="text-h6 white--text">
              {{ user.displayName ? user.displayName.charAt(0).toUpperCase() : 'U' }}
            </span>
          </v-avatar>
          <span class="mr-4">{{ user.displayName }}</span>
          <v-btn @click="signOut">Đăng xuất</v-btn>
        </div>
        <v-btn v-else @click="signInWithGoogle" :loading="isSigningIn">
          Đăng nhập bằng Google
        </v-btn>
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

    <!-- Loading overlay during sign-in -->
    <v-overlay :model-value="isSigningIn" class="align-center justify-center" persistent>
      <v-card class="pa-6 text-center" elevation="8" rounded="lg">
        <v-progress-circular indeterminate color="primary" size="64" class="mb-4"></v-progress-circular>
        <div class="text-h6">Đang đăng nhập...</div>
        <div class="text-caption text-medium-emphasis mt-2">
          Vui lòng đợi trong giây lát
        </div>
      </v-card>
    </v-overlay>
  </v-app>
</template>

<script setup>
import { useAuth } from '@/firebase/authService';

const { user, signInWithGoogle, signOut, isReady, isSigningIn, authError } = useAuth();
</script>

<style>
.fill-height {
  height: 100vh;
}
</style>
