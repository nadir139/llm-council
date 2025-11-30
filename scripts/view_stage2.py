"""
View Stage 2 analytics data for a specific conversation.

Usage:
    python view_stage2.py <conversation_id>

Example:
    python view_stage2.py 47495629-ce1f-4e9a-bc03-b644c5ba72e5
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8001"
ADMIN_KEY = "ciaociaociao"

def view_stage2(conversation_id):
    """Fetch and display Stage 2 data for a conversation."""

    print("=" * 80)
    print(f"Stage 2 Analytics for Conversation: {conversation_id}")
    print("=" * 80)

    response = requests.get(
        f"{BASE_URL}/api/admin/conversations/{conversation_id}/stage2",
        headers={"X-Admin-Key": ADMIN_KEY}
    )

    if response.status_code != 200:
        print(f"\n[ERROR] Status {response.status_code}: {response.json().get('detail')}")
        return

    data = response.json()

    print(f"\nConversation Title: {data['title']}")
    print(f"Created: {data['created_at']}")
    print(f"Total Interactions: {data['total_interactions']}")
    print("\n" + "=" * 80)

    if not data.get('stage2_data'):
        print(f"\n{data.get('message', 'No Stage 2 data available')}")
        return

    # Display each interaction
    for i, interaction in enumerate(data['stage2_data'], 1):
        print(f"\n{'#' * 80}")
        print(f"INTERACTION {i} (Message Index: {interaction['message_index']})")
        print(f"{'#' * 80}")

        print(f"\nUser Question:")
        print(f"  {interaction['user_question']}")

        # Show label-to-model mapping
        label_map = interaction['metadata']['label_to_model']
        if label_map:
            print(f"\nModel Mapping (Anonymization):")
            for label, model in sorted(label_map.items()):
                model_name = model.split('/')[-1] if '/' in model else model
                print(f"  {label} -> {model_name}")

        # Show aggregate rankings
        agg_rankings = interaction['metadata']['aggregate_rankings']
        if agg_rankings:
            print(f"\nAggregate Rankings (Street Cred):")
            for rank_idx, agg in enumerate(agg_rankings, 1):
                model_name = agg['model'].split('/')[-1] if '/' in agg['model'] else agg['model']
                avg_rank = agg['average_rank']
                count = agg['rankings_count']
                print(f"  #{rank_idx}: {model_name} (avg rank: {avg_rank:.2f}, {count} votes)")

        # Show individual rankings
        print(f"\n{'-' * 80}")
        print(f"INDIVIDUAL PEER REVIEWS:")
        print(f"{'-' * 80}")

        for rank_idx, ranking in enumerate(interaction['stage2'], 1):
            model_name = ranking['model'].split('/')[-1] if '/' in ranking['model'] else ranking['model']

            print(f"\n[{rank_idx}] Reviewer: {model_name}")
            print(f"{'-' * 80}")

            # Show parsed ranking (the order they ranked responses)
            if ranking.get('parsed_ranking'):
                print(f"\nRanking Order:")
                for pos, label in enumerate(ranking['parsed_ranking'], 1):
                    actual_model = label_map.get(label, label)
                    actual_model_name = actual_model.split('/')[-1] if '/' in actual_model else actual_model
                    print(f"  {pos}. {label} ({actual_model_name})")

            # Show full review text
            print(f"\nFull Review:")
            print(f"{'-' * 80}")
            # Wrap text to 80 characters
            review_text = ranking['ranking']
            for line in review_text.split('\n'):
                if len(line) <= 76:
                    print(f"  {line}")
                else:
                    # Simple word wrap
                    words = line.split()
                    current_line = "  "
                    for word in words:
                        if len(current_line) + len(word) + 1 <= 80:
                            current_line += word + " "
                        else:
                            print(current_line.rstrip())
                            current_line = "  " + word + " "
                    if current_line.strip():
                        print(current_line.rstrip())
            print()

        # Crisis detection
        if interaction['metadata'].get('is_crisis'):
            print("\n[!] CRISIS DETECTED - Crisis resources were shown to user")

    print("\n" + "=" * 80)
    print("End of Stage 2 Analytics")
    print("=" * 80)

def list_conversations():
    """List all available conversations."""
    response = requests.get(f"{BASE_URL}/api/conversations")

    if response.status_code != 200:
        print("[ERROR] Could not fetch conversations")
        return

    convs = response.json()

    print("\n" + "=" * 80)
    print("Available Conversations")
    print("=" * 80)

    for conv in convs:
        if conv['message_count'] > 0:
            print(f"\nID: {conv['id']}")
            print(f"  Title: {conv['title']}")
            print(f"  Messages: {conv['message_count']}")
            print(f"  Created: {conv['created_at']}")
            if conv.get('starred'):
                print(f"  [STARRED]")

    print("\n" + "=" * 80)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\nUsage: python view_stage2.py <conversation_id>")
        print("\nTo see available conversations, run:")
        print("  python view_stage2.py --list\n")
        sys.exit(1)

    if sys.argv[1] == "--list":
        try:
            list_conversations()
        except requests.exceptions.ConnectionError:
            print("\n[ERROR] Could not connect to backend at", BASE_URL)
            print("Make sure the backend is running: uv run python -m backend.main\n")
    else:
        conversation_id = sys.argv[1]
        try:
            view_stage2(conversation_id)
        except requests.exceptions.ConnectionError:
            print("\n[ERROR] Could not connect to backend at", BASE_URL)
            print("Make sure the backend is running: uv run python -m backend.main\n")
        except Exception as e:
            print(f"\n[ERROR] {type(e).__name__}: {e}\n")
