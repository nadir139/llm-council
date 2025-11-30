"""3-stage Wellness Council orchestration."""

from typing import List, Dict, Any, Tuple
from .openrouter import query_model
from .config import (
    COUNCIL_MODELS, CHAIRMAN_MODEL, ROLE_PROMPTS, ROLE_NAMES,
    MEDICAL_DISCLAIMER, CRISIS_KEYWORDS
)
import asyncio


def check_for_crisis(user_query: str) -> bool:
    """
    Detect if query contains crisis indicators requiring immediate intervention.

    Args:
        user_query: The user's question

    Returns:
        True if crisis keywords detected, False otherwise
    """
    query_lower = user_query.lower()
    return any(keyword in query_lower for keyword in CRISIS_KEYWORDS)


async def stage1_collect_responses(user_query: str) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual responses from wellness professionals.

    Args:
        user_query: The user's wellness question/concern

    Returns:
        List of dicts with 'model', 'response', and 'role' keys
    """
    # Prepend disclaimer to user query
    query_with_disclaimer = f"""{MEDICAL_DISCLAIMER}

User's Question/Concern:
{user_query}

Please provide your professional perspective on this concern."""

    stage1_results = []

    # Query each model with its specific professional role
    tasks = []
    for model in COUNCIL_MODELS:
        role_context = ROLE_PROMPTS.get(model, "")

        messages = [
            {"role": "system", "content": role_context},
            {"role": "user", "content": query_with_disclaimer}
        ]

        tasks.append(query_model(model, messages))

    # Wait for all responses
    responses = await asyncio.gather(*tasks)

    # Format results with role information
    for model, response in zip(COUNCIL_MODELS, responses):
        if response is not None:  # Only include successful responses
            stage1_results.append({
                "model": model,
                "response": response.get('content', ''),
                "role": ROLE_NAMES.get(model, "Health Professional")
            })

    return stage1_results


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Response A, Response B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])

    ranking_prompt = f"""You are a healthcare professional conducting peer review of wellness recommendations.

User's Concern: {user_query}

Here are responses from different healthcare professionals (anonymized for unbiased review):

{responses_text}

Your task as a healthcare professional:
1. First, evaluate each response individually. For each response, consider:
   - Appropriateness and safety of the advice given
   - Whether important medical/psychological factors were considered
   - Potential risks, contraindications, or red flags
   - Completeness of the professional perspective
   - Evidence-based quality and practical applicability
   - Compassion and person-centered approach

2. Then, at the very end of your response, provide your FINAL RANKING of which responses would be most helpful and safe for this person.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Example format:

Response A provides compassionate insight into emotional factors but may miss underlying medical considerations...
Response B offers evidence-based interventions and appropriately addresses safety concerns...
Response C takes a holistic approach but could be more specific...

FINAL RANKING:
1. Response B
2. Response C
3. Response A

Now provide your peer evaluation and ranking:"""

    # Get rankings from all council models in parallel, each with their professional role
    tasks = []
    for model in COUNCIL_MODELS:
        role_context = ROLE_PROMPTS.get(model, "")
        messages = [
            {"role": "system", "content": role_context},
            {"role": "user", "content": ranking_prompt}
        ]
        tasks.append(query_model(model, messages))

    responses = await asyncio.gather(*tasks)

    # Format results
    stage2_results = []
    for model, response in zip(COUNCIL_MODELS, responses):
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed,
                "role": ROLE_NAMES.get(model, "Health Professional")
            })

    return stage2_results, label_to_model


async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2

    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nResponse: {result['response']}"
        for result in stage1_results
    ])

    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])

    chairman_prompt = f"""You are an Integrative Wellness Coordinator synthesizing input from a multidisciplinary healthcare team.

{MEDICAL_DISCLAIMER}

User's Concern: {user_query}

PROFESSIONAL PERSPECTIVES (Stage 1):
{stage1_text}

PEER EVALUATIONS (Stage 2):
{stage2_text}

Your task as Integrative Wellness Coordinator:
Synthesize all professional perspectives into a holistic, compassionate wellness recommendation that:

1. **Safety First**: Flag any medical red flags or concerns requiring immediate professional intervention
2. **Integrative Approach**: Combine physical, mental, emotional, and behavioral health dimensions
3. **Actionable Steps**: Provide clear, practical next steps the person can take
4. **Professional Care**: Emphasize when and why to seek specific professional help
5. **Evidence-Based**: Prioritize interventions with research support
6. **Person-Centered**: Be compassionate, non-judgmental, and empowering
7. **Patterns of Agreement**: Highlight where multiple professionals agree (strong signal)
8. **Balanced Perspective**: Address different viewpoints respectfully

Structure your response as:
- **Key Insights**: What the council collectively understands about this concern
- **Recommended Approach**: Integrated action plan combining perspectives
- **Important Considerations**: Safety concerns, when to seek professional help, what to monitor
- **Next Steps**: Specific, actionable recommendations

Provide your integrative wellness recommendation:"""

    messages = [{"role": "user", "content": chairman_prompt}]

    # Query the chairman model
    response = await query_model(CHAIRMAN_MODEL, messages)

    if response is None:
        # Fallback if chairman fails
        return {
            "model": CHAIRMAN_MODEL,
            "response": "Error: Unable to generate final synthesis."
        }

    return {
        "model": CHAIRMAN_MODEL,
        "response": response.get('content', '')
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]

            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches

    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        ranking_text = ranking['ranking']

        # Parse the ranking from the structured format
        parsed_ranking = parse_ranking_from_text(ranking_text)

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })

    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])

    return aggregate


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    # Use gemini-2.5-flash for title generation (fast and cheap)
    response = await query_model("google/gemini-2.5-flash", messages, timeout=30.0)

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(user_query: str) -> Tuple[List, List, Dict, Dict]:
    """
    Run the complete 3-stage wellness council process.

    Args:
        user_query: The user's wellness question/concern

    Returns:
        Tuple of (stage1_results, stage2_results, stage3_result, metadata)
    """
    # Check for crisis keywords
    is_crisis = check_for_crisis(user_query)

    # Stage 1: Collect individual responses from wellness professionals
    stage1_results = await stage1_collect_responses(user_query)

    # If no models responded successfully, return error
    if not stage1_results:
        return [], [], {
            "model": "error",
            "response": "All wellness professionals failed to respond. Please try again."
        }, {"is_crisis": is_crisis}

    # Stage 2: Collect peer rankings
    stage2_results, label_to_model = await stage2_collect_rankings(user_query, stage1_results)

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final wellness recommendation
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results
    )

    # Prepare metadata
    metadata = {
        "label_to_model": label_to_model,
        "aggregate_rankings": aggregate_rankings,
        "is_crisis": is_crisis
    }

    return stage1_results, stage2_results, stage3_result, metadata
