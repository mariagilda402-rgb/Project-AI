import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // Absoluto para o HUD servido em /nexus no Flask; evita ./assets a resolver para /assets (página em branco).
  base: '/nexus/',
  build: {
    // Recharts + framer-motion + lucide num único chunk ~600–700 kB; gzip ~200 kB — aviso padrão 500 kB é demasiado agressivo aqui.
    chunkSizeWarningLimit: 900,
  },
})
