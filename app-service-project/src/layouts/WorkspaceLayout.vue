<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useDisplay } from 'vuetify';
import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut,
} from 'firebase/auth';

import { auth } from '../firebase/config';

const props = defineProps({
  title: {
    type: String,
    default: 'Action Toolbar',
  },
  treeItems: {
    type: Array,
    default: () => [
      {
        id: 'knowledge-root',
        title: 'Sơ đồ tri thức',
        children: [
          { id: 'overview', title: 'Tổng quan' },
          { id: 'operations', title: 'Vận hành' },
          { id: 'reports', title: 'Báo cáo' },
        ],
      },
    ],
  },
});

const router = useRouter();
const display = useDisplay();
const isMobile = computed(() => display.smAndDown.value);
const drawer = ref(!isMobile.value);

watch(isMobile, (value) => {
  drawer.value = !value;
});

const normalizedTreeItems = computed(() => normalizeItems(props.treeItems));

function normalizeItems(items = []) {
  return items.map((item) => ({
    id: item.id,
    title: item.title ?? item.name ?? 'Mục chưa đặt tên',
    children: normalizeItems(item.children ?? []),
  }));
}

function toggleDrawer() {
  drawer.value = !drawer.value;
}

const user = ref(null);
const authLoading = ref(true);
const authError = ref('');

const googleProvider = new GoogleAuthProvider();
googleProvider.setCustomParameters({ prompt: 'select_account' });

const stopAuthListener = onAuthStateChanged(
  auth,
  (currentUser) => {
    user.value = currentUser;
    authError.value = '';
    authLoading.value = false;
  },
  (error) => {
    user.value = null;
    authError.value = error?.message ?? 'Không thể xác thực người dùng.';
    authLoading.value = false;
  }
);

onBeforeUnmount(() => {
  stopAuthListener?.();
  if (typeof window !== 'undefined' && window.__AUTH_TEST_API__) {
    delete window.__AUTH_TEST_API__;
  }
});

const isAuthenticated = computed(() => !!user.value);
const userDisplayName = computed(
  () => user.value?.displayName || user.value?.email || 'Tài khoản'
);

async function signInWithGoogle() {
  authError.value = '';
  try {
    await signInWithPopup(auth, googleProvider);
  } catch (error) {
    authError.value =
      error instanceof Error ? error.message : 'Đăng nhập thất bại.';
  }
}

async function signOutUser() {
  authError.value = '';
  try {
    await signOut(auth);
    user.value = null;
    authLoading.value = false;
    await router.push('/');
  } catch (error) {
    authError.value =
      error instanceof Error ? error.message : 'Đăng xuất thất bại.';
  }
}

if (typeof window !== 'undefined') {
  window.__AUTH_TEST_API__ = {
    setUser: (value) => {
      user.value = value;
    },
    setLoading: (value) => {
      authLoading.value = value;
    },
    setError: (value) => {
      authError.value = value ?? '';
    },
  };
}
</script>

<template>
  <v-app>
    <v-navigation-drawer
      v-model="drawer"
      :permanent="!isMobile"
      :temporary="isMobile"
      class="workspace-drawer"
      width="280"
      app
    >
      <v-toolbar density="compact" flat class="px-4">
        <v-toolbar-title class="text-subtitle-2 font-weight-medium">
          Danh mục
        </v-toolbar-title>
      </v-toolbar>
      <v-divider />
      <div class="drawer-scroll">
        <v-treeview
          :items="normalizedTreeItems"
          activatable
          density="compact"
          item-title="title"
          item-value="id"
          open-on-click
          color="primary"
        />
      </div>
    </v-navigation-drawer>

    <v-main class="workspace-main">
      <v-toolbar density="compact" flat class="workspace-toolbar">
        <v-btn
          v-if="isMobile"
          icon="mdi-menu"
          variant="text"
          density="compact"
          class="me-2"
          @click="toggleDrawer"
        />
        <v-toolbar-title class="text-subtitle-2 font-weight-medium">
          {{ title }}
        </v-toolbar-title>
        <v-spacer />
        <slot name="toolbar-actions">
          <v-btn density="compact" variant="tonal">Thao tác mẫu</v-btn>
        </slot>
        <div class="auth-controls ms-4 d-flex align-center">
          <v-progress-circular
            v-if="authLoading"
            size="20"
            width="2"
            indeterminate
            color="primary"
          />
          <template v-else>
            <v-btn
              v-if="!isAuthenticated"
              color="primary"
              prepend-icon="mdi-google"
              variant="outlined"
              density="compact"
              @click="signInWithGoogle"
            >
              Đăng nhập bằng Google
            </v-btn>
            <div v-else class="d-flex align-center">
              <v-chip
                size="small"
                color="primary"
                variant="tonal"
                class="me-2"
              >
                {{ userDisplayName }}
              </v-chip>
              <v-btn
                variant="text"
                density="compact"
                color="primary"
                @click="signOutUser"
              >
                Đăng xuất
              </v-btn>
            </div>
          </template>
        </div>
      </v-toolbar>

      <div class="workspace-wrapper">
        <v-alert
          v-if="authError"
          type="error"
          density="compact"
          variant="tonal"
          class="mb-4"
        >
          {{ authError }}
        </v-alert>
        <slot>
          <div class="content-placeholder text-body-2 text-medium-emphasis">
            Nội dung khu vực làm việc (placeholder).
          </div>
        </slot>
      </div>
    </v-main>
  </v-app>
</template>

<style scoped>
.workspace-drawer {
  border-right: 1px solid rgba(0, 0, 0, 0.08);
}

.drawer-scroll {
  height: calc(100% - 49px);
  overflow-y: auto;
  padding: 8px 4px 16px;
}

.workspace-main {
  background: #f4f6fb;
}

.workspace-toolbar {
  background: #ffffff;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.workspace-wrapper {
  min-height: calc(100vh - 49px);
  padding: 24px;
}

.content-placeholder {
  background: #ffffff;
  border: 1px dashed rgba(25, 118, 210, 0.4);
  border-radius: 12px;
  padding: 32px;
  text-align: center;
}

.auth-controls {
  gap: 8px;
}
</style>
