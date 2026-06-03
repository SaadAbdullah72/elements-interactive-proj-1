// main.jsx
// Vite/React entry point used by the dev server. Keep this file minimal.
// Add global providers (Redux, Context, ErrorBoundary) here when needed.
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import axios from 'axios'
import './index.css'
import App from './App.jsx'

// Global axios interceptor: automatically attach Bearer token to all requests
axios.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('authToken')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, (error) => {
  return Promise.reject(error)
})

// Handle 401 responses: token expired or invalid
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      sessionStorage.removeItem('authToken')
      sessionStorage.removeItem('userRole')
      window.location.href = '/'
    }
    return Promise.reject(error)
  }
)

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
