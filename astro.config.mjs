import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://honda.cat',
  output: 'static',
  build: {
    format: 'directory'
  }
});
