"""Stripe payment integration for LLM Council."""

import os
import stripe
from typing import Dict, Any, Optional
from dotenv import load_dotenv

load_dotenv()

# Initialize Stripe with secret key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Webhook signing secret for verifying webhook signatures
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

# Subscription plan configuration
# Prices are in cents (EUR)
SUBSCRIPTION_PLANS = {
    "single_report": {
        "name": "Single Report",
        "price": 199,  # €1.99 in cents
        "currency": "eur",
        "description": "One-time purchase: 5 additional back-and-forth interactions with the council",
        "payment_mode": "payment",  # One-time payment
        "interactions": 5,  # 5 back-and-forth on top of 2 free reports
    },
    "monthly": {
        "name": "Monthly Subscription",
        "price": 799,  # €7.99 in cents
        "currency": "eur",
        "description": "Unlimited reports and interactions, billed monthly",
        "payment_mode": "subscription",
        "billing_interval": "month",
        "interactions": "unlimited",
    },
    "yearly": {
        "name": "Yearly Subscription",
        "price": 7000,  # €70 in cents
        "currency": "eur",
        "description": "Unlimited reports and interactions, billed annually",
        "payment_mode": "subscription",
        "billing_interval": "year",
        "interactions": "unlimited",
    },
}


async def create_checkout_session(
    tier: str,
    user_id: str,
    success_url: str,
    cancel_url: str
) -> Dict[str, Any]:
    """
    Create a Stripe checkout session for a subscription tier.

    Args:
        tier: Subscription tier (single_report, monthly, yearly)
        user_id: Clerk user ID (stored in metadata)
        success_url: URL to redirect on successful payment
        cancel_url: URL to redirect on cancelled payment

    Returns:
        Dict with checkout session details including session ID and URL

    Raises:
        ValueError: If tier is invalid or Stripe API fails
    """
    if tier not in SUBSCRIPTION_PLANS:
        raise ValueError(f"Invalid subscription tier: {tier}")

    plan = SUBSCRIPTION_PLANS[tier]

    try:
        # Build line item
        line_item = {
            "price_data": {
                "currency": plan["currency"],
                "product_data": {
                    "name": plan["name"],
                    "description": plan["description"],
                },
                "unit_amount": plan["price"],
            },
            "quantity": 1,
        }

        # Add recurring data for subscriptions
        if plan["payment_mode"] == "subscription":
            line_item["price_data"]["recurring"] = {
                "interval": plan["billing_interval"]
            }

        # Create checkout session
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[line_item],
            mode=plan["payment_mode"],
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=user_id,  # Store user_id for webhook processing
            metadata={
                "user_id": user_id,
                "tier": tier,
            },
        )

        return {
            "session_id": session.id,
            "url": session.url,
        }

    except stripe.error.StripeError as e:
        raise ValueError(f"Stripe API error: {str(e)}")


def verify_webhook_signature(payload: bytes, signature: str) -> Optional[Dict[str, Any]]:
    """
    Verify Stripe webhook signature and return the event.

    Args:
        payload: Raw request body as bytes
        signature: Stripe-Signature header value

    Returns:
        Stripe event dict if signature is valid, None otherwise

    Raises:
        ValueError: If webhook secret is not configured
    """
    if not STRIPE_WEBHOOK_SECRET:
        raise ValueError("STRIPE_WEBHOOK_SECRET not configured")

    try:
        event = stripe.Webhook.construct_event(
            payload, signature, STRIPE_WEBHOOK_SECRET
        )
        return event
    except stripe.error.SignatureVerificationError:
        # Invalid signature
        return None
    except Exception as e:
        # Other errors
        print(f"Webhook verification error: {e}")
        return None


def get_plan_details(tier: str) -> Optional[Dict[str, Any]]:
    """
    Get subscription plan details by tier.

    Args:
        tier: Subscription tier (single_report, monthly, yearly)

    Returns:
        Plan details dict or None if tier is invalid
    """
    return SUBSCRIPTION_PLANS.get(tier)


def get_all_plans() -> Dict[str, Dict[str, Any]]:
    """
    Get all available subscription plans.

    Returns:
        Dict of all subscription plans
    """
    return SUBSCRIPTION_PLANS


def cancel_subscription(stripe_subscription_id: str) -> None:
    """
    Cancel a Stripe subscription at the end of the current billing period.

    Args:
        stripe_subscription_id: The Stripe subscription ID to cancel

    Raises:
        ValueError: If Stripe API fails or subscription doesn't exist
    """
    try:
        stripe.Subscription.modify(
            stripe_subscription_id,
            cancel_at_period_end=True
        )
    except stripe.error.StripeError as e:
        raise ValueError(f"Failed to cancel subscription: {str(e)}")


def create_customer_portal_session(stripe_customer_id: str, return_url: str) -> str:
    """
    Create a Stripe Customer Portal session for managing payment methods and subscriptions.

    Args:
        stripe_customer_id: The Stripe customer ID
        return_url: URL to redirect to after the customer leaves the portal

    Returns:
        The Customer Portal session URL

    Raises:
        ValueError: If Stripe API fails or customer doesn't exist
    """
    try:
        session = stripe.billing_portal.Session.create(
            customer=stripe_customer_id,
            return_url=return_url,
        )
        return session.url
    except stripe.error.StripeError as e:
        raise ValueError(f"Failed to create customer portal session: {str(e)}")


def retrieve_checkout_session(session_id: str) -> Optional[Dict[str, Any]]:
    """
    Retrieve a Stripe checkout session by ID.

    This is used as a fallback for development when webhooks don't work
    (since webhooks require a public URL).

    Args:
        session_id: The Stripe checkout session ID

    Returns:
        Dict with session details or None if not found

    Raises:
        ValueError: If Stripe API fails
    """
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return {
            "id": session.id,
            "payment_status": session.payment_status,
            "status": session.status,
            "customer": session.customer,
            "subscription": session.subscription,
            "metadata": dict(session.metadata) if session.metadata else {},
        }
    except stripe.error.StripeError as e:
        raise ValueError(f"Failed to retrieve checkout session: {str(e)}")
