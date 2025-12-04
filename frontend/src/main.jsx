/**
 * Main entry point for the Wellness Partner application
 *
 * Supabase authentication is initialized in supabaseClient.js and used throughout the app.
 * Unlike Clerk, Supabase doesn't require a provider wrapper - just import the client where needed.
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'

// Supabase client is initialized in supabaseClient.js
// No provider wrapper needed - just import { supabase } where you need it

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
