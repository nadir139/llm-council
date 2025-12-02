"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio

from . import storage
from . import config
from .council import run_full_council, generate_conversation_title, stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, calculate_aggregate_rankings
from .auth import get_current_user, get_admin_key

app = FastAPI(title="LLM Council API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str


class UpdateTitleRequest(BaseModel):
    """Request to update conversation title."""
    title: str


class FollowUpRequest(BaseModel):
    """Request to submit follow-up answers for Feature 3."""
    follow_up_answers: str


class CreateProfileRequest(BaseModel):
    """Request to create user profile."""
    gender: str
    age_range: str
    mood: str


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
    messages: List[Dict[str, Any]]


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations(user: Dict[str, Any] = Depends(get_current_user)):
    """List all conversations (metadata only). Requires authentication."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(
    request: CreateConversationRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Create a new conversation. Requires authentication."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get a specific conversation with all its messages. Requires authentication."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.

    Feature 3: Now injects user profile for personalized recommendations.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Feature 3: Get user profile for context injection
    user_profile = storage.get_user_profile(user["user_id"])

    # Feature 3: Get follow-up context if it exists
    follow_up_context = conversation.get("follow_up_answers")

    # Run the 3-stage council process with profile and follow-up context
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content,
        user_profile=user_profile,
        follow_up_context=follow_up_context
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
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
async def send_message_stream(
    conversation_id: str,
    request: SendMessageRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.

    Feature 3: Now injects user profile and follow-up context for personalization.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Feature 3: Get user profile for context injection
    user_profile = storage.get_user_profile(user["user_id"])

    # Feature 3: Get follow-up context if it exists
    follow_up_context = conversation.get("follow_up_answers")

    async def event_generator():
        try:
            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses with profile and follow-up context
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(
                request.content,
                user_profile=user_profile,
                follow_up_context=follow_up_context
            )
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(request.content, stage1_results, stage2_results)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            # Reload conversation to get updated report_cycle
            conversation = storage.get_conversation(conversation_id)

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
    user: Dict[str, Any] = Depends(get_current_user)
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
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if already submitted follow-up for this cycle
    if conversation.get("has_follow_up", False):
        raise HTTPException(
            status_code=400,
            detail="Follow-up already submitted for this report cycle"
        )

    # Save follow-up answers to conversation
    storage.save_follow_up_answers(conversation_id, request.follow_up_answers)

    # Reload conversation to get updated data
    conversation = storage.get_conversation(conversation_id)

    # Get user profile for personalization
    user_profile = storage.get_user_profile(user["user_id"])

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
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Reload conversation again to get final state
    conversation = storage.get_conversation(conversation_id)

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
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Toggle the starred status of a conversation. Requires authentication."""
    try:
        starred = storage.toggle_conversation_starred(conversation_id)
        return {"starred": starred}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.patch("/api/conversations/{conversation_id}/title")
async def update_conversation_title(
    conversation_id: str,
    request: UpdateTitleRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Update the title of a conversation. Requires authentication."""
    try:
        storage.update_conversation_title(conversation_id, request.title)
        return {"title": request.title}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Delete a conversation. Requires authentication."""
    storage.delete_conversation(conversation_id)
    return {"deleted": True}


@app.get("/api/admin/conversations/{conversation_id}/stage2")
async def get_stage2_analytics(
    conversation_id: str,
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key")
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
    conversation = storage.get_conversation(conversation_id)
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
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a user profile (after onboarding questions).
    Profile is locked after creation and cannot be edited.
    """
    # Check if profile already exists
    existing_profile = storage.get_user_profile(user["user_id"])
    if existing_profile:
        raise HTTPException(
            status_code=400,
            detail="Profile already exists and is locked"
        )

    # Create profile
    profile = storage.create_user_profile(
        user_id=user["user_id"],
        email=user["email"],
        profile_data={
            "gender": request.gender,
            "age_range": request.age_range,
            "mood": request.mood
        }
    )

    return profile


@app.get("/api/users/profile", response_model=UserProfile)
async def get_profile(user: Dict[str, Any] = Depends(get_current_user)):
    """Get the current user's profile."""
    profile = storage.get_user_profile(user["user_id"])

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Profile not found. Please complete onboarding."
        )

    return profile


@app.patch("/api/users/profile", response_model=UserProfile)
async def update_profile(
    request: CreateProfileRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update user profile (only if not locked).
    Note: Profiles are locked by default after creation per spec.
    """
    try:
        profile = storage.update_user_profile(
            user_id=user["user_id"],
            profile_data={
                "gender": request.gender,
                "age_range": request.age_range,
                "mood": request.mood
            }
        )
        return profile
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
