/**
 * Paywall component with Supabase authentication
 */
import { useState, useEffect } from 'react';
import { supabase } from '../supabaseClient';
import { api } from '../api';
import './Paywall.css';

export default function Paywall() {
  // Get Supabase session token
  const getToken = async () => {
    const { data: { session } } = await supabase.auth.getSession();
    return session?.access_token;
  };
  const [plans, setPlans] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedTier, setSelectedTier] = useState(null);

  useEffect(() => {
    async function fetchPlans() {
      try {
        const plansData = await api.getSubscriptionPlans();
        setPlans(plansData);
      } catch (error) {
        console.error('Failed to load subscription plans:', error);
      }
    }

    fetchPlans();
  }, []);

  const handleSubscribe = async (tier) => {
    setLoading(true);
    setSelectedTier(tier);

    try {
      const { checkout_url } = await api.createCheckoutSession(tier, getToken);
      // Redirect to Stripe checkout
      window.location.href = checkout_url;
    } catch (error) {
      console.error('Failed to create checkout session:', error);
      alert('Failed to start checkout. Please try again.');
      setLoading(false);
      setSelectedTier(null);
    }
  };

  if (!plans) {
    return (
      <div className="paywall-container">
        <div className="paywall-loading">Loading subscription plans...</div>
      </div>
    );
  }

  const formatPrice = (cents, currency) => {
    const amount = (cents / 100).toFixed(2);
    const symbol = currency === 'eur' ? '€' : '$';
    return `${symbol}${amount}`;
  };

  return (
    <div className="paywall-container">
      <div className="paywall-content">
        <div className="paywall-header">
          <h1>Unlock Your Wellness Journey</h1>
          <p className="paywall-subtitle">
            You've reached the free tier limit of 2 conversations. Choose a plan to continue.
          </p>
        </div>

        <div className="pricing-cards">
          {/* Single Report */}
          <div className="pricing-card">
            <div className="pricing-header">
              <h3>{plans.single_report.name}</h3>
              <div className="pricing-price">
                {formatPrice(plans.single_report.price, plans.single_report.currency)}
              </div>
              <p className="pricing-subtitle">One-time purchase</p>
            </div>

            <div className="pricing-features">
              <ul>
                <li>✓ 5 back-and-forth interactions</li>
                <li>✓ Full council deliberation</li>
                <li>✓ Personalized recommendations</li>
                <li>✓ Access for this conversation only</li>
              </ul>
            </div>

            <button
              className="pricing-button"
              onClick={() => handleSubscribe('single_report')}
              disabled={loading}
            >
              {loading && selectedTier === 'single_report' ? 'Processing...' : 'Buy Once'}
            </button>
          </div>

          {/* Monthly Subscription */}
          <div className="pricing-card pricing-card-popular">
            <div className="pricing-badge">POPULAR</div>
            <div className="pricing-header">
              <h3>{plans.monthly.name}</h3>
              <div className="pricing-price">
                {formatPrice(plans.monthly.price, plans.monthly.currency)}
                <span className="pricing-period">/month</span>
              </div>
              <p className="pricing-subtitle">Cancel anytime</p>
            </div>

            <div className="pricing-features">
              <ul>
                <li>✓ Unlimited conversations</li>
                <li>✓ Unlimited interactions</li>
                <li>✓ Full council deliberation</li>
                <li>✓ Personalized recommendations</li>
                <li>✓ All expired reports restored</li>
              </ul>
            </div>

            <button
              className="pricing-button pricing-button-primary"
              onClick={() => handleSubscribe('monthly')}
              disabled={loading}
            >
              {loading && selectedTier === 'monthly' ? 'Processing...' : 'Subscribe Monthly'}
            </button>
          </div>

          {/* Yearly Subscription */}
          <div className="pricing-card">
            <div className="pricing-badge pricing-badge-best">BEST VALUE</div>
            <div className="pricing-header">
              <h3>{plans.yearly.name}</h3>
              <div className="pricing-price">
                {formatPrice(plans.yearly.price, plans.yearly.currency)}
                <span className="pricing-period">/year</span>
              </div>
              <p className="pricing-subtitle">Save {Math.round((1 - (plans.yearly.price / 12) / plans.monthly.price) * 100)}% vs monthly</p>
            </div>

            <div className="pricing-features">
              <ul>
                <li>✓ Unlimited conversations</li>
                <li>✓ Unlimited interactions</li>
                <li>✓ Full council deliberation</li>
                <li>✓ Personalized recommendations</li>
                <li>✓ All expired reports restored</li>
                <li>✓ Best value - 12 months for the price of 9</li>
              </ul>
            </div>

            <button
              className="pricing-button"
              onClick={() => handleSubscribe('yearly')}
              disabled={loading}
            >
              {loading && selectedTier === 'yearly' ? 'Processing...' : 'Subscribe Yearly'}
            </button>
          </div>
        </div>

        <div className="paywall-footer">
          <p>🔒 Secure payment processing by Stripe</p>
          <p className="paywall-disclaimer">
            All plans include access to our full wellness council of specialized professionals.
            Recurring subscriptions can be cancelled at any time.
          </p>
        </div>
      </div>
    </div>
  );
}
