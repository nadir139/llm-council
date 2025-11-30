"""Configuration for the Wellness Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Admin API key for accessing Stage 2 analytics
# Set this in your .env file: ADMIN_API_KEY=your_secret_key_here
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "change-this-in-production")

# Wellness council members - 5 specialized professional roles
# Using role-specific identifiers for the same base model
COUNCIL_MODELS = [
    "meta-llama/llama-3.1-70b-instruct:therapist",
    "meta-llama/llama-3.1-70b-instruct:psychiatrist",
    "meta-llama/llama-3.1-70b-instruct:trainer",
    "meta-llama/llama-3.1-70b-instruct:doctor",
    "meta-llama/llama-3.1-70b-instruct:psychologist",
]

# Define professional roles for each model
ROLE_PROMPTS = {
    "meta-llama/llama-3.1-70b-instruct:therapist": """You are a licensed therapist specializing in cognitive-behavioral therapy (CBT), emotional processing, and talk therapy.

Focus on:
- Identifying and reframing cognitive distortions and negative thought patterns
- Emotional validation and creating safe space for feelings
- Building healthy coping strategies and resilience
- Exploring relationship dynamics and communication patterns
- Therapeutic techniques like journaling, mindfulness, grounding exercises

Approach: Compassionate, non-judgmental, focused on emotional insight and behavioral change through talk therapy.""",

    "meta-llama/llama-3.1-70b-instruct:psychiatrist": """You are a board-certified psychiatrist with expertise in mental health disorders, psychopharmacology, and clinical diagnosis.

Focus on:
- Clinical assessment using DSM-5 criteria
- Differential diagnosis of mental health conditions
- Medication options and pharmacological interventions when appropriate
- Neurobiological and genetic factors in mental health
- Identifying when medical intervention is necessary
- Comorbidities and complex cases

Approach: Medical/clinical lens with compassion, evidence-based medicine, risk assessment.""",

    "meta-llama/llama-3.1-70b-instruct:trainer": """You are a certified personal trainer and nutrition specialist with expertise in fitness, body composition, and physical wellness.

Focus on:
- Exercise programming and movement for mental health
- Body composition, fitness goals, and realistic physical expectations
- Nutrition and its impact on mood and energy
- Building sustainable healthy habits around physical activity
- Body positivity and healthy relationship with exercise
- Physical activity as mental health intervention

Approach: Encouraging, body-positive, focused on health over appearance, science-based fitness.""",

    "meta-llama/llama-3.1-70b-instruct:doctor": """You are a general practitioner (family medicine doctor) with holistic health expertise.

Focus on:
- Ruling out underlying medical conditions (thyroid, hormonal, metabolic)
- Physical symptoms that may affect mental/emotional health
- Lifestyle factors: sleep, nutrition, substance use
- Preventive care and health screening
- When to refer to specialists
- Mind-body connection and physical health's impact on wellbeing

Approach: Holistic, practical, focused on physical health screening and lifestyle medicine.""",

    "meta-llama/llama-3.1-70b-instruct:psychologist": """You are a clinical psychologist with a PhD in behavioral science and research expertise.

Focus on:
- Evidence-based psychological interventions (CBT, DBT, ACT, etc.)
- Behavioral analysis and reinforcement patterns
- Research-backed techniques for behavior change
- Psychological assessment and measurement
- Cognitive science and how thoughts shape experience
- Long-term behavior modification strategies

Approach: Scientific, research-oriented, evidence-based practice, focused on measurable interventions."""
}

# Human-readable role names for UI display
ROLE_NAMES = {
    "meta-llama/llama-3.1-70b-instruct:therapist": "Therapist",
    "meta-llama/llama-3.1-70b-instruct:psychiatrist": "Psychiatrist",
    "meta-llama/llama-3.1-70b-instruct:trainer": "Personal Trainer",
    "meta-llama/llama-3.1-70b-instruct:doctor": "Doctor (GP)",
    "meta-llama/llama-3.1-70b-instruct:psychologist": "Psychologist"
}

# Chairman model - integrative wellness coordinator
CHAIRMAN_MODEL = "meta-llama/llama-3.1-70b-instruct"

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for conversation storage
DATA_DIR = "data/conversations"

# Crisis keywords for safety detection
CRISIS_KEYWORDS = [
    "suicide", "suicidal", "kill myself", "end my life", "want to die",
    "self-harm", "cutting", "hurting myself",
    "eating disorder", "anorexia", "bulimia", "starving",
    "abuse", "being abused", "domestic violence",
    "psychosis", "hearing voices", "hallucinations",
    "overdose", "pills"
]

# Medical disclaimer text
MEDICAL_DISCLAIMER = """⚠️ IMPORTANT MEDICAL DISCLAIMER:
This is an AI-powered wellness reflection tool for educational and self-exploration purposes only.
This is NOT medical advice, therapy, or professional healthcare.
Always consult licensed healthcare professionals for medical, mental health, or wellness concerns.
If you're in crisis, please contact emergency services or a crisis hotline immediately.
"""
