import { createApp } from 'vue';

import App from './App.vue';
import router from './router';
import vuetify from './plugins/vuetify';

import '@mdi/font/css/materialdesignicons.css';
import './assets/main.css';

const app = createApp(App);

// Global error handler
app.config.errorHandler = (error, instance, info) => {
  console.error('[Vue Error]', {
    error,
    instance,
    info,
  });
  // You might want to send this to your error tracking service in production
};

// Warning handler
app.config.warnHandler = (msg, instance, trace) => {
  console.warn('[Vue Warning]', {
    message: msg,
    instance,
    trace,
  });
};

app.use(router).use(vuetify).mount('#app');
