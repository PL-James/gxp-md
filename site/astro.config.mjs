import { defineConfig } from 'astro/config';
import tailwindcss from '@tailwindcss/vite';

export default defineConfig({
  site: 'https://gxp.md',
  output: 'static',
  vite: {
    plugins: [tailwindcss()],
  },
});
