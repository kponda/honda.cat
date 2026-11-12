import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://honda.cat',
  output: 'static',
  build: {
    format: 'directory'
  },
  redirects: {
    '/articles/circuit-maintenance-wire-locking-brake-fluid-tire-pressure': '/articles/circuit-maintenance-wire-locking-safety-wire-technique/'
  }
});
