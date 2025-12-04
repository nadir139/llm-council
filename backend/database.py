"""
Database models and connection management for LLM Council.

Uses SQLAlchemy with PostgreSQL for scalable, production-ready storage.
"""

from sqlalchemy import Column, String, DateTime, Boolean, Integer, JSON, Text, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import NullPool
from datetime import datetime
from typing import Optional
import os

Base = declarative_base()


class User(Base):
    """
    User profiles with onboarding data.
    Linked to Clerk user_id for authentication.
    """
    __tablename__ = "users"

    user_id = Column(String(255), primary_key=True, index=True)  # Clerk user ID
    email = Column(String(255), nullable=True, index=True)

    # Onboarding profile data
    gender = Column(String(50), nullable=True)
    age_range = Column(String(50), nullable=True)
    mood = Column(String(100), nullable=True)

    profile_locked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")
    subscription = relationship("Subscription", back_populates="user", uselist=False, cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "email": self.email,
            "profile": {
                "gender": self.gender,
                "age_range": self.age_range,
                "mood": self.mood
            },
            "profile_locked": self.profile_locked,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Subscription(Base):
    """
    User subscription and payment information.
    Linked to Stripe for payment processing.
    """
    __tablename__ = "subscriptions"

    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True, index=True)
    tier = Column(String(50), nullable=False, default="free")  # free, single_report, monthly, yearly
    status = Column(String(50), nullable=False, default="active")  # active, cancelled, expired

    # Stripe integration
    stripe_customer_id = Column(String(255), nullable=True, index=True)
    stripe_subscription_id = Column(String(255), nullable=True, index=True)

    # Billing information
    current_period_end = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="subscription")

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "tier": self.tier,
            "status": self.status,
            "stripe_customer_id": self.stripe_customer_id,
            "stripe_subscription_id": self.stripe_subscription_id,
            "current_period_end": self.current_period_end.isoformat() if self.current_period_end else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class Conversation(Base):
    """
    User conversations/sessions with the LLM Council.
    Contains all messages and metadata.
    """
    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, index=True)  # UUID
    user_id = Column(String(255), ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True)

    title = Column(String(500), nullable=True)
    starred = Column(Boolean, default=False, nullable=False)

    # Feature 5: Expiration for free tier
    expires_at = Column(DateTime, nullable=True, index=True)

    # Feature 3: Follow-up cycle tracking
    report_cycle = Column(Integer, default=1, nullable=False)  # 1 = first report, 2 = second report
    has_follow_up = Column(Boolean, default=False, nullable=False)
    follow_up_answers = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

    # Indexes for common queries
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_user_starred', 'user_id', 'starred'),
    )

    def to_dict(self, include_messages=False, message_count=None):
        """
        Convert conversation to dictionary.

        Args:
            include_messages: If True, include full message list (requires eager loading)
            message_count: Optional pre-computed message count to avoid lazy loading
        """
        from sqlalchemy.orm.attributes import instance_state
        from sqlalchemy.orm.base import NO_VALUE

        # Check if messages are loaded to avoid lazy loading in async context
        state = instance_state(self)
        messages_loaded = state.attrs.messages.loaded_value is not NO_VALUE

        data = {
            "id": self.id,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "title": self.title or "New Conversation",
            "starred": self.starred,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "report_cycle": self.report_cycle,
            "has_follow_up": self.has_follow_up,
            "follow_up_answers": self.follow_up_answers,
            "message_count": message_count if message_count is not None else (len(self.messages) if messages_loaded else 0)
        }

        if include_messages and messages_loaded:
            data["messages"] = [msg.to_dict() for msg in self.messages]

        return data


class Message(Base):
    """
    Individual messages within a conversation.
    Stores both user messages and LLM Council responses.
    """
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, index=True)  # UUID
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)

    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=True)  # For user messages

    # Council response data (for assistant messages)
    stage1 = Column(JSON, nullable=True)  # List of individual model responses
    stage2 = Column(JSON, nullable=True)  # List of peer rankings
    stage3 = Column(JSON, nullable=True)  # Final synthesis
    metadata_ = Column("metadata", JSON, nullable=True)  # DB column stays "metadata"

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

    # Index for efficient message retrieval
    __table_args__ = (
        Index('idx_conversation_created', 'conversation_id', 'created_at'),
    )

    def to_dict(self):
        data = {
            "role": self.role,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

        if self.role == "user":
            data["content"] = self.content
        else:  # assistant
            data["stage1"] = self.stage1
            data["stage2"] = self.stage2
            data["stage3"] = self.stage3
            if self.metadata:
                data["metadata"] = self.metadata

        return data


# Database connection management
class DatabaseManager:
    """
    Manages database connections and session creation.
    Singleton pattern for efficient connection pooling.
    """
    _engine = None
    _session_maker = None

    @classmethod
    def initialize(cls, database_url: Optional[str] = None):
        """Initialize database engine and session maker."""
        if cls._engine is not None:
            return  # Already initialized

        # Get database URL from environment or parameter
        db_url = database_url or os.getenv("DATABASE_URL")

        if not db_url:
            raise ValueError("DATABASE_URL environment variable not set")

        # Convert postgres:// to postgresql:// for SQLAlchemy
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        # Convert to async URL
        if not db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        # Create async engine
        cls._engine = create_async_engine(
            db_url,
            echo=False,  # Set to True for SQL query logging
            pool_pre_ping=True,  # Verify connections before using
            pool_size=5,  # Connection pool size
            max_overflow=10  # Max overflow connections
        )

        # Create session maker
        cls._session_maker = sessionmaker(
            cls._engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    @classmethod
    async def create_tables(cls):
        """Create all tables in the database."""
        if cls._engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with cls._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @classmethod
    async def drop_tables(cls):
        """Drop all tables in the database. USE WITH CAUTION!"""
        if cls._engine is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        async with cls._engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    @classmethod
    def get_session(cls) -> AsyncSession:
        """Get a new database session."""
        if cls._session_maker is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        return cls._session_maker()

    @classmethod
    async def close(cls):
        """Close database engine and connections."""
        if cls._engine is not None:
            await cls._engine.dispose()
            cls._engine = None
            cls._session_maker = None


# Convenience function for getting sessions
async def get_db_session() -> AsyncSession:
    """
    Dependency function for FastAPI endpoints.
    Usage: session: AsyncSession = Depends(get_db_session)
    """
    session = DatabaseManager.get_session()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
