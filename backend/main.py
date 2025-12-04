"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, field_validator
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio
import structlog
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

from . import db_storage
from . import config
from .database import DatabaseManager, get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings
from .auth import get_current_user, get_admin_key
from .stripe_integration import create_checkout_session, verify_webhook_signature, get_all_plans, cancel_subscription, create_customer_portal_session, retrieve_checkout_session

# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="LLM Council API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    """Initialize database connection on app startup."""
    logger.info("initializing_database")
    try:
        DatabaseManager.initialize()
        await DatabaseManager.create_tables()
        logger.info("database_ready")
    except Exception as e:
        logger.error("database_initialization_failed", error=str(e))
        raise


@app.on_event("shutdown")
async def shutdown():
    """Close database connections on shutdown."""
    logger.info("closing_database")
    await DatabaseManager.close()
    logger.info("database_closed")


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str

    @field_validator('content')
    @classmethod
    def validate_content(cls, v):
        """Validate message content to prevent abuse and injection attacks."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        if len(v) > 5000:
            raise ValueError("Message too long (max 5000 characters)")
        return v.strip()


class UpdateTitleRequest(BaseModel):
    """Request to update conversation title."""
    title: str


class FollowUpRequest(BaseModel):
    """Request to submit follow-up answers for Feature 3."""
    follow_up_answers: str

    @field_validator('follow_up_answers')
    @classmethod
    def validate_follow_up(cls, v):
        """Validate follow-up answers."""
        if not v or not v.strip():
            raise ValueError("Follow-up answers cannot be empty")
        if len(v) > 10000:  # Allow longer for follow-up answers
            raise ValueError("Follow-up answers too long (max 10000 characters)")
        return v.strip()


class CreateProfileRequest(BaseModel):
    """Request to create user profile."""
    gender: str
    age_range: str
    mood: str


class CreateCheckoutRequest(BaseModel):
    """Request to create a checkout session."""
    tier: str  # "single_report", "monthly", or "yearly"


class SubscriptionResponse(BaseModel):
    """Subscription status response."""
    user_id: str
    tier: str
    status: str
    current_period_end: Optional[str]
    created_at: str
    updated_at: str


class UserProfile(BaseModel):
    """User profile response."""
    user_id: str
    email: Optional[str]
    profile: Dict[str, str]
    created_at: str
    profile_locked: bool


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    starred: bool
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]] = []  # Default to empty list for new conversations


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations(
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """List all conversations for the current user (metadata only). Requires authentication."""
    # Filter conversations by user_id for access control
    return await db_storage.list_conversations(user_id=user["user_id"], session=session)


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(
    request: CreateConversationRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Create a new conversation. Requires authentication.

    Feature 4 & 5: Enforces paywall - free users can only create 2 conversations.
    When attempting to create a 3rd conversation, returns 402 Payment Required.
    """
    user_id = user["user_id"]

    # Get user's subscription
    subscription = await db_storage.get_subscription(user_id, session)
    if subscription is None:
        # Create default free subscription
        subscription = await db_storage.create_subscription(user_id, tier="free", session=session)

    # Feature 4: Paywall enforcement for free users
    if subscription["tier"] == "free":
        # Count existing conversations for this user
        existing_conversations = await db_storage.list_conversations(user_id=user_id, session=session)

        # Free users can create max 2 conversations (FREE_CONVERSATION_LIMIT)
        if len(existing_conversations) >= config.FREE_CONVERSATION_LIMIT:
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "payment_required",
                    "message": f"Free tier limited to {config.FREE_CONVERSATION_LIMIT} conversations. Please subscribe to continue.",
                    "current_count": len(existing_conversations),
                    "limit": config.FREE_CONVERSATION_LIMIT
                }
            )

    # Create conversation with user_id (subscription tier handled in db_storage)
    conversation = await db_storage.create_conversation(user_id=user_id, session=session)

    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Get a specific conversation with all its messages. Requires authentication."""
    conversation = await db_storage.get_conversation(conversation_id, session)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Feature 4: Check ownership - users can only access their own conversations
    if conversation.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    return conversation


@app.post("/api/conversations/{conversation_id}/message")
@limiter.limit("10/minute")  # Limit to 10 queries per minute per user
async def send_message(
    request: Request,
    conversation_id: str,
    message_request: SendMessageRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.

    Feature 3: Now injects user profile for personalized recommendations.
    """
    logger.info("message_received",
                user_id=user["user_id"],
                conversation_id=conversation_id,
                message_length=len(message_request.content))

    # Check if conversation exists
    conversation = await db_storage.get_conversation(conversation_id, session)
    if conversation is None:
        logger.error("conversation_not_found", conversation_id=conversation_id)
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Feature 4: Check ownership
    if conversation.get("user_id") != user["user_id"]:
        logger.warning("unauthorized_access_attempt",
                      user_id=user["user_id"],
                      conversation_id=conversation_id)
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    await db_storage.add_message(
        conversation_id,
        {"role": "user", "content": message_request.content},
        session
    )

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(message_request.content)
        await db_storage.update_conversation_title(conversation_id, title, session)

    # Feature 3: Get user profile for context injection
    user_profile = await db_storage.get_user_profile(user["user_id"], session)

    # Feature 3: Get follow-up context if it exists
    follow_up_context = conversation.get("follow_up_answers")

    # Run the 3-stage council process with profile and follow-up context
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        message_request.content,
        user_profile=user_profile,
        follow_up_context=follow_up_context
    )

    # Add assistant message with all stages
    await db_storage.add_message(
        conversation_id,
        {
            "role": "assistant",
            "stage1": stage1_results,
            "stage2": stage2_results,
            "stage3": stage3_result,
            "metadata": metadata
        },
        session
    )

    # Return the complete response with metadata
    # Include report_cycle for frontend to know when to show follow-up form
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata,
        "report_cycle": conversation.get("report_cycle", 0)
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
@limiter.limit("10/minute")  # Limit to 10 queries per minute per user
async def send_message_stream(
    request: Request,
    conversation_id: str,
    message_request: SendMessageRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.

    Feature 3: Now injects user profile and follow-up context for personalization.
    """
    # Check if conversation exists
    conversation = await db_storage.get_conversation(conversation_id, session)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Feature 4: Check ownership
    if conversation.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Feature 3: Get user profile for context injection
    user_profile = await db_storage.get_user_profile(user["user_id"], session)

    # Feature 3: Get follow-up context if it exists
    follow_up_context = conversation.get("follow_up_answers")

    async def event_generator():
        try:
            # Add user message
            await db_storage.add_message(
                conversation_id,
                {"role": "user", "content": message_request.content},
                session
            )

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(message_request.content))

            # Stage 1: Collect responses with profile and follow-up context
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(
                message_request.content,
                user_profile=user_profile,
                follow_up_context=follow_up_context
            )
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(message_request.content, stage1_results)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(message_request.content, stage1_results, stage2_results)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                await db_storage.update_conversation_title(conversation_id, title, session)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            await db_storage.add_message(
                conversation_id,
                {
                    "role": "assistant",
                    "stage1": stage1_results,
                    "stage2": stage2_results,
                    "stage3": stage3_result,
                    "metadata": {"label_to_model": label_to_model, "aggregate_rankings": aggregate_rankings}
                },
                session
            )

            # Reload conversation to get updated report_cycle
            conversation = await db_storage.get_conversation(conversation_id, session)

            # Send completion event with report_cycle
            yield f"data: {json.dumps({'type': 'complete', 'report_cycle': conversation.get('report_cycle', 0)})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.post("/api/conversations/{conversation_id}/follow-up")
async def submit_follow_up(
    conversation_id: str,
    request: FollowUpRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Submit follow-up answers and generate second report (Feature 3).

    This endpoint:
    1. Saves the user's follow-up answers to the conversation
    2. Increments the report_cycle counter
    3. Automatically generates a second council report with the follow-up context
    4. Returns the new report (Stage 1 + Stage 3)

    The follow-up context will be injected into all future messages in this conversation.
    """
    # Check if conversation exists
    conversation = await db_storage.get_conversation(conversation_id, session)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Feature 4: Check ownership
    if conversation.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if already submitted follow-up for this cycle
    if conversation.get("has_follow_up", False):
        raise HTTPException(
            status_code=400,
            detail="Follow-up already submitted for this report cycle"
        )

    # Save follow-up answers to conversation
    conversation = await db_storage.update_conversation_follow_up(
        conversation_id,
        request.follow_up_answers,
        session
    )

    # Get user profile for personalization
    user_profile = await db_storage.get_user_profile(user["user_id"], session)

    # Get the last user question from the conversation
    # The follow-up is answering questions about the previous report
    last_user_message = None
    for message in reversed(conversation["messages"]):
        if message["role"] == "user":
            last_user_message = message["content"]
            break

    if not last_user_message:
        raise HTTPException(
            status_code=400,
            detail="No previous question found to generate follow-up report"
        )

    # Generate second report with follow-up context
    # Note: We re-ask the same question but now with follow-up context injected
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        last_user_message,
        user_profile=user_profile,
        follow_up_context=request.follow_up_answers
    )

    # Add assistant message with the new report
    await db_storage.add_message(
        conversation_id,
        {
            "role": "assistant",
            "stage1": stage1_results,
            "stage2": stage2_results,
            "stage3": stage3_result,
            "metadata": metadata
        },
        session
    )

    # Reload conversation again to get final state
    conversation = await db_storage.get_conversation(conversation_id, session)

    # Return the new report
    return {
        "stage1": stage1_results,
        "stage3": stage3_result,  # Frontend only displays Stage 1 and Stage 3
        "metadata": metadata,
        "report_cycle": conversation.get("report_cycle", 0),
        "message": "Second report generated successfully with follow-up context"
    }


@app.post("/api/conversations/{conversation_id}/star")
async def toggle_star_conversation(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Toggle the starred status of a conversation. Requires authentication."""
    # Feature 4: Check ownership before allowing star
    conversation = await db_storage.get_conversation(conversation_id, session)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        result = await db_storage.toggle_conversation_star(conversation_id, session)
        return {"starred": result.get("starred", False)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.patch("/api/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: str,
    request: UpdateTitleRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Update the title of a conversation. Requires authentication."""
    # Feature 4: Check ownership before allowing rename
    conversation = await db_storage.get_conversation(conversation_id, session)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        await db_storage.update_conversation_title(conversation_id, request.title, session)
        return {"title": request.title}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Delete a conversation. Requires authentication."""
    # Feature 4: Check ownership before allowing delete
    conversation = await db_storage.get_conversation(conversation_id, session)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if conversation.get("user_id") != user["user_id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    await db_storage.delete_conversation(conversation_id, session)
    return {"deleted": True}


@app.get("/api/admin/conversations/{conversation_id}/stage2")
async def get_stage2_analytics(
    conversation_id: str,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get Stage 2 data for analytics and research (admin only).

    This endpoint is hidden from regular users and requires an admin API key.
    Stage 2 contains:
    - Raw peer review rankings from each model
    - Label-to-model mapping (de-anonymization data)
    - Aggregate rankings (street cred scores)

    Usage:
    curl -H "X-Admin-Key: your_admin_key" http://localhost:8001/api/admin/conversations/{id}/stage2
    """
    # Verify admin key
    if x_admin_key != config.ADMIN_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Admin access required. Please provide a valid X-Admin-Key header."
        )

    # Get the conversation
    conversation = await db_storage.get_conversation(conversation_id, session)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Extract Stage 2 data from all messages
    stage2_analytics = []

    for idx, message in enumerate(conversation["messages"]):
        if message["role"] == "assistant" and "stage2" in message:
            # Extract Stage 2 data
            analytics_entry = {
                "message_index": idx,
                "user_question": conversation["messages"][idx - 1]["content"] if idx > 0 else "N/A",
                "stage2": message["stage2"],
                "metadata": {
                    "label_to_model": message.get("metadata", {}).get("label_to_model", {}),
                    "aggregate_rankings": message.get("metadata", {}).get("aggregate_rankings", []),
                    "is_crisis": message.get("metadata", {}).get("is_crisis", False)
                }
            }
            stage2_analytics.append(analytics_entry)

    if not stage2_analytics:
        return {
            "conversation_id": conversation_id,
            "title": conversation.get("title", "Untitled"),
            "created_at": conversation.get("created_at"),
            "message": "No Stage 2 data found in this conversation",
            "stage2_data": []
        }

    return {
        "conversation_id": conversation_id,
        "title": conversation.get("title", "Untitled"),
        "created_at": conversation.get("created_at"),
        "total_interactions": len(stage2_analytics),
        "stage2_data": stage2_analytics,
        "note": "This data is for analytics and research purposes. Stage 2 is hidden from end users."
    }


# User Profile Endpoints


@app.post("/api/users/profile", response_model=UserProfile)
async def create_profile(
    request: CreateProfileRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Create a user profile (after onboarding questions).
    Profile is locked after creation and cannot be edited.
    """
    # Check if profile already exists
    existing_profile = await db_storage.get_user_profile(user["user_id"], session)
    if existing_profile:
        raise HTTPException(
            status_code=400,
            detail="Profile already exists and is locked"
        )

    # Create profile
    profile = await db_storage.create_user_profile(
        user_id=user["user_id"],
        profile_data={
            "email": user["email"],
            "gender": request.gender,
            "age_range": request.age_range,
            "mood": request.mood
        },
        session=session
    )

    return profile


@app.get("/api/users/profile", response_model=UserProfile)
async def get_profile(
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """Get the current user's profile."""
    profile = await db_storage.get_user_profile(user["user_id"], session)

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Profile not found. Please complete onboarding."
        )

    return profile


@app.patch("/api/users/profile", response_model=UserProfile)
async def update_profile(
    request: CreateProfileRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Update user profile (only if not locked).
    Note: Profiles are locked by default after creation per spec.
    """
    try:
        profile = await db_storage.update_user_profile(
            user_id=user["user_id"],
            profile_data={
                "gender": request.gender,
                "age_range": request.age_range,
                "mood": request.mood
            },
            session=session
        )
        return profile
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# Subscription and Payment Endpoints (Feature 4)


@app.get("/api/subscription/plans")
async def get_subscription_plans():
    """
    Get all available subscription plans.
    Public endpoint - no authentication required.
    """
    return get_all_plans()


@app.get("/api/subscription", response_model=SubscriptionResponse)
async def get_user_subscription(
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get the current user's subscription status.
    Creates a free subscription if none exists.
    """
    subscription = await db_storage.get_subscription(user["user_id"], session)

    if subscription is None:
        # Create default free subscription
        subscription = await db_storage.create_subscription(user["user_id"], tier="free", session=session)

    return subscription


@app.post("/api/subscription/checkout")
async def create_subscription_checkout(
    request: CreateCheckoutRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a Stripe checkout session for a subscription purchase.
    Returns the checkout session URL to redirect the user.
    """
    # Validate tier
    valid_tiers = ["single_report", "monthly", "yearly"]
    if request.tier not in valid_tiers:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid tier. Must be one of: {', '.join(valid_tiers)}"
        )

    # Create checkout session with frontend URLs
    # TODO: Update these URLs for production deployment
    frontend_base = "http://localhost:5173"
    success_url = f"{frontend_base}/payment-success?session_id={{CHECKOUT_SESSION_ID}}"
    cancel_url = f"{frontend_base}/paywall"

    try:
        session = await create_checkout_session(
            tier=request.tier,
            user_id=user["user_id"],
            success_url=success_url,
            cancel_url=cancel_url
        )

        return {
            "checkout_url": session["url"],
            "session_id": session["session_id"]
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/subscription/cancel")
async def cancel_user_subscription(
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Cancel the user's recurring subscription at the end of the current billing period.
    Only works for active recurring subscriptions (monthly, yearly).
    """
    # Get user's subscription
    subscription = await db_storage.get_subscription(user["user_id"], session)

    if subscription is None:
        raise HTTPException(status_code=404, detail="No subscription found")

    # Check if user has an active recurring subscription
    if subscription.get("tier") not in ["monthly", "yearly"]:
        raise HTTPException(
            status_code=400,
            detail="Only recurring subscriptions can be cancelled"
        )

    if subscription.get("status") != "active":
        raise HTTPException(
            status_code=400,
            detail="Subscription is not active"
        )

    # Get Stripe subscription ID
    stripe_sub_id = subscription.get("stripe_subscription_id")
    if not stripe_sub_id:
        raise HTTPException(
            status_code=400,
            detail="No Stripe subscription ID found"
        )

    # Cancel the subscription in Stripe
    try:
        cancel_subscription(stripe_sub_id)

        # Update local status to reflect cancellation
        await db_storage.update_subscription(
            user["user_id"],
            {"status": "cancelled"},
            session
        )

        return {
            "message": "Subscription cancelled successfully. Access will continue until the end of the current billing period.",
            "subscription": await db_storage.get_subscription(user["user_id"], session)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/subscription/portal")
async def get_subscription_portal(
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Get the Stripe Customer Portal URL for managing payment methods.
    Creates a session that redirects back to the settings page.
    """
    # Get user's subscription
    subscription = await db_storage.get_subscription(user["user_id"], session)

    if subscription is None:
        raise HTTPException(status_code=404, detail="No subscription found")

    # Check if user has a Stripe customer ID
    stripe_customer_id = subscription.get("stripe_customer_id")
    if not stripe_customer_id:
        raise HTTPException(
            status_code=400,
            detail="No payment method on file. Please purchase a plan first."
        )

    # Create Customer Portal session
    frontend_base = "http://localhost:5173"
    return_url = f"{frontend_base}/settings"

    try:
        portal_url = create_customer_portal_session(stripe_customer_id, return_url)

        return {
            "portal_url": portal_url
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


class VerifySessionRequest(BaseModel):
    """Request to verify a checkout session."""
    session_id: str


@app.post("/api/subscription/verify-session")
async def verify_checkout_session_endpoint(
    request: VerifySessionRequest,
    user: Dict[str, Any] = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session)
):
    """
    Verify a Stripe checkout session and update subscription.

    This is a fallback for development where webhooks don't work
    (since webhooks require a public URL). In production, webhooks
    should handle subscription updates.
    """
    try:
        # Retrieve the checkout session from Stripe
        checkout_session = retrieve_checkout_session(request.session_id)

        if not checkout_session:
            raise HTTPException(status_code=404, detail="Checkout session not found")

        # Verify payment was successful
        if checkout_session["payment_status"] != "paid":
            raise HTTPException(
                status_code=400,
                detail=f"Payment not completed. Status: {checkout_session['payment_status']}"
            )

        # Get tier from metadata
        tier = checkout_session["metadata"].get("tier")
        metadata_user_id = checkout_session["metadata"].get("user_id")

        # Verify the session belongs to this user
        if metadata_user_id != user["user_id"]:
            raise HTTPException(status_code=403, detail="Session does not belong to this user")

        # Get or create subscription
        subscription = await db_storage.get_subscription(user["user_id"], session)
        if subscription is None:
            subscription = await db_storage.create_subscription(user["user_id"], tier=tier, session=session)
        else:
            # Update existing subscription
            update_data = {
                "tier": tier,
                "status": "active"
            }
            if checkout_session.get("customer"):
                update_data["stripe_customer_id"] = checkout_session["customer"]
            if checkout_session.get("subscription"):
                update_data["stripe_subscription_id"] = checkout_session["subscription"]

            await db_storage.update_subscription(user["user_id"], update_data, session)

        # Auto-restore expired reports for paid users
        await db_storage.restore_all_expired_reports(user["user_id"], session)

        # Reload subscription to get updated data
        subscription = await db_storage.get_subscription(user["user_id"], session)

        return {
            "success": True,
            "subscription": subscription,
            "message": "Subscription verified and activated successfully"
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/api/webhooks/stripe")
async def stripe_webhook(request: Request):
    """
    Handle Stripe webhook events for payment processing.

    This endpoint:
    1. Verifies the webhook signature
    2. Processes payment events (checkout.session.completed, etc.)
    3. Updates user subscription status
    4. Restores expired reports for paid users (Feature 5)
    """
    # Get raw body and signature
    payload = await request.body()
    signature = request.headers.get("stripe-signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing stripe-signature header")

    # Verify webhook signature
    event = verify_webhook_signature(payload, signature)
    if event is None:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    # Create database session for webhook processing
    session = DatabaseManager.get_session()
    try:
        # Handle different event types
        event_type = event["type"]

        if event_type == "checkout.session.completed":
            # Payment successful
            checkout_session = event["data"]["object"]
            user_id = checkout_session["metadata"]["user_id"]
            tier = checkout_session["metadata"]["tier"]
            stripe_customer_id = checkout_session.get("customer")  # Capture customer ID for portal access

            # Get or create subscription
            subscription = await db_storage.get_subscription(user_id, session)
            if subscription is None:
                # Create new subscription
                subscription = await db_storage.create_subscription(user_id, tier=tier, session=session)
                # Now update with Stripe IDs (can't pass to create_subscription due to schema)
                update_data = {}
                if stripe_customer_id:
                    update_data["stripe_customer_id"] = stripe_customer_id
                if tier in ["monthly", "yearly"]:
                    update_data["stripe_subscription_id"] = checkout_session.get("subscription")
                if update_data:
                    await db_storage.update_subscription(user_id, update_data, session)
            else:
                # Update existing subscription
                update_data = {
                    "tier": tier,
                    "status": "active"
                }

                # Store Stripe customer ID for Customer Portal access
                if stripe_customer_id:
                    update_data["stripe_customer_id"] = stripe_customer_id

                # For recurring subscriptions, store Stripe subscription ID
                if tier in ["monthly", "yearly"]:
                    update_data["stripe_subscription_id"] = checkout_session.get("subscription")
                    # current_period_end will be set by subscription.created webhook

                await db_storage.update_subscription(user_id, update_data, session)

            # Feature 5: Auto-restore all expired reports when user subscribes
            await db_storage.restore_all_expired_reports(user_id, session)

        elif event_type == "customer.subscription.created":
            # Subscription created (for recurring plans)
            subscription_obj = event["data"]["object"]
            stripe_sub_id = subscription_obj["id"]
            current_period_end = subscription_obj["current_period_end"]

            # Convert timestamp to ISO format
            from datetime import datetime
            period_end_iso = datetime.fromtimestamp(current_period_end).isoformat()

            # Update subscription by Stripe ID
            await db_storage.update_subscription_by_stripe_id(
                stripe_sub_id,
                {"current_period_end": period_end_iso},
                session
            )

        elif event_type == "customer.subscription.updated":
            # Subscription updated (renewal, plan change, etc.)
            subscription_obj = event["data"]["object"]
            stripe_sub_id = subscription_obj["id"]
            status = subscription_obj["status"]
            current_period_end = subscription_obj["current_period_end"]

            # Convert timestamp to ISO format
            from datetime import datetime
            period_end_iso = datetime.fromtimestamp(current_period_end).isoformat()

            # Update subscription
            await db_storage.update_subscription_by_stripe_id(
                stripe_sub_id,
                {
                    "status": status,
                    "current_period_end": period_end_iso
                },
                session
            )

        elif event_type == "customer.subscription.deleted":
            # Subscription cancelled/expired
            subscription_obj = event["data"]["object"]
            stripe_sub_id = subscription_obj["id"]

            # Update subscription status
            await db_storage.update_subscription_by_stripe_id(
                stripe_sub_id,
                {"status": "cancelled"},
                session
            )

        await session.commit()
        return {"received": True}
    except Exception as e:
        await session.rollback()
        logger.error("webhook_processing_error", error=str(e))
        raise
    finally:
        await session.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
