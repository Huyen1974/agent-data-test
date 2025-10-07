<template>
  <v-container class="fill-height" fluid>
    <v-row align="center" justify="center">
      <v-col cols="12" sm="8" md="4">
        <v-card class="elevation-12">
          <v-toolbar color="primary" dark flat>
            <v-toolbar-title>Đăng xuất</v-toolbar-title>
          </v-toolbar>
          <v-card-text class="text-center">
            <h2>Bạn đã đăng xuất thành công.</h2>
            <p>Cảm ơn bạn đã sử dụng ứng dụng.</p>
            <v-btn color="primary" to="/" class="mt-4">
              Trở về trang chủ
            </v-btn>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>
  </v-container>
</template>

<script setup>
// No script logic needed for this simple view
</script>

<style scoped>
.fill-height {
  min-height: 100vh;
}
</style>
