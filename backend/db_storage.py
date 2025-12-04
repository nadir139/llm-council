"""
PostgreSQL-based storage implementation for LLM Council.

This replaces the JSON file-based storage with a scalable database solution.
Maintains API compatibility with the existing storage.py interface.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import select, update, delete, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import uuid

from .database import User, Subscription, Conversation, Message, DatabaseManager


# =====================
# USER OPERATIONS
# =====================

async def create_user_profile(user_id: str, profile_data: Dict[str, Any], session: AsyncSession) -> Dict[str, Any]:
    """
    Create a new user profile with onboarding data.

    Args:
        user_id: Clerk user ID
        profile_data: Dict with gender, age_range, mood
        session: Database session

    Returns:
        User profile dict
    """
    user = User(
        user_id=user_id,
        email=profile_data.get("email"),
        gender=profile_data.get("gender"),
        age_range=profile_data.get("age_range"),
        mood=profile_data.get("mood"),
        profile_locked=False
    )

    session.add(user)
    await session.flush()

    # Also create default free subscription
    subscription = Subscription(
        user_id=user_id,
        tier="free",
        status="active"
    )
    session.add(subscription)
    await session.flush()

    return user.to_dict()


async def get_user_profile(user_id: str, session: AsyncSession) -> Optional[Dict[str, Any]]:
    """Get user profile by user_id."""
    result = await session.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    return user.to_dict() if user else None


async def update_user_profile(user_id: str, profile_data: Dict[str, Any], session: AsyncSession) -> Dict[str, Any]:
    """
    Update user profile (only if not locked).

    Args:
        user_id: Clerk user ID
        profile_data: Dict with fields to update
        session: Database session

    Returns:
        Updated user profile dict
    """
    result = await session.execute(
        select(User).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise ValueError(f"User {user_id} not found")

    if user.profile_locked:
        raise ValueError("Profile is locked and cannot be updated")

    # Update fields
    if "email" in profile_data:
        user.email = profile_data["email"]
    if "gender" in profile_data:
        user.gender = profile_data["gender"]
    if "age_range" in profile_data:
        user.age_range = profile_data["age_range"]
    if "mood" in profile_data:
        user.mood = profile_data["mood"]

    user.updated_at = datetime.utcnow()
    await session.flush()

    return user.to_dict()


# =====================
# SUBSCRIPTION OPERATIONS
# =====================

async def create_subscription(user_id: str, tier: str, session: AsyncSession) -> Dict[str, Any]:
    """Create a new subscription for a user."""
    subscription = Subscription(
        user_id=user_id,
        tier=tier,
        status="active"
    )

    session.add(subscription)
    await session.flush()

    return subscription.to_dict()


async def get_subscription(user_id: str, session: AsyncSession) -> Optional[Dict[str, Any]]:
    """Get user's subscription."""
    result = await session.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()
    return subscription.to_dict() if subscription else None


async def update_subscription(user_id: str, update_data: Dict[str, Any], session: AsyncSession) -> Dict[str, Any]:
    """Update user's subscription."""
    result = await session.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        raise ValueError(f"Subscription for user {user_id} not found")

    # Update fields
    for key, value in update_data.items():
        if hasattr(subscription, key):
            setattr(subscription, key, value)

    subscription.updated_at = datetime.utcnow()
    await session.flush()

    return subscription.to_dict()


async def update_subscription_by_stripe_id(stripe_sub_id: str, update_data: Dict[str, Any], session: AsyncSession) -> Optional[Dict[str, Any]]:
    """Update subscription by Stripe subscription ID."""
    result = await session.execute(
        select(Subscription).where(Subscription.stripe_subscription_id == stripe_sub_id)
    )
    subscription = result.scalar_one_or_none()

    if not subscription:
        return None

    # Update fields
    for key, value in update_data.items():
        if hasattr(subscription, key):
            setattr(subscription, key, value)

    subscription.updated_at = datetime.utcnow()
    await session.flush()

    return subscription.to_dict()


# =====================
# CONVERSATION OPERATIONS
# =====================

async def create_conversation(user_id: str, session: AsyncSession) -> Dict[str, Any]:
    """Create a new conversation."""
    conversation = Conversation(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=None,
        starred=False,
        report_cycle=1,
        has_follow_up=False
    )

    # Check if user has free tier - set expiration
    subscription = await get_subscription(user_id, session)
    if subscription and subscription["tier"] == "free":
        # Free tier conversations expire in 7 days
        conversation.expires_at = datetime.utcnow() + timedelta(days=7)

    session.add(conversation)
    await session.flush()

    return conversation.to_dict()


async def get_conversation(conversation_id: str, session: AsyncSession) -> Optional[Dict[str, Any]]:
    """Get conversation by ID with all messages."""
    result = await session.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    return conversation.to_dict(include_messages=True) if conversation else None


async def list_conversations(user_id: str, session: AsyncSession) -> List[Dict[str, Any]]:
    """List all conversations for a user, ordered by created_at desc."""
    result = await session.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.created_at.desc())
    )
    conversations = result.scalars().all()
    return [conv.to_dict() for conv in conversations]


async def update_conversation_title(conversation_id: str, title: str, session: AsyncSession) -> Dict[str, Any]:
    """Update conversation title."""
    result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation.title = title
    conversation.updated_at = datetime.utcnow()
    await session.flush()

    return conversation.to_dict()


async def toggle_conversation_star(conversation_id: str, session: AsyncSession) -> Dict[str, Any]:
    """Toggle starred status of a conversation."""
    result = await session.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation.starred = not conversation.starred
    conversation.updated_at = datetime.utcnow()
    await session.flush()

    return conversation.to_dict()


async def delete_conversation(conversation_id: str, session: AsyncSession) -> None:
    """Delete a conversation and all its messages."""
    await session.execute(
        delete(Conversation).where(Conversation.id == conversation_id)
    )
    await session.flush()


async def update_conversation_follow_up(conversation_id: str, follow_up_answers: str, session: AsyncSession) -> Dict[str, Any]:
    """Update conversation with follow-up answers and increment report cycle."""
    result = await session.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()

    if not conversation:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation.follow_up_answers = follow_up_answers
    conversation.has_follow_up = True
    conversation.report_cycle = 2
    conversation.updated_at = datetime.utcnow()
    await session.flush()

    return conversation.to_dict(include_messages=True)


async def restore_all_expired_reports(user_id: str, session: AsyncSession) -> None:
    """
    Remove expiration from all conversations when user upgrades.
    Feature 5: Auto-restore expired reports on subscription.
    """
    await session.execute(
        update(Conversation)
        .where(and_(
            Conversation.user_id == user_id,
            Conversation.expires_at.isnot(None)
        ))
        .values(expires_at=None)
    )
    await session.flush()


# =====================
# MESSAGE OPERATIONS
# =====================

async def add_message(conversation_id: str, message_data: Dict[str, Any], session: AsyncSession) -> Dict[str, Any]:
    """
    Add a message to a conversation.

    Args:
        conversation_id: Conversation ID
        message_data: Dict with role, content (for user), stage1/2/3 (for assistant)
        session: Database session

    Returns:
        Message dict
    """
    message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role=message_data["role"],
        content=message_data.get("content"),
        stage1=message_data.get("stage1"),
        stage2=message_data.get("stage2"),
        stage3=message_data.get("stage3"),
        metadata=message_data.get("metadata")
    )

    session.add(message)

    # Update conversation's updated_at
    await session.execute(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(updated_at=datetime.utcnow())
    )

    await session.flush()

    return message.to_dict()


# =====================
# UTILITY FUNCTIONS
# =====================

async def count_user_conversations(user_id: str, session: AsyncSession) -> int:
    """Count total conversations for a user."""
    result = await session.execute(
        select(func.count(Conversation.id)).where(Conversation.user_id == user_id)
    )
    return result.scalar_one()


async def get_active_conversations_count(user_id: str, session: AsyncSession) -> int:
    """
    Count non-expired conversations for free tier limit checking.
    Feature 4: Enforce free tier conversation limit.
    """
    now = datetime.utcnow()
    result = await session.execute(
        select(func.count(Conversation.id)).where(
            and_(
                Conversation.user_id == user_id,
                or_(
                    Conversation.expires_at.is_(None),
                    Conversation.expires_at > now
                )
            )
        )
    )
    return result.scalar_one()
