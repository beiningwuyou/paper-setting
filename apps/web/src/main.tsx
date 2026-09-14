import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Workflow } from './features/Workflow'
import './styles.css'
import './styles-prototype.css'
import './styles-simple.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: (count, error) => !(error instanceof Error && 'status' in error && Number((error as { status: number }).status) < 500) && count < 2 },
    mutations: { retry: false },
  },
})

createRoot(document.getElementById('root')!).render(
  <StrictMode><QueryClientProvider client={queryClient}><Workflow /></QueryClientProvider></StrictMode>,
)

if ('serviceWorker' in navigator && import.meta.env.PROD) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => undefined)
  })
}
