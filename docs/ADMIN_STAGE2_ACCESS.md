# Admin Access to Stage 2 Analytics

## Quick Start

To list all available conversations in the terminal:
```bash
python scripts/view_stage2.py --list
```

To analyze a specific conversation, use the conversation ID:
```bash
python scripts/view_stage2.py 0d609c3e-5a8d-4b60-ab3c-aab7a6fe0a43
```

This will display Stage 2 analytics in the terminal.

## Overview

Stage 2 (peer review and rankings) has been hidden from end users but continues to run in the background for analytics and research purposes. This document explains how to access Stage 2 data as an administrator.

## Setup

1. **Set your admin API key** in `.env`:
   ```bash
   ADMIN_API_KEY=your_secret_admin_key_here
   ```

   ⚠️ **Important**: Use a strong, unique key in production. This key grants access to all Stage 2 analytics data.

2. **Restart the backend** after setting the environment variable:
   ```bash
   uv run python -m backend.main
   ```

## Accessing Stage 2 Data

### Using cURL

```bash
curl -H "X-Admin-Key: your_secret_admin_key_here" \
     http://localhost:8001/api/admin/conversations/{conversation_id}/stage2
```

Replace `{conversation_id}` with the actual conversation ID.

### Using Python

**Recommended: Use the provided script**
```bash
python scripts/view_stage2.py <conversation_id>
```

**Or manually:**
```python
import requests

ADMIN_KEY = "your_secret_admin_key_here"
CONVERSATION_ID = "your-conversation-id"

response = requests.get(
    f"http://localhost:8001/api/admin/conversations/{CONVERSATION_ID}/stage2",
    headers={"X-Admin-Key": ADMIN_KEY}
)

data = response.json()
print(json.dumps(data, indent=2))
```

### Using JavaScript/Fetch

```javascript
const ADMIN_KEY = 'your_secret_admin_key_here';
const CONVERSATION_ID = 'your-conversation-id';

fetch(`http://localhost:8001/api/admin/conversations/${CONVERSATION_ID}/stage2`, {
  headers: {
    'X-Admin-Key': ADMIN_KEY
  }
})
  .then(res => res.json())
  .then(data => console.log(data));
```

## Response Format

The endpoint returns comprehensive Stage 2 analytics:

```json
{
  "conversation_id": "abc-123",
  "title": "Conversation title",
  "created_at": "2025-01-15T10:00:00Z",
  "total_interactions": 2,
  "stage2_data": [
    {
      "message_index": 1,
      "user_question": "How can I manage stress better?",
      "stage2": [
        {
          "model": "meta-llama/llama-3.1-70b-instruct:therapist",
          "ranking": "Full raw ranking text with evaluations...",
          "parsed_ranking": ["Response C", "Response A", "Response B", ...]
        },
        // ... 4 more model rankings
      ],
      "metadata": {
        "label_to_model": {
          "Response A": "meta-llama/llama-3.1-70b-instruct:therapist",
          "Response B": "meta-llama/llama-3.1-70b-instruct:psychiatrist",
          "Response C": "meta-llama/llama-3.1-70b-instruct:psychologist",
          // ...
        },
        "aggregate_rankings": [
          {
            "model": "meta-llama/llama-3.1-70b-instruct:psychologist",
            "average_rank": 1.8,
            "rankings_count": 5
          },
          // ... sorted by average rank
        ],
        "is_crisis": false
      }
    }
    // ... more interactions
  ],
  "note": "This data is for analytics and research purposes. Stage 2 is hidden from end users."
}
```

## What Stage 2 Contains

### 1. **Raw Rankings** (`stage2` array)
- Each council member's evaluation of all responses
- Anonymous labels (Response A, B, C, etc.)
- Ranking rationale and reasoning
- Parsed ranking order

### 2. **De-anonymization Map** (`label_to_model`)
- Maps anonymous labels to actual model identifiers
- Example: `"Response A"` → `"meta-llama/llama-3.1-70b-instruct:therapist"`

### 3. **Aggregate Rankings** (`aggregate_rankings`)
- Combined "street cred" scores across all peer reviews
- Average rank position (lower is better)
- Number of votes each response received
- Sorted from best to worst

### 4. **Metadata**
- Crisis detection flag
- User question for context
- Message index in conversation

## Use Cases

### Research & Development
- Analyze which models perform best across different topics
- Identify bias patterns in peer review
- Measure inter-model agreement
- Track model performance over time

### Model Fine-Tuning
- Use rankings as training data for model improvement
- Identify areas where specific models excel or struggle
- Create datasets for preference learning

### Quality Assurance
- Verify that peer review system is working correctly
- Detect anomalies in model behavior
- Monitor consistency of rankings

### Analytics Dashboard (Future)
- Aggregate statistics across all conversations
- Visualize model performance trends
- Generate reports on council effectiveness

## Security Notes

1. **Never expose the admin endpoint publicly** without additional authentication
2. **Rotate the ADMIN_API_KEY** regularly
3. **Use HTTPS** in production to protect the API key in transit
4. **Log all admin access** for audit purposes
5. **Consider IP whitelisting** for admin endpoints in production

## Production Deployment

When deploying to production:

1. Set `ADMIN_API_KEY` in Railway/Fly.io environment variables
2. Consider adding IP whitelisting:
   ```python
   # backend/main.py
   from fastapi import Request

   ALLOWED_ADMIN_IPS = ["your.ip.address.here"]

   @app.get("/api/admin/conversations/{conversation_id}/stage2")
   async def get_stage2_analytics(
       conversation_id: str,
       request: Request,
       x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")
   ):
       # Check IP whitelist
       client_ip = request.client.host
       if client_ip not in ALLOWED_ADMIN_IPS:
           raise HTTPException(status_code=403, detail="IP not authorized")

       # ... rest of function
   ```

3. Consider adding rate limiting for admin endpoints

## Finding Conversation IDs

### Method 1: From the UI
Look at the browser URL when viewing a conversation:
```
http://localhost:5173/?conversation=abc-123-def-456
```
The conversation ID is `abc-123-def-456`

### Method 2: Via API
List all conversations:
```bash
curl http://localhost:8001/api/conversations
```

### Method 3: From Storage
Check the `data/conversations/` directory - each JSON file is named with the conversation ID.

## Troubleshooting

### Error: "Admin access required"
- Check that `X-Admin-Key` header matches `ADMIN_API_KEY` in `.env`
- Verify the header name is exactly `X-Admin-Key` (case-sensitive)

### Error: "Conversation not found"
- Verify the conversation ID is correct
- Check that the conversation exists in `data/conversations/`

### No Stage 2 data returned
- Verify that messages have been sent in this conversation
- Stage 2 data is only present in assistant messages
- Check that the backend processed Stage 2 (it runs automatically)

## Example: Analyzing Model Performance

```python
import requests
import json
from collections import defaultdict

ADMIN_KEY = "your_admin_key"
BASE_URL = "http://localhost:8001"

# Get all conversations
conversations = requests.get(f"{BASE_URL}/api/conversations").json()

# Analyze Stage 2 data across all conversations
model_scores = defaultdict(list)

for conv in conversations:
    response = requests.get(
        f"{BASE_URL}/api/admin/conversations/{conv['id']}/stage2",
        headers={"X-Admin-Key": ADMIN_KEY}
    )

    if response.status_code == 200:
        data = response.json()

        for interaction in data.get('stage2_data', []):
            for ranking in interaction['metadata']['aggregate_rankings']:
                model = ranking['model']
                avg_rank = ranking['average_rank']
                model_scores[model].append(avg_rank)

# Calculate overall performance
for model, scores in model_scores.items():
    avg_score = sum(scores) / len(scores)
    print(f"{model}: {avg_score:.2f} (lower is better)")
```

## Questions?

For issues or questions about Stage 2 analytics access, check:
1. Backend logs for any errors
2. Network requests in browser DevTools
3. Environment variables are set correctly

---

**Last Updated:** 2025-01-15
**Feature Status:** ✅ Implemented (Feature 6)
