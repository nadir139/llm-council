"""
Test script to verify the admin Stage 2 endpoint is working correctly.

This script tests:
1. Admin endpoint with correct API key (should succeed)
2. Admin endpoint with wrong API key (should fail with 403)
3. Admin endpoint with missing API key (should fail with 403)
4. Admin endpoint with non-existent conversation (should fail with 404)
"""

import requests
import json

BASE_URL = "http://localhost:8001"
ADMIN_KEY = "change-this-in-production"  # Match the default in config.py

def test_admin_endpoint():
    print("=" * 60)
    print("Testing Admin Stage 2 Endpoint")
    print("=" * 60)

    # Get a conversation with messages
    print("\n1. Finding a conversation with messages...")
    convs = requests.get(f"{BASE_URL}/api/conversations").json()

    test_conv = None
    for conv in convs:
        if conv['message_count'] > 0:
            test_conv = conv
            break

    if not test_conv:
        print("[FAIL] No conversations with messages found. Please send a message first.")
        return

    print(f"[PASS] Found conversation: {test_conv['id']} with {test_conv['message_count']} messages")

    # Test 1: Correct API key
    print("\n2. Testing with correct API key...")
    response = requests.get(
        f"{BASE_URL}/api/admin/conversations/{test_conv['id']}/stage2",
        headers={"X-Admin-Key": ADMIN_KEY}
    )

    if response.status_code == 200:
        data = response.json()
        print(f"[PASS] SUCCESS! Status: {response.status_code}")
        print(f"   - Conversation: {data.get('title')}")
        print(f"   - Total interactions: {data.get('total_interactions')}")

        if data.get('stage2_data'):
            print(f"   - Found Stage 2 data for {len(data['stage2_data'])} interactions")

            # Show details of first interaction
            first = data['stage2_data'][0]
            print(f"\n   First interaction details:")
            print(f"   - User question: {first['user_question'][:50]}...")
            print(f"   - Number of rankings: {len(first['stage2'])}")
            print(f"   - Aggregate rankings: {len(first['metadata']['aggregate_rankings'])} models")
        else:
            print(f"   - Message: {data.get('message')}")
    else:
        print(f"[FAIL] FAILED! Status: {response.status_code}")
        print(f"   Response: {response.json()}")

    # Test 2: Wrong API key
    print("\n3. Testing with wrong API key (should fail)...")
    response = requests.get(
        f"{BASE_URL}/api/admin/conversations/{test_conv['id']}/stage2",
        headers={"X-Admin-Key": "wrong-key"}
    )

    if response.status_code == 403:
        print(f"[PASS] Correctly rejected! Status: {response.status_code}")
        print(f"   Message: {response.json().get('detail')}")
    else:
        print(f"[FAIL] UNEXPECTED! Status: {response.status_code}")

    # Test 3: Missing API key
    print("\n4. Testing with missing API key (should fail)...")
    response = requests.get(
        f"{BASE_URL}/api/admin/conversations/{test_conv['id']}/stage2"
    )

    if response.status_code == 403:
        print(f"[PASS] Correctly rejected! Status: {response.status_code}")
        print(f"   Message: {response.json().get('detail')}")
    else:
        print(f"[FAIL] UNEXPECTED! Status: {response.status_code}")

    # Test 4: Non-existent conversation
    print("\n5. Testing with non-existent conversation (should fail)...")
    response = requests.get(
        f"{BASE_URL}/api/admin/conversations/fake-id-12345/stage2",
        headers={"X-Admin-Key": ADMIN_KEY}
    )

    if response.status_code == 404:
        print(f"[PASS] Correctly rejected! Status: {response.status_code}")
        print(f"   Message: {response.json().get('detail')}")
    else:
        print(f"[FAIL] UNEXPECTED! Status: {response.status_code}")

    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_admin_endpoint()
    except requests.exceptions.ConnectionError:
        print("[ERROR] Could not connect to backend at", BASE_URL)
        print("   Make sure the backend is running with: uv run python -m backend.main")
    except Exception as e:
        print(f"[ERROR] {type(e).__name__}: {e}")
