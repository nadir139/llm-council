# Utility Scripts

This directory contains utility scripts for development, testing, and administration.

## Scripts

### `view_stage2.py`
View Stage 2 analytics data for conversations (requires admin key).

**Usage:**
```bash
# List all conversations
python scripts/view_stage2.py --list

# View Stage 2 data for a specific conversation
python scripts/view_stage2.py <conversation_id>
```

**Example:**
```bash
python scripts/view_stage2.py 0d609c3e-5a8d-4b60-ab3c-aab7a6fe0a43
```

### `test_admin_endpoint.py`
Test script for validating the admin Stage 2 endpoint.

**Usage:**
```bash
python scripts/test_admin_endpoint.py
```

## Configuration

These scripts use the `ADMIN_API_KEY` from your `.env` file. Make sure it's set correctly:
```bash
ADMIN_API_KEY=your_secret_key_here
```

## Documentation

For more details on Stage 2 analytics, see [docs/ADMIN_STAGE2_ACCESS.md](../docs/ADMIN_STAGE2_ACCESS.md).
