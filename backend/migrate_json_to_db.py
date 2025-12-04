"""
Migration script: JSON files → PostgreSQL database

This script migrates data from the JSON file-based storage to PostgreSQL.
Run this ONCE during migration, then switch to database storage.

Usage:
    python -m backend.migrate_json_to_db

Prerequisites:
    - DATABASE_URL set in .env
    - Existing JSON files in data/ directories
    - PostgreSQL database created
"""

import asyncio
import json
import os
from pathlib import Path
from datetime import datetime

from backend.database import DatabaseManager, User, Subscription, Conversation, Message
from backend.db_storage import (
    create_user_profile,
    create_subscription,
    get_user_profile,
    get_subscription
)


async def migrate_profiles():
    """Migrate user profiles from JSON to database."""
    profiles_dir = Path("data/profiles")
    if not profiles_dir.exists():
        print("No profiles directory found. Skipping profile migration.")
        return 0

    migrated = 0
    session = DatabaseManager.get_session()

    try:
        for profile_file in profiles_dir.glob("*.json"):
            with open(profile_file, 'r') as f:
                profile_data = json.load(f)

            user_id = profile_data.get("user_id")

            # Check if user already exists
            existing = await get_user_profile(user_id, session)
            if existing:
                print(f"  ⚠️  User {user_id} already exists. Skipping.")
                continue

            # Create user
            await create_user_profile(
                user_id=user_id,
                profile_data={
                    "email": profile_data.get("email"),
                    "gender": profile_data["profile"].get("gender"),
                    "age_range": profile_data["profile"].get("age_range"),
                    "mood": profile_data["profile"].get("mood")
                },
                session=session
            )

            # Lock profile if it was locked in JSON
            if profile_data.get("profile_locked"):
                user = await session.get(User, user_id)
                user.profile_locked = True

            migrated += 1
            print(f"  ✓ Migrated profile: {user_id}")

        await session.commit()
        print(f"\n✓ Migrated {migrated} user profiles")
        return migrated

    except Exception as e:
        await session.rollback()
        print(f"\n✗ Error migrating profiles: {e}")
        raise
    finally:
        await session.close()


async def migrate_subscriptions():
    """Migrate subscriptions from JSON to database."""
    subscriptions_dir = Path("data/subscriptions")
    if not subscriptions_dir.exists():
        print("No subscriptions directory found. Skipping subscription migration.")
        return 0

    migrated = 0
    session = DatabaseManager.get_session()

    try:
        for sub_file in subscriptions_dir.glob("*.json"):
            with open(sub_file, 'r') as f:
                sub_data = json.load(f)

            user_id = sub_data.get("user_id")

            # Check if subscription already exists
            existing = await get_subscription(user_id, session)
            if existing:
                print(f"  ⚠️  Subscription for {user_id} already exists. Skipping.")
                continue

            # Create subscription
            subscription = Subscription(
                user_id=user_id,
                tier=sub_data.get("tier", "free"),
                status=sub_data.get("status", "active"),
                stripe_customer_id=sub_data.get("stripe_customer_id"),
                stripe_subscription_id=sub_data.get("stripe_subscription_id"),
                current_period_end=datetime.fromisoformat(sub_data["current_period_end"]) if sub_data.get("current_period_end") else None,
                created_at=datetime.fromisoformat(sub_data["created_at"]) if sub_data.get("created_at") else datetime.utcnow(),
                updated_at=datetime.fromisoformat(sub_data["updated_at"]) if sub_data.get("updated_at") else datetime.utcnow()
            )

            session.add(subscription)
            migrated += 1
            print(f"  ✓ Migrated subscription: {user_id} ({sub_data.get('tier')})")

        await session.commit()
        print(f"\n✓ Migrated {migrated} subscriptions")
        return migrated

    except Exception as e:
        await session.rollback()
        print(f"\n✗ Error migrating subscriptions: {e}")
        raise
    finally:
        await session.close()


async def migrate_conversations():
    """Migrate conversations and messages from JSON to database."""
    conversations_dir = Path("data/conversations")
    if not conversations_dir.exists():
        print("No conversations directory found. Skipping conversation migration.")
        return 0, 0

    migrated_conversations = 0
    migrated_messages = 0
    session = DatabaseManager.get_session()

    try:
        for conv_file in conversations_dir.glob("*.json"):
            with open(conv_file, 'r') as f:
                conv_data = json.load(f)

            conversation_id = conv_data.get("id")

            # Check if conversation already exists
            existing = await session.get(Conversation, conversation_id)
            if existing:
                print(f"  ⚠️  Conversation {conversation_id} already exists. Skipping.")
                continue

            # Create conversation
            conversation = Conversation(
                id=conversation_id,
                user_id=conv_data.get("user_id"),
                title=conv_data.get("title"),
                starred=conv_data.get("starred", False),
                expires_at=datetime.fromisoformat(conv_data["expires_at"]) if conv_data.get("expires_at") else None,
                report_cycle=conv_data.get("report_cycle", 1),
                has_follow_up=conv_data.get("has_follow_up", False),
                follow_up_answers=conv_data.get("follow_up_answers"),
                created_at=datetime.fromisoformat(conv_data["created_at"]) if conv_data.get("created_at") else datetime.utcnow()
            )

            session.add(conversation)
            migrated_conversations += 1

            # Migrate messages
            for msg in conv_data.get("messages", []):
                message = Message(
                    id=msg.get("id", str(os.urandom(16).hex())),
                    conversation_id=conversation_id,
                    role=msg.get("role"),
                    content=msg.get("content"),
                    stage1=msg.get("stage1"),
                    stage2=msg.get("stage2"),
                    stage3=msg.get("stage3"),
                    metadata_=msg.get("metadata"),
                    created_at=datetime.fromisoformat(msg["created_at"]) if msg.get("created_at") else datetime.utcnow()
                )
                session.add(message)
                migrated_messages += 1

            print(f"  ✓ Migrated conversation: {conversation_id} ({len(conv_data.get('messages', []))} messages)")

        await session.commit()
        print(f"\n✓ Migrated {migrated_conversations} conversations with {migrated_messages} messages")
        return migrated_conversations, migrated_messages

    except Exception as e:
        await session.rollback()
        print(f"\n✗ Error migrating conversations: {e}")
        raise
    finally:
        await session.close()


async def main():
    """Main migration function."""
    print("=" * 60)
    print("LLM Council: JSON → PostgreSQL Migration")
    print("=" * 60)

    # Initialize database
    print("\n1. Initializing database connection...")
    try:
        DatabaseManager.initialize()
        print("✓ Database connected")
    except Exception as e:
        print(f"✗ Failed to connect to database: {e}")
        print("\nMake sure:")
        print("  - DATABASE_URL is set in .env")
        print("  - PostgreSQL is running")
        print("  - Database exists")
        return

    # Create tables
    print("\n2. Creating database tables...")
    try:
        await DatabaseManager.create_tables()
        print("✓ Tables created (or already exist)")
    except Exception as e:
        print(f"✗ Failed to create tables: {e}")
        return

    # Migrate data
    print("\n3. Migrating user profiles...")
    profiles_count = await migrate_profiles()

    print("\n4. Migrating subscriptions...")
    subscriptions_count = await migrate_subscriptions()

    print("\n5. Migrating conversations and messages...")
    conversations_count, messages_count = await migrate_conversations()

    # Summary
    print("\n" + "=" * 60)
    print("Migration Summary:")
    print("=" * 60)
    print(f"  User Profiles:    {profiles_count}")
    print(f"  Subscriptions:    {subscriptions_count}")
    print(f"  Conversations:    {conversations_count}")
    print(f"  Messages:         {messages_count}")
    print("=" * 60)
    print("\n✓ Migration complete!")
    print("\nNext steps:")
    print("  1. Verify data in PostgreSQL")
    print("  2. Update backend/main.py to use db_storage instead of storage")
    print("  3. Test all endpoints")
    print("  4. Backup and delete JSON files (data/ directory)")
    print("  5. Delete backend/storage.py and backend/profile.py")


if __name__ == "__main__":
    asyncio.run(main())
