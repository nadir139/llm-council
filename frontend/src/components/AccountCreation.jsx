/**
 * AccountCreation component using Supabase Auth
 *
 * Provides simple email/password authentication for both sign up and sign in.
 * Replaces Clerk's pre-built UI components with a custom form.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../supabaseClient';
import './AccountCreation.css';

export default function AccountCreation({ mode = 'signup', onSuccess }) {
  const isSignUp = mode === 'signup';
  const navigate = useNavigate();

  // Form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  // Handle sign up
  const handleSignUp = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      const { data, error } = await supabase.auth.signUp({
        email,
        password,
        options: {
          // Email confirmation can be enabled in Supabase dashboard
          // For development, you may want to disable email confirmation
          emailRedirectTo: `${window.location.origin}/chat`,
        },
      });

      if (error) throw error;

      if (data?.user) {
        // Check if email confirmation is required
        if (data.user.identities && data.user.identities.length === 0) {
          setMessage('Account already exists. Please sign in instead.');
        } else if (data.session) {
          // User is signed in immediately (email confirmation disabled)
          setMessage('Account created successfully! Redirecting...');
          setTimeout(() => navigate('/'), 500);
        } else {
          // Email confirmation required
          setMessage('Please check your email to confirm your account.');
        }
      }
    } catch (error) {
      setError(error.message || 'Failed to create account');
    } finally {
      setLoading(false);
    }
  };

  // Handle sign in
  const handleSignIn = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setMessage(null);

    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) throw error;

      if (data?.session) {
        setMessage('Signed in successfully! Redirecting...');
        setTimeout(() => navigate('/'), 500);
      }
    } catch (error) {
      setError(error.message || 'Failed to sign in');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = isSignUp ? handleSignUp : handleSignIn;

  return (
    <div className="account-creation">
      <div className="account-creation-container">
        <div className="account-creation-header">
          <h2>{isSignUp ? 'Create your account to continue' : 'Welcome back!'}</h2>
          <p className="account-creation-subheading">
            {isSignUp
              ? "We'll save your progress and generate your personalized report"
              : 'Sign in to access your reports and continue your journey'}
          </p>
        </div>

        <div className="clerk-form-wrapper">
          <form onSubmit={handleSubmit} className="supabase-auth-form">
            {/* Email input */}
            <div className="form-field">
              <label htmlFor="email">Email address</label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="Enter your email"
                required
                disabled={loading}
                className="clerk-input"
              />
            </div>

            {/* Password input */}
            <div className="form-field">
              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Enter your password"
                required
                minLength={6}
                disabled={loading}
                className="clerk-input"
              />
              {isSignUp && (
                <p className="field-hint">Must be at least 6 characters</p>
              )}
            </div>

            {/* Error message */}
            {error && (
              <div className="auth-message error">
                {error}
              </div>
            )}

            {/* Success message */}
            {message && (
              <div className="auth-message success">
                {message}
              </div>
            )}

            {/* Submit button */}
            <button
              type="submit"
              disabled={loading}
              className="clerk-primary-button"
            >
              {loading ? 'Loading...' : isSignUp ? 'Sign Up' : 'Sign In'}
            </button>

            {/* Toggle between sign in/sign up */}
            <div className="auth-toggle">
              {isSignUp ? (
                <p>
                  Already have an account?{' '}
                  <a href="#/signin" className="clerk-link">
                    Sign in
                  </a>
                </p>
              ) : (
                <p>
                  Don't have an account?{' '}
                  <a href="#/signup" className="clerk-link">
                    Sign up
                  </a>
                </p>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
