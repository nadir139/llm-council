/**
 * Supabase client configuration
 *
 * Initialize Supabase client for authentication and database access.
 * The client uses the anon key (safe to expose) and the Supabase URL.
 */
import { createClient } from '@supabase/supabase-js';

// Supabase configuration from environment variables
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

// Validate required environment variables
if (!supabaseUrl) {
  console.error('Missing VITE_SUPABASE_URL environment variable');
}

if (!supabaseAnonKey) {
  console.error('Missing VITE_SUPABASE_ANON_KEY environment variable');
}

// Create and export Supabase client
// The anon key is safe to expose - it has row-level security policies
export const supabase = createClient(supabaseUrl, supabaseAnonKey, {
  auth: {
    // Persist session in localStorage (default behavior)
    autoRefreshToken: true,
    persistSession: true,
    detectSessionInUrl: true
  }
});
