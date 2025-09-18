import { createApp } from 'vue'

import App from './App.vue'
import vuetify from './plugins/vuetify'

import '@mdi/font/css/materialdesignicons.css'
import './assets/main.css'

createApp(App).use(vuetify).mount('#app')
