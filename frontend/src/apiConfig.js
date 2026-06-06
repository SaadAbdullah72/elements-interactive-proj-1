// apiConfig.js
// Central place for API endpoint configuration used by frontend
// components. This uses the Vite environment variable defined in
// frontend/.env, with a fallback to the live backend URL.
const backend = import.meta.env.VITE_BACKEND_URL || 'https://hello-world--k6076606.replit.app'
export const API_URL = backend.replace(/\/$/, '')