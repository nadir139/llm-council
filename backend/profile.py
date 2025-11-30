"""User profile storage and management."""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

# Profile data directory
PROFILE_DIR = "data/profiles"


def ensure_profile_dir():
    """Ensure the profile directory exists."""
    Path(PROFILE_DIR).mkdir(parents=True, exist_ok=True)


def get_profile_path(user_id: str) -> str:
    """Get the file path for a user profile."""
    return os.path.join(PROFILE_DIR, f"{user_id}.json")


def create_profile(
    user_id: str,
    gender: str,
    age_range: str,
    mood: str
) -> Dict[str, Any]:
    """
    Create a new user profile.

    Args:
        user_id: Unique identifier for the user (conversation_id for anonymous users)
        gender: User's gender selection
        age_range: User's age range selection
        mood: User's current mood selection

    Returns:
        New profile dict
    """
    ensure_profile_dir()

    # Validate inputs
    valid_genders = ["Male", "Female", "Other", "Prefer not to say"]
    valid_age_ranges = ["12-17", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
    valid_moods = ["Happy", "I don't know", "Sad"]

    if gender not in valid_genders:
        raise ValueError(f"Invalid gender. Must be one of: {valid_genders}")
    if age_range not in valid_age_ranges:
        raise ValueError(f"Invalid age range. Must be one of: {valid_age_ranges}")
    if mood not in valid_moods:
        raise ValueError(f"Invalid mood. Must be one of: {valid_moods}")

    profile = {
        "user_id": user_id,
        "gender": gender,
        "age_range": age_range,
        "mood": mood,
        "created_at": datetime.utcnow().isoformat(),
        "locked": True  # Profile is locked after creation
    }

    # Save to file
    path = get_profile_path(user_id)
    with open(path, 'w') as f:
        json.dump(profile, f, indent=2)

    return profile


def get_profile(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a user profile from storage.

    Args:
        user_id: Unique identifier for the user

    Returns:
        Profile dict or None if not found
    """
    path = get_profile_path(user_id)

    if not os.path.exists(path):
        return None

    with open(path, 'r') as f:
        return json.load(f)


def profile_exists(user_id: str) -> bool:
    """
    Check if a profile exists for a user.

    Args:
        user_id: Unique identifier for the user

    Returns:
        True if profile exists, False otherwise
    """
    return os.path.exists(get_profile_path(user_id))


def get_profile_context(user_id: str) -> str:
    """
    Get profile information formatted for LLM prompt injection.

    Args:
        user_id: Unique identifier for the user

    Returns:
        Formatted profile context string for LLM prompts
    """
    profile = get_profile(user_id)

    if profile is None:
        return ""

    # Format profile data for LLM context
    context = f"""USER PROFILE CONTEXT:
- Gender: {profile['gender']}
- Age Range: {profile['age_range']}
- Current Mood: {profile['mood']}

Please consider this context when providing your professional perspective. Tailor your response to be appropriate for this individual's age, and be mindful of their current emotional state."""

    return context
