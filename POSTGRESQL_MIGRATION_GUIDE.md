# PostgreSQL Migration Guide

**Status**: 🟡 **Preparation Complete - Integration Pending**

All PostgreSQL infrastructure is ready. Main.py integration is the final step (estimated 2-3 hours).

---

## ✅ Completed Steps

### 1. Database Models (✅ Complete)
- **File**: `backend/database.py` (289 lines)
- **Models**: User, Subscription, Conversation, Message
- **Features**:
  - Async SQLAlchemy with asyncpg
  - Proper foreign keys and relationships
  - Indexes for common queries
  - Connection pooling (pool_size=5, max_overflow=10)
  - DatabaseManager singleton pattern

### 2. Database Storage Layer (✅ Complete)
- **File**: `backend/db_storage.py` (369 lines)
- **Functions**: All CRUD operations implemented
  - User: create_user_profile, get_user_profile, update_user_profile
  - Subscription: create_subscription, get_subscription, update_subscription
  - Conversation: create/get/list/update/delete/toggle_star
  - Message: add_message
  - Utility: count_user_conversations, get_active_conversations_count
- **API Compatibility**: Maintains same interface as storage.py

### 3. Migration Script (✅ Complete)
- **File**: `backend/migrate_json_to_db.py`
- **Features**:
  - Migrates profiles, subscriptions, conversations, messages
  - Handles existing records gracefully (skip duplicates)
  - Preserves timestamps and metadata
  - Provides detailed progress output

### 4. Dependencies (✅ Installed)
```bash
✅ asyncpg==0.31.0        # PostgreSQL async driver
✅ sqlalchemy==2.0.44     # ORM
✅ psycopg2-binary==2.9.11  # PostgreSQL adapter
```

### 5. Configuration (✅ Complete)
- **File**: `.env.example` created with DATABASE_URL documentation
- **Validation**: DatabaseManager checks for DATABASE_URL on init

---

## 🟡 Remaining Work: main.py Integration

### Overview
Replace ~50 synchronous `storage.*` calls with async `db_storage.*` calls.

**Challenge**: storage.py functions are sync, db_storage.py functions are async + require sessions.

### Required Changes

#### A. App Startup - Initialize Database
```python
# backend/main.py - Add to startup

from .database import DatabaseManager, get_db_session

@app.on_event("startup")
async def startup():
    """Initialize database connection on app startup."""
    logger.info("initializing_database")
    DatabaseManager.initialize()
    await DatabaseManager.create_tables()
    logger.info("database_ready")

@app.on_event("shutdown")
async def shutdown():
    """Close database connections on shutdown."""
    logger.info("closing_database")
    await DatabaseManager.close()
```

#### B. Replace Import Statement
```python
# OLD
from . import storage

# NEW
from . import db_storage
from .database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession
```

#### C. Add Session Dependency to All Endpoints
All database-touching endpoints need:
```python
async def endpoint_name(
    ...,
    session: AsyncSession = Depends(get_db_session)
):
```

#### D. Replace Function Calls

**Pattern**: `storage.function()` → `await db_storage.function(..., session)`

**Examples**:
```python
# OLD (sync)
conversation = storage.get_conversation(conversation_id)

# NEW (async with session)
conversation = await db_storage.get_conversation(conversation_id, session)

# OLD (sync)
storage.add_user_message(conversation_id, content)

# NEW (async with session)
await db_storage.add_message(
    conversation_id,
    {"role": "user", "content": content},
    session
)
```

### Detailed Function Mapping

| Old (storage.py) | New (db_storage.py) | Session Required |
|------------------|---------------------|------------------|
| `list_conversations(user_id)` | `list_conversations(user_id, session)` | ✅ |
| `create_conversation(user_id, tier)` | `create_conversation(user_id, session)` | ✅ |
| `get_conversation(id)` | `get_conversation(id, session)` | ✅ |
| `update_conversation_title(id, title)` | `update_conversation_title(id, title, session)` | ✅ |
| `toggle_conversation_starred(id)` | `toggle_conversation_star(id, session)` | ✅ |
| `delete_conversation(id)` | `delete_conversation(id, session)` | ✅ |
| `add_user_message(id, content)` | `add_message(id, {role, content}, session)` | ✅ |
| `add_assistant_message(id, stage1, stage2, stage3, metadata)` | `add_message(id, {role, stage1, stage2, stage3, metadata}, session)` | ✅ |
| `save_follow_up_answers(id, answers)` | `update_conversation_follow_up(id, answers, session)` | ✅ |
| `get_user_profile(user_id)` | `get_user_profile(user_id, session)` | ✅ |
| `create_user_profile(user_id, data)` | `create_user_profile(user_id, data, session)` | ✅ |
| `update_user_profile(user_id, data)` | `update_user_profile(user_id, data, session)` | ✅ |
| `get_subscription(user_id)` | `get_subscription(user_id, session)` | ✅ |
| `create_subscription(user_id, tier)` | `create_subscription(user_id, tier, session)` | ✅ |
| `update_subscription(user_id, data)` | `update_subscription(user_id, data, session)` | ✅ |
| `update_subscription_by_stripe_id(stripe_id, data)` | `update_subscription_by_stripe_id(stripe_id, data, session)` | ✅ |
| `restore_all_expired_reports(user_id)` | `restore_all_expired_reports(user_id, session)` | ✅ |

### Endpoints Requiring Updates (38 total)

#### Conversation Endpoints (9)
- ✅ `GET /api/conversations` - list_conversations
- ✅ `POST /api/conversations` - create_conversation
- ✅ `GET /api/conversations/{id}` - get_conversation
- ✅ `POST /api/conversations/{id}/message` - get_conversation, add_message, update_title, get_user_profile, add_message
- ✅ `POST /api/conversations/{id}/message/stream` - Similar to above
- ✅ `POST /api/conversations/{id}/follow-up` - get_conversation, save_follow_up_answers
- ✅ `POST /api/conversations/{id}/star` - toggle_conversation_starred
- ✅ `PATCH /api/conversations/{id}/title` - update_conversation_title
- ✅ `DELETE /api/conversations/{id}` - delete_conversation

#### User Profile Endpoints (3)
- ✅ `POST /api/users/profile` - create_user_profile
- ✅ `GET /api/users/profile` - get_user_profile
- ✅ `PATCH /api/users/profile` - update_user_profile

#### Subscription Endpoints (4)
- ✅ `GET /api/subscription` - get_subscription
- ✅ `POST /api/subscription/checkout` - get_subscription
- ✅ `POST /api/subscription/cancel` - get_subscription, update_subscription
- ✅ `POST /api/webhooks/stripe` - update_subscription_by_stripe_id, restore_all_expired_reports

---

## 📋 Migration Checklist

### Pre-Migration
- [ ] **Backup JSON data** (`cp -r data/ data_backup/`)
- [ ] **Set DATABASE_URL** in `.env`
- [ ] **Create PostgreSQL database**
  ```bash
  createdb llmcouncil
  # OR in psql:
  # CREATE DATABASE llmcouncil;
  ```
- [ ] **Test database connection**
  ```bash
  python backend/test_connection.py
  ```

### Migration
- [ ] **Run migration script**
  ```bash
  python -m backend.migrate_json_to_db
  ```
- [ ] **Verify data in PostgreSQL**
  ```sql
  SELECT COUNT(*) FROM users;
  SELECT COUNT(*) FROM subscriptions;
  SELECT COUNT(*) FROM conversations;
  SELECT COUNT(*) FROM messages;
  ```

### Code Integration
- [ ] **Update main.py**
  - [ ] Add startup/shutdown handlers
  - [ ] Replace `storage` import with `db_storage`
  - [ ] Add `session` dependency to all endpoints
  - [ ] Replace all `storage.*` calls with `await db_storage.*`
  - [ ] Update `add_user_message` to `add_message` with dict format
  - [ ] Update `add_assistant_message` to `add_message` with dict format

### Testing
- [ ] **Test basic endpoints**
  - [ ] `GET /` (health check)
  - [ ] `POST /api/users/profile` (create profile)
  - [ ] `GET /api/users/profile` (get profile)
  - [ ] `POST /api/conversations` (create conversation)
  - [ ] `GET /api/conversations` (list conversations)
  - [ ] `POST /api/conversations/{id}/message` (send message)
- [ ] **Test subscription flows**
  - [ ] Create checkout session
  - [ ] Webhook handlers
  - [ ] Subscription updates
- [ ] **Test edge cases**
  - [ ] Non-existent conversation
  - [ ] Unauthorized access (wrong user_id)
  - [ ] Expired conversations
  - [ ] Follow-up answers

### Cleanup
- [ ] **Backup JSON files** (if tests pass)
  ```bash
  tar -czf data_backup_$(date +%Y%m%d).tar.gz data/
  ```
- [ ] **Delete JSON storage code**
  ```bash
  rm backend/storage.py
  rm backend/profile.py
  ```
- [ ] **Update documentation**
  - [ ] Update CLAUDE.md to reflect database usage
  - [ ] Update README.md with database setup instructions

---

## 🚀 Quick Start (After Integration)

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your values

# 2. Create database
createdb llmcouncil

# 3. Run migration (if you have existing JSON data)
python -m backend.migrate_json_to_db

# 4. Start backend
./start.sh
# OR
python -m backend.main
```

---

## 🐛 Troubleshooting

### "Database not initialized"
**Solution**: Add startup handler to main.py

### "asyncpg.exceptions.UndefinedTableError"
**Solution**: Run `DatabaseManager.create_tables()` in startup handler

### "Multiple sessions in one request"
**Solution**: Use single session per request via `Depends(get_db_session)`

### "SSL connection required"
**Solution**: Add `?sslmode=require` to DATABASE_URL for production

### "Connection pool exhausted"
**Solution**: Increase `pool_size` and `max_overflow` in database.py

---

## 📊 Performance Benefits

### Before (JSON Files)
- **Concurrent writes**: ❌ Data loss risk
- **Pagination**: ❌ Loads all into memory
- **Transactions**: ❌ No ACID guarantees
- **Scalability**: ~100 users max

### After (PostgreSQL)
- **Concurrent writes**: ✅ ACID transactions
- **Pagination**: ✅ Database-level pagination
- **Transactions**: ✅ Rollback on errors
- **Scalability**: 10,000+ users

---

## 🎯 Estimated Effort

| Task | Time | Complexity |
|------|------|------------|
| Update main.py imports and startup | 15 min | Easy |
| Add session dependencies to endpoints | 30 min | Medium |
| Replace storage calls (38 endpoints) | 90 min | Medium |
| Test all endpoints | 30 min | Easy |
| Fix bugs and edge cases | 30 min | Medium |
| **Total** | **~3 hours** | **Medium** |

---

## 📝 Notes

- **Transaction Safety**: `get_db_session()` automatically commits on success, rolls back on errors
- **Connection Pooling**: Handled by SQLAlchemy, no manual management needed
- **Async Context**: All db_storage functions are `async`, must be `await`ed
- **Session Lifecycle**: One session per request, automatically closed
- **Error Handling**: SQLAlchemy exceptions automatically rollback

---

## ✅ Next Immediate Step

**Run the integration:**
1. Open `backend/main.py`
2. Add startup/shutdown handlers (5 lines)
3. Replace storage import with db_storage (1 line)
4. Add session dependency to first endpoint
5. Test that endpoint
6. Repeat for remaining 37 endpoints

**Or**: Create a separate branch for testing:
```bash
git checkout -b feature/postgres-migration
# Make changes, test thoroughly
# Merge when confident
```

---

**Last Updated**: 2025-12-04
**Status**: Ready for integration
**Blocking Issue**: main.py needs refactoring to async database calls
