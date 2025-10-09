// Simplified main.js for debugging
import { createApp } from 'vue';

const app = createApp({
  template: '<div><h1>Test App</h1><button @click="test">Test Button</button></div>',
  methods: {
    test() {
      console.log('Button clicked!');
    }
  }
});

app.mount('#app');
console.log('Simple Vue app mounted');
