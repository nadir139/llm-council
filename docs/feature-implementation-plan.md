# Feature Implementation Plan - LLM Council Production

## Overview

Transform the current LLM Council app into a freemium psychological counseling service with Instagram/TikTok marketing focus.

## User Journey Summary

1. Instagram/TikTok ad → Click link
2. Land on web app → Answer 3 quick onboarding questions (anonymous)
3. First free report → Get Stage 1 (5 perspectives) + Stage 3 (synthesis)
4. Follow-up form → Answer questions about the report
5. Second free report → Generated with new context, has blurred "intriguing questions"
6. Paywall → Choose subscription (€7.99/mo, €70/yr, or €1.99 single report)
7. After payment → Access full reports with unlimited interactions
8. Grace period → 7 days to view last report, then hidden until payment

---

## Implementation Plan - Step by Step

### Feature 1: User Profile & Onboarding System

**Goal:** Capture user profile data (Gender, Age, Mood) after they try the app anonymously.

#### Backend Changes

**1.1 Update Database Schema**

Create new tables/collections:

```python
# User Profile Model
{
  "user_id": "unique_id",
  "email": "user@example.com",  # Added during account creation
  "profile": {
    "gender": "Male | Female | Other | Prefer not to say",
    "age_range": "12-17 | 18-24 | 25-34 | 35-44 | 45-54 | 55-64 | 65+",
    "mood": "Happy | I don't know | Sad"
  },
  "created_at": "2025-01-15T10:00:00Z",
  "profile_locked": true  # Cannot edit after creation
}

# Subscription Model
{
  "user_id": "unique_id",
  "tier": "free | single_report | monthly | yearly",
  "status": "active | cancelled | expired",
  "stripe_subscription_id": "sub_xxx",
  "current_period_end": "2025-02-15T10:00:00Z",
  "report_count": 2,  # For free users: max 2
  "interaction_count": 0  # For single_report: max 5
}

# Conversation/Report Enhancement
{
  "conversation_id": "existing_id",
  "user_id": "unique_id",  # NEW: Associate with user
  "report_cycle": 1,  # 1 = first free, 2 = second free, 3+ = paid
  "has_follow_up": false,  # Has user answered follow-up questions?
  "follow_up_answers": {
    "question_1": "User answer...",
    "question_2": "User answer...",
    "additional_context": "Optional user input"
  },
  "created_at": "2025-01-15T10:00:00Z",
  "expires_at": "2025-01-22T10:00:00Z",  # 7 days for free users
  "is_visible": true  # Hidden after 7 days for non-paying users
}
```

**1.2 Create Backend Endpoints**

New endpoints in `backend/main.py`:

```python
# Profile management
POST   /api/users/profile          # Create profile (after 3 questions)
GET    /api/users/profile          # Get current user profile
PATCH  /api/users/profile          # Update profile (if unlocked)

# Subscription management
GET    /api/users/subscription     # Get current subscription status
POST   /api/users/subscription/checkout  # Create Stripe checkout session
POST   /api/webhooks/stripe        # Handle Stripe webhooks

# Report access control
GET    /api/reports/{id}/access    # Check if user can access report
POST   /api/reports/{id}/restore   # Restore expired report (if paid)
```

**1.3 Update Existing Endpoints**

Modify `POST /api/conversations/{id}/message` to:
- Check user subscription tier
- Enforce report limits (2 for free, 5 for single_report, unlimited for monthly/yearly)
- Set expiration dates for free user reports
- Include profile context in LLM prompts

**Files to Modify:**
- `backend/main.py` - Add new endpoints
- `backend/storage.py` - Add user profile and subscription storage
- `backend/council.py` - Inject profile context into Stage 1 prompts
- `backend/config.py` - Add Stripe keys and subscription tiers

#### Frontend Changes

**1.4 Create Onboarding Flow**

New components:

```
frontend/src/components/
├── Onboarding.jsx           # Main onboarding flow
├── OnboardingQuestions.jsx  # 3 profile questions
├── AccountCreation.jsx      # Email/password signup after first report
└── Paywall.jsx              # Subscription selection UI
```

**Onboarding Flow:**

1. **Landing Page** (new route: `/start`)
   - Welcome message
   - "Get Started" button
   - No login required

2. **Profile Questions** (route: `/onboarding/questions`)
   - Question 1: Gender (dropdown: Male, Female, Other, Prefer not to say)
   - Question 2: Age Range (dropdown: 12-17, 18-24, 25-34, 35-44, 45-54, 55-64, 65+)
   - Question 3: Mood (3 buttons: Happy 😊 | I don't know 🤔 | Sad 😔)
   - Save to localStorage (temporary, no account yet)

3. **First Report** (route: `/report/new`)
   - User asks their first question
   - Show streaming Stage 1 + Stage 3 (NO Stage 2)
   - After completion, show follow-up form

**1.5 Follow-Up Question Form**

After Stage 3 completes, show a form at the bottom:

```jsx
// Component structure
<FollowUpForm>
  <Question>Is there anything else you'd like to add?</Question>
  <Textarea placeholder="Share any additional thoughts or context..." />
  <SubmitButton>Continue to Next Report</SubmitButton>
</FollowUpForm>
```

On submit:
- Save answers to conversation
- Trigger second report generation automatically
- Prompt account creation (email/password)

**1.6 Account Creation Prompt**

After first report + follow-up, before showing second report:

```jsx
<AccountCreation>
  <Heading>Create your account to continue</Heading>
  <Subheading>We'll save your progress and generate your personalized report</Subheading>
  <EmailInput />
  <PasswordInput />
  <SignUpButton>Create Account & Continue</SignUpButton>
</AccountCreation>
```

**Files to Create/Modify:**
- `frontend/src/components/Onboarding.jsx` (new)
- `frontend/src/components/OnboardingQuestions.jsx` (new)
- `frontend/src/components/AccountCreation.jsx` (new)
- `frontend/src/components/FollowUpForm.jsx` (new)
- `frontend/src/App.jsx` - Add new routes
- `frontend/src/api.js` - Add profile/subscription API calls

---

### Feature 2: Authentication System

**Goal:** Integrate Clerk or Auth0 for user authentication.

**Recommendation: Use Clerk** (easier React integration, generous free tier)

#### Backend Changes

**2.1 Install Clerk SDK**

```bash
uv add clerk-backend-api
```

**2.2 Add Authentication Middleware**

```python
# backend/auth.py (new file)
from clerk_backend_api import Clerk
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer

clerk = Clerk(api_key=os.getenv("CLERK_SECRET_KEY"))
security = HTTPBearer()

async def get_current_user(token: HTTPAuthorizationCredentials = Depends(security)):
    try:
        # Verify JWT token with Clerk
        user = clerk.verify_token(token.credentials)
        return user
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid authentication")

# Protected endpoint example
@app.get("/api/users/profile")
async def get_profile(user = Depends(get_current_user)):
    return get_user_profile(user.id)
```

**2.3 Protect Endpoints**

Add `user = Depends(get_current_user)` to:
- All `/api/conversations/*` endpoints
- All `/api/users/*` endpoints
- All `/api/reports/*` endpoints

Keep public:
- `/api/health` (health check)
- `/api/webhooks/stripe` (Stripe webhooks)

**Files to Create/Modify:**
- `backend/auth.py` (new)
- `backend/main.py` - Add auth middleware to routes
- `backend/config.py` - Add CLERK_SECRET_KEY

#### Frontend Changes

**2.4 Install Clerk React SDK**

```bash
cd frontend
npm install @clerk/clerk-react
```

**2.5 Wrap App with ClerkProvider**

```jsx
// frontend/src/main.jsx
import { ClerkProvider } from '@clerk/clerk-react'

const clerkPubKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY

ReactDOM.createRoot(document.getElementById('root')).render(
  <ClerkProvider publishableKey={clerkPubKey}>
    <App />
  </ClerkProvider>
)
```

**2.6 Add Authentication UI**

```jsx
// frontend/src/components/AccountCreation.jsx
import { SignUp } from '@clerk/clerk-react'

export default function AccountCreation() {
  return (
    <div className="account-creation">
      <h2>Create your account to continue</h2>
      <SignUp
        afterSignUpUrl="/report/second"
        appearance={{
          elements: {
            // Custom styling for mobile
          }
        }}
      />
    </div>
  )
}
```

**2.7 Add Auth Token to API Calls**

```javascript
// frontend/src/api.js
import { useAuth } from '@clerk/clerk-react'

// In component:
const { getToken } = useAuth()

async function sendMessage(conversationId, content) {
  const token = await getToken()

  const response = await fetch(`${API_BASE}/api/conversations/${conversationId}/message`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ content })
  })

  return response.json()
}
```

**Files to Modify:**
- `frontend/src/main.jsx` - Add ClerkProvider
- `frontend/src/api.js` - Add auth tokens to all requests
- `frontend/src/App.jsx` - Add protected routes
- `frontend/.env.local` - Add VITE_CLERK_PUBLISHABLE_KEY

---

### Feature 3: Report Interaction Flow

**Goal:** Allow users to answer follow-up questions and trigger second report generation.

#### Backend Changes

**3.1 Update Council Prompt Generation**

Modify `backend/council.py` to inject profile context:

```python
def build_stage1_prompt(user_question: str, user_profile: dict, follow_up_context: str = None):
    """Build Stage 1 prompt with user context."""

    profile_context = f"""
User Profile:
- Gender: {user_profile['gender']}
- Age Range: {user_profile['age_range']}
- Current Mood: {user_profile['mood']}
"""

    if follow_up_context:
        profile_context += f"\nAdditional Context from User:\n{follow_up_context}\n"

    prompt = f"""{SPECIALIST_ROLE_PROMPT}

{profile_context}

User Question: {user_question}

Please provide your professional perspective considering the user's profile and context above.
"""

    return prompt
```

**3.2 Add Follow-Up Question Endpoint**

```python
@app.post("/api/conversations/{conversation_id}/follow-up")
async def submit_follow_up(
    conversation_id: str,
    answers: dict,
    user = Depends(get_current_user)
):
    # Save follow-up answers
    storage.update_conversation(conversation_id, {
        "has_follow_up": True,
        "follow_up_answers": answers
    })

    # Automatically trigger second report generation
    # Use follow-up context in Stage 1 prompts
    second_report = await generate_report_with_context(
        conversation_id=conversation_id,
        user_id=user.id,
        follow_up_context=answers.get("additional_context"),
        report_cycle=2
    )

    return second_report
```

**Files to Modify:**
- `backend/council.py` - Update prompt generation
- `backend/main.py` - Add follow-up endpoint
- `backend/storage.py` - Add follow_up_answers to conversation model

#### Frontend Changes

**3.3 Create Follow-Up Form Component**

```jsx
// frontend/src/components/FollowUpForm.jsx
import { useState } from 'react'

export default function FollowUpForm({ conversationId, onSubmit }) {
  const [additionalContext, setAdditionalContext] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)

    try {
      await api.submitFollowUp(conversationId, {
        additional_context: additionalContext
      })

      onSubmit() // Navigate to account creation
    } catch (error) {
      console.error('Failed to submit follow-up:', error)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="follow-up-form">
      <h3>Is there anything else you'd like to add?</h3>
      <textarea
        value={additionalContext}
        onChange={(e) => setAdditionalContext(e.target.value)}
        placeholder="Share any additional thoughts, feelings, or context that might help us understand you better..."
        rows={4}
      />
      <button onClick={handleSubmit} disabled={loading}>
        {loading ? 'Generating your personalized report...' : 'Continue'}
      </button>
    </div>
  )
}
```

**3.4 Update ChatInterface to Show Follow-Up**

```jsx
// frontend/src/components/ChatInterface.jsx
{conversation.messages.map((message) => (
  message.role === 'assistant' && (
    <>
      <Stage1 data={message.stage1} />
      {/* Stage 2 removed from UI */}
      <Stage3 data={message.stage3} />

      {/* Show follow-up form after first report */}
      {!conversation.has_follow_up && conversation.report_cycle === 1 && (
        <FollowUpForm
          conversationId={conversation.id}
          onSubmit={() => navigate('/account/create')}
        />
      )}
    </>
  )
))}
```

**Files to Create/Modify:**
- `frontend/src/components/FollowUpForm.jsx` (new)
- `frontend/src/components/ChatInterface.jsx` - Add follow-up form
- `frontend/src/api.js` - Add submitFollowUp function

---

### Feature 4: Paywall & Subscription System

**Goal:** Integrate Stripe for subscriptions after second report.

#### Backend Changes

**4.1 Install Stripe SDK**

```bash
uv add stripe
```

**4.2 Create Stripe Checkout Endpoint**

```python
# backend/stripe_integration.py (new file)
import stripe
import os

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

SUBSCRIPTION_PLANS = {
    "monthly": {
        "price_id": "price_xxx",  # From Stripe Dashboard
        "amount": 799,  # €7.99
        "interval": "month"
    },
    "yearly": {
        "price_id": "price_yyy",
        "amount": 7000,  # €70
        "interval": "year"
    },
    "single_report": {
        "price_id": "price_zzz",
        "amount": 199,  # €1.99
        "interval": "one_time"
    }
}

async def create_checkout_session(user_id: str, plan: str, success_url: str, cancel_url: str):
    """Create Stripe checkout session."""

    plan_config = SUBSCRIPTION_PLANS[plan]

    session = stripe.checkout.Session.create(
        customer_email=user.email,
        metadata={"user_id": user_id, "plan": plan},
        line_items=[{
            "price": plan_config["price_id"],
            "quantity": 1
        }],
        mode="subscription" if plan != "single_report" else "payment",
        success_url=success_url,
        cancel_url=cancel_url
    )

    return session.url

@app.post("/api/users/subscription/checkout")
async def create_checkout(
    plan: str,
    user = Depends(get_current_user)
):
    checkout_url = await create_checkout_session(
        user_id=user.id,
        plan=plan,
        success_url=f"{FRONTEND_URL}/subscription/success",
        cancel_url=f"{FRONTEND_URL}/subscription/cancel"
    )

    return {"checkout_url": checkout_url}
```

**4.3 Handle Stripe Webhooks**

```python
@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, os.getenv("STRIPE_WEBHOOK_SECRET")
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Handle successful payment
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["metadata"]["user_id"]
        plan = session["metadata"]["plan"]

        # Update user subscription
        storage.update_subscription(user_id, {
            "tier": plan,
            "status": "active",
            "stripe_subscription_id": session.get("subscription"),
            "current_period_end": session.get("current_period_end")
        })

    # Handle subscription cancellation
    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        # Revert to free tier
        storage.update_subscription_by_stripe_id(
            subscription["id"],
            {"tier": "free", "status": "cancelled"}
        )

    return {"status": "success"}
```

**Files to Create/Modify:**
- `backend/stripe_integration.py` (new)
- `backend/main.py` - Add Stripe endpoints
- `backend/config.py` - Add Stripe keys
- `backend/storage.py` - Add subscription management

#### Frontend Changes

**4.4 Create Paywall Component**

```jsx
// frontend/src/components/Paywall.jsx
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function Paywall({ reportCycle }) {
  const [loading, setLoading] = useState(false)
  const navigate = useNavigate()

  const plans = [
    {
      id: 'single_report',
      name: 'Single Report',
      price: '€1.99',
      description: '5 interactions + final report',
      features: [
        '5 LLM interaction cycles',
        'Final comprehensive report',
        'Valid for 30 days'
      ]
    },
    {
      id: 'monthly',
      name: 'Monthly',
      price: '€7.99/mo',
      description: 'Unlimited reports & interactions',
      features: [
        'Unlimited interactions',
        'Unlimited reports',
        'Priority support',
        'Cancel anytime'
      ],
      popular: true
    },
    {
      id: 'yearly',
      name: 'Yearly',
      price: '€70/yr',
      description: 'Best value - 2 months free!',
      features: [
        'Everything in Monthly',
        'Save €25.88 per year',
        'Priority support'
      ]
    }
  ]

  const handleSelectPlan = async (planId) => {
    setLoading(true)
    try {
      const { checkout_url } = await api.createCheckoutSession(planId)
      window.location.href = checkout_url
    } catch (error) {
      console.error('Failed to create checkout:', error)
      setLoading(false)
    }
  }

  return (
    <div className="paywall">
      <div className="paywall-header">
        <h2>Continue Your Journey</h2>
        <p>You've completed {reportCycle} free reports. Choose a plan to continue:</p>
      </div>

      <div className="plans-grid">
        {plans.map((plan) => (
          <div key={plan.id} className={`plan-card ${plan.popular ? 'popular' : ''}`}>
            {plan.popular && <div className="badge">Most Popular</div>}
            <h3>{plan.name}</h3>
            <div className="price">{plan.price}</div>
            <p className="description">{plan.description}</p>
            <ul className="features">
              {plan.features.map((feature, i) => (
                <li key={i}>✓ {feature}</li>
              ))}
            </ul>
            <button
              onClick={() => handleSelectPlan(plan.id)}
              disabled={loading}
              className={plan.popular ? 'primary' : 'secondary'}
            >
              {loading ? 'Loading...' : 'Select Plan'}
            </button>
          </div>
        ))}
      </div>

      <div className="paywall-footer">
        <p className="grace-period-notice">
          💡 Your last report will remain accessible for 7 days
        </p>
      </div>
    </div>
  )
}
```

**4.5 Show Paywall After Second Report**

```jsx
// frontend/src/components/ChatInterface.jsx
{conversation.report_cycle === 2 && !userSubscription.is_paid && (
  <Paywall reportCycle={conversation.report_cycle} />
)}
```

**4.6 Blur Intriguing Questions in Second Report**

```jsx
// frontend/src/components/Stage3.jsx
<div className="final-synthesis">
  {data.content}

  {conversation.report_cycle === 2 && !userSubscription.is_paid && (
    <div className="locked-section">
      <div className="blur-overlay">
        <p className="intriguing-questions">
          {/* Show blurred preview */}
          Based on your responses, we have identified several deeper patterns...
        </p>
      </div>
      <div className="unlock-prompt">
        <LockIcon />
        <p>Unlock deeper insights and continue your journey</p>
        <button onClick={() => navigate('/subscribe')}>
          View Subscription Plans
        </button>
      </div>
    </div>
  )}
</div>
```

**Files to Create/Modify:**
- `frontend/src/components/Paywall.jsx` (new)
- `frontend/src/components/Stage3.jsx` - Add locked section
- `frontend/src/api.js` - Add createCheckoutSession function
- `frontend/src/App.jsx` - Add subscription success/cancel routes

---

### Feature 5: 7-Day Report Retention

**Goal:** Free users can access their last report for 7 days, then it's hidden.

#### Backend Changes

**5.1 Add Expiration Logic**

```python
# backend/storage.py
from datetime import datetime, timedelta

def create_conversation(user_id: str, subscription_tier: str):
    """Create new conversation with expiration for free users."""

    conversation = {
        "id": generate_id(),
        "user_id": user_id,
        "created_at": datetime.utcnow().isoformat(),
        "is_visible": True,
        "messages": []
    }

    # Free users: 7-day expiration
    if subscription_tier == "free":
        conversation["expires_at"] = (
            datetime.utcnow() + timedelta(days=7)
        ).isoformat()
    else:
        conversation["expires_at"] = None  # No expiration for paid users

    return conversation

def check_conversation_access(conversation_id: str, user_id: str):
    """Check if user can access conversation."""

    conversation = get_conversation(conversation_id)

    # Check ownership
    if conversation["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    # Check expiration for free users
    if conversation.get("expires_at"):
        expires_at = datetime.fromisoformat(conversation["expires_at"])
        if datetime.utcnow() > expires_at:
            # Hide conversation
            update_conversation(conversation_id, {"is_visible": False})
            raise HTTPException(status_code=403, detail="Report expired. Please subscribe to restore access.")

    return conversation
```

**5.2 Add Restore Endpoint**

```python
@app.post("/api/reports/{conversation_id}/restore")
async def restore_report(
    conversation_id: str,
    user = Depends(get_current_user)
):
    """Restore expired report for paid users."""

    subscription = get_subscription(user.id)

    if subscription["tier"] == "free":
        raise HTTPException(status_code=403, detail="Subscription required to restore reports")

    # Restore visibility and remove expiration
    storage.update_conversation(conversation_id, {
        "is_visible": True,
        "expires_at": None
    })

    return {"status": "restored"}
```

**Files to Modify:**
- `backend/storage.py` - Add expiration logic
- `backend/main.py` - Add restore endpoint, check access on GET requests

#### Frontend Changes

**5.3 Show Expiration Warning**

```jsx
// frontend/src/components/Sidebar.jsx
{conversations.map((conv) => {
  const daysLeft = calculateDaysLeft(conv.expires_at)

  return (
    <div key={conv.id} className="conversation-item">
      <span>{conv.title}</span>

      {conv.expires_at && daysLeft <= 3 && (
        <div className="expiration-warning">
          ⏰ {daysLeft} days left
        </div>
      )}
    </div>
  )
})}
```

**5.4 Handle Expired Reports**

```jsx
// frontend/src/components/ChatInterface.jsx
{conversation.is_visible === false && (
  <div className="expired-report">
    <LockIcon />
    <h3>This report has expired</h3>
    <p>Subscribe to restore access to all your reports</p>
    <button onClick={() => navigate('/subscribe')}>
      View Subscription Plans
    </button>
  </div>
)}
```

**Files to Modify:**
- `frontend/src/components/Sidebar.jsx` - Show expiration warnings
- `frontend/src/components/ChatInterface.jsx` - Handle expired state
- `frontend/src/utils/dates.js` (new) - Date calculation helpers

---

### Feature 6: Hide Stage 2 from Users

**Goal:** Remove Stage 2 from user-facing UI, keep backend data for analytics.

#### Backend Changes

**6.1 Keep Stage 2 Processing**

No changes needed! Stage 2 still runs in background for:
- Model ranking analytics
- Future fine-tuning data
- Admin/research purposes

**6.2 Add Admin Endpoint (Optional)**

```python
@app.get("/api/admin/conversations/{conversation_id}/stage2")
async def get_stage2_analytics(
    conversation_id: str,
    admin_key: str = Header(None)
):
    """Get Stage 2 data for analytics (admin only)."""

    if admin_key != os.getenv("ADMIN_API_KEY"):
        raise HTTPException(status_code=403, detail="Admin access required")

    conversation = storage.get_conversation(conversation_id)
    return {
        "stage2": conversation["messages"][-1]["stage2"],
        "label_to_model": conversation["messages"][-1]["metadata"]["label_to_model"],
        "aggregate_rankings": conversation["messages"][-1]["metadata"]["aggregate_rankings"]
    }
```

**Files to Modify:**
- `backend/main.py` - Add admin endpoint (optional)

#### Frontend Changes

**6.3 Remove Stage 2 from UI**

```jsx
// frontend/src/components/ChatInterface.jsx
{message.role === 'assistant' && (
  <>
    <Stage1 data={message.stage1} />
    {/* REMOVED: <Stage2 data={message.stage2} /> */}
    <Stage3 data={message.stage3} />
  </>
)}
```

**6.4 Update Tab Navigation**

Remove "Rankings" tab, keep only:
- "Individual Perspectives" (Stage 1)
- "Final Synthesis" (Stage 3)

**Files to Modify:**
- `frontend/src/components/ChatInterface.jsx` - Remove Stage 2 component
- Delete `frontend/src/components/Stage2.jsx` (or keep for admin view)
- Update CSS to remove Stage 2 styling

---

### Feature 7: Mobile Optimization & PWA

**Goal:** Ensure excellent mobile UX for Instagram/TikTok users.

#### Frontend Changes

**7.1 Add PWA Manifest**

```json
// frontend/public/manifest.json
{
  "name": "LLM Council - AI Psychological Support",
  "short_name": "LLM Council",
  "description": "Get personalized psychological insights from multiple AI specialists",
  "start_url": "/start",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#4a90e2",
  "orientation": "portrait",
  "icons": [
    {
      "src": "/icon-192.png",
      "sizes": "192x192",
      "type": "image/png"
    },
    {
      "src": "/icon-512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

**7.2 Update index.html**

```html
<!-- frontend/index.html -->
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
  <meta name="theme-color" content="#4a90e2">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="default">
  <meta name="apple-mobile-web-app-title" content="LLM Council">

  <link rel="manifest" href="/manifest.json">
  <link rel="apple-touch-icon" href="/icon-192.png">
</head>
```

**7.3 Mobile CSS Improvements**

```css
/* frontend/src/index.css - Mobile optimizations */

/* Touch-friendly buttons */
button, .button {
  min-height: 44px;
  min-width: 44px;
  font-size: 16px; /* Prevent iOS zoom */
  padding: 12px 20px;
}

/* Responsive typography */
body {
  font-size: 16px; /* Prevent iOS zoom */
  line-height: 1.5;
}

/* Mobile-friendly forms */
input, textarea {
  font-size: 16px; /* Prevent iOS zoom */
  padding: 12px;
  border-radius: 8px;
}

textarea {
  resize: vertical;
  min-height: 100px;
}

/* Optimize for mobile viewports */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    transform: translateX(-100%);
    transition: transform 0.3s ease;
  }

  .sidebar.open {
    transform: translateX(0);
  }

  .plan-card {
    width: 100%;
    margin-bottom: 16px;
  }

  .stage1-tabs {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
  }
}
```

**Files to Create/Modify:**
- `frontend/public/manifest.json` (new)
- `frontend/public/icon-192.png` (new - create app icon)
- `frontend/public/icon-512.png` (new - create app icon)
- `frontend/index.html` - Add PWA meta tags
- `frontend/src/index.css` - Add mobile optimizations

---

### Feature 8: Deployment to Production

**Goal:** Deploy backend to Railway/Fly.io and frontend to Vercel.

#### Backend Deployment

**8.1 Create Dockerfile**

```dockerfile
# Dockerfile
FROM python:3.10-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Copy application code
COPY backend/ ./backend/

# Expose port
EXPOSE 8001

# Run application
CMD ["uv", "run", "python", "-m", "backend.main"]
```

**8.2 Create Railway Config**

```json
// railway.json
{
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "Dockerfile"
  },
  "deploy": {
    "startCommand": "uv run python -m backend.main",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

**8.3 Environment Variables**

Set in Railway dashboard:
```
OPENROUTER_API_KEY=sk-or-xxx
CLERK_SECRET_KEY=sk_live_xxx
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx
ADMIN_API_KEY=your_admin_key
DATABASE_URL=postgresql://... (if using PostgreSQL)
```

**Files to Create:**
- `Dockerfile`
- `railway.json` or `fly.toml`
- `.dockerignore`

#### Frontend Deployment

**8.4 Configure Vercel**

```json
// vercel.json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "devCommand": "npm run dev",
  "installCommand": "npm install",
  "framework": "vite",
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

**8.5 Environment Variables**

Set in Vercel dashboard:
```
VITE_API_BASE_URL=https://your-backend.railway.app
VITE_CLERK_PUBLISHABLE_KEY=pk_live_xxx
```

**8.6 Update CORS in Backend**

```python
# backend/main.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://your-app.vercel.app",
        "https://llm-council.com"  # Your custom domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Files to Create/Modify:**
- `frontend/vercel.json` (new)
- `backend/main.py` - Update CORS origins

---

## Implementation Order

### Phase 1: Core Features (Week 1)
1. ✅ Feature 6: Hide Stage 2 from UI (30 min)
2. ✅ Feature 1: User profile & onboarding (1 day)
3. ✅ Feature 2: Authentication (Clerk integration) (1 day)
4. ✅ Feature 3: Report interaction flow (1 day)

### Phase 2: Monetization (Week 2)
5. ✅ Feature 4: Paywall & Stripe subscriptions (2 days)
6. ✅ Feature 5: 7-day report retention (1 day)

### Phase 3: Polish & Deploy (Week 3)
7. ✅ Feature 7: Mobile optimization & PWA (1 day)
8. ✅ Feature 8: Production deployment (1 day)

---

## Summary

**Total Development Time: ~7-10 days**

**What We're Building:**
- Freemium model with 2 free reports
- Profile-based personalization
- Instagram/TikTok optimized onboarding
- Stripe subscription system (€1.99, €7.99/mo, €70/yr)
- Mobile-first PWA
- 7-day grace period for free users

**Tech Stack (No Changes):**
- Backend: FastAPI + Python
- Frontend: React + Vite
- Auth: Clerk
- Payments: Stripe
- Hosting: Railway (backend) + Vercel (frontend)

Ready to start implementing? Let's begin with Feature 6 (hide Stage 2) since it's the quickest win!
