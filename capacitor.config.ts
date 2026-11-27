import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.bharatdigital.jarvis',
  appName: 'Bharat Digital Jarvis',
  webDir: 'dist',
  server: {
    androidScheme: 'https'
  }
};

export default config;
