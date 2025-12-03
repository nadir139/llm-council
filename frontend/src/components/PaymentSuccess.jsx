import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth, useUser } from '@clerk/clerk-react';
import { api } from '../api';
import './PaymentSuccess.css';

export default function PaymentSuccess() {
  const navigate = useNavigate();
  const { getToken, isLoaded: authLoaded } = useAuth();
  const { isSignedIn, isLoaded: userLoaded } = useUser();
  const [loading, setLoading] = useState(true);
  const [subscription, setSubscription] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function verifyPayment() {
      // Wait for auth to be ready
      if (!authLoaded || !userLoaded || !isSignedIn) {
        return;
      }

      try {
        // Get session_id from URL
        const urlParams = new URLSearchParams(window.location.search);
        const sessionId = urlParams.get('session_id');

        if (!sessionId) {
          setError('Missing payment session ID. Please try again or contact support.');
          setLoading(false);
          return;
        }

        // Verify the checkout session and update subscription
        // This is a fallback for development where webhooks don't work
        const result = await api.verifyCheckoutSession(sessionId, getToken);

        if (result.success && result.subscription) {
          setSubscription(result.subscription);
          setLoading(false);
        } else {
          throw new Error('Verification succeeded but subscription data missing');
        }
      } catch (err) {
        console.error('Failed to verify payment:', err);
        setError(err.message || 'Failed to verify payment status. Please contact support.');
        setLoading(false);
      }
    }

    verifyPayment();
  }, [getToken, authLoaded, userLoaded, isSignedIn]);

  const handleContinue = () => {
    // Navigate back to chat
    navigate('/');
  };

  if (loading) {
    return (
      <div className="payment-success-container">
        <div className="payment-success-content">
          <div className="payment-success-spinner"></div>
          <h2>Verifying your payment...</h2>
          <p>Please wait while we confirm your subscription.</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="payment-success-container">
        <div className="payment-success-content payment-error">
          <div className="payment-success-icon">⚠️</div>
          <h2>Payment Verification Issue</h2>
          <p>{error}</p>
          <button onClick={handleContinue} className="payment-success-button">
            Return to App
          </button>
        </div>
      </div>
    );
  }

  const getTierDisplayName = (tier) => {
    const names = {
      'single_report': 'Single Report',
      'monthly': 'Monthly Subscription',
      'yearly': 'Yearly Subscription'
    };
    return names[tier] || tier;
  };

  return (
    <div className="payment-success-container">
      <div className="payment-success-content">
        <div className="payment-success-icon">✓</div>
        <h1>Payment Successful!</h1>
        <p className="payment-success-subtitle">
          Thank you for subscribing to {getTierDisplayName(subscription?.tier)}
        </p>

        <div className="payment-success-details">
          <h3>What happens next:</h3>
          <ul>
            <li>✓ Your subscription is now active</li>
            {subscription?.tier === 'single_report' ? (
              <>
                <li>✓ You can now have 5 back-and-forth interactions</li>
                <li>✓ Get personalized wellness recommendations</li>
              </>
            ) : (
              <>
                <li>✓ Create unlimited conversations</li>
                <li>✓ Unlimited interactions with the wellness council</li>
                <li>✓ All previously expired reports have been restored</li>
              </>
            )}
          </ul>
        </div>

        <button onClick={handleContinue} className="payment-success-button">
          Start Your Wellness Journey
        </button>

        <p className="payment-success-footer">
          You'll receive a confirmation email from Stripe shortly.
        </p>
      </div>
    </div>
  );
}
