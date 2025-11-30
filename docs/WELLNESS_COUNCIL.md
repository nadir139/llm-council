# Wellness Council

**A Multidisciplinary AI Wellness Reflection Tool**

## ⚠️ CRITICAL DISCLAIMER

**THIS IS NOT MEDICAL ADVICE, THERAPY, OR PROFESSIONAL HEALTHCARE.**

Wellness Council is an AI-powered educational and self-exploration tool designed to help you reflect on wellness concerns from multiple professional perspectives. It is:

- ✅ For educational purposes and personal reflection
- ✅ A tool to organize your thoughts before seeing professionals
- ✅ A way to explore different wellness perspectives
- ❌ NOT a replacement for licensed healthcare professionals
- ❌ NOT medical, psychiatric, or psychological diagnosis or treatment
- ❌ NOT emergency services

**Always consult licensed healthcare professionals for medical, mental health, or wellness concerns.**

### Crisis Resources

If you're experiencing a mental health crisis or thoughts of self-harm:

- **988 Suicide & Crisis Lifeline:** Call or text **988** (24/7)
- **Crisis Text Line:** Text HOME to **741741** (24/7)
- **Emergency Services:** Call **911** or go to your nearest emergency room
- **International:** Find resources at [FindAHelpline.com](https://findahelpline.com)

---

## What is Wellness Council?

Wellness Council is a 3-stage deliberation system where multiple AI models, each given a specific healthcare professional role, collaboratively provide perspectives on wellness questions. The system combines:

- **Therapist** - CBT, emotional processing, talk therapy approaches
- **Psychiatrist** - Clinical assessment, medical perspectives, pharmacology
- **Personal Trainer** - Physical fitness, nutrition, body wellness
- **Doctor (GP)** - General health screening, lifestyle medicine, physical health
- **Psychologist** - Evidence-based interventions, behavioral science, research

### Key Innovation: Anonymous Peer Review

In **Stage 2**, each professional perspective anonymously evaluates all other perspectives, preventing bias and ensuring objective assessment of advice quality—just like real multidisciplinary healthcare teams.

---

## How It Works

### Stage 1: Professional Perspectives
Each AI "professional" independently responds to your wellness concern based on their specialized expertise. You can view each perspective individually through tabs.

**Example Question:** *"I feel that I am fat but everybody still thinks that I am skinny, how can I improve how I see myself, especially mentally?"*

**Responses:**
- **Therapist:** Explores cognitive distortions about body image, emotional processing
- **Psychiatrist:** Considers body dysmorphic disorder screening, clinical assessment
- **Personal Trainer:** Discusses body composition vs. weight, realistic fitness goals
- **Doctor:** Rules out thyroid/metabolic issues, nutritional deficiencies
- **Psychologist:** Applies evidence-based research on body image interventions

### Stage 2: Anonymous Peer Review
Each professional evaluates all responses (labeled as "Response A", "Response B", etc.) without knowing who wrote what. They assess:

- Appropriateness and safety of advice
- Medical/psychological factors considered
- Evidence-based quality
- Compassion and person-centered approach

The system calculates **aggregate rankings** showing which perspectives received the highest peer evaluations.

**Why This Matters:** Just like in real healthcare, different professionals catch each other's blind spots. The psychiatrist might recognize when the personal trainer's advice could reinforce dysmorphic thinking. The doctor might note medical factors the therapist hadn't considered.

### Stage 3: Integrative Wellness Recommendation
An **Integrative Wellness Coordinator** synthesizes all perspectives and peer reviews into a holistic recommendation that:

- Prioritizes safety (flags any red flags)
- Combines physical, mental, emotional dimensions
- Provides actionable next steps
- Emphasizes when to seek professional help
- Highlights where professionals agree (strong signal)

---

## Features

### Crisis Detection
The system automatically detects crisis keywords (suicide, self-harm, eating disorders, abuse, etc.) and displays prominent crisis resources at the top of responses.

### Medical Disclaimers
Prominent disclaimers appear throughout the interface to ensure users understand this is a reflection tool, not medical care.

### Transparent Reasoning
All raw professional evaluations are visible. You can see:
- Each professional's full response
- Each peer evaluation with extracted rankings
- How aggregate rankings were calculated

This transparency builds trust and allows you to validate the system's interpretation.

### Professional Role Badges
Each response is clearly labeled with the professional role, making it easy to understand the lens through which advice is given.

---

## Use Cases

### 1. Self-Reflection Before Appointments
Use Wellness Council to organize your thoughts and understand different perspectives before seeing actual healthcare providers. This can help you:
- Articulate concerns more clearly
- Know which type of professional to see first
- Prepare questions for your appointments

### 2. Understanding Multidisciplinary Perspectives
Wellness concerns often span multiple domains (mental, physical, behavioral). Wellness Council helps you see how different professionals would approach the same issue.

### 3. Exploring Options
When you're unsure whether a concern is primarily physical, mental, or behavioral, seeing multiple perspectives can help you understand the full picture.

### 4. Educational Tool
Learn about different therapeutic approaches, evidence-based interventions, and how healthcare professionals think about wellness.

---

## Example Scenarios

### Scenario 1: Body Image Concerns
**Question:** *"I feel that I am fat but everybody still thinks that I am skinny, how can I improve how I see myself, especially mentally?"*

**What You Get:**
- Therapist identifies cognitive distortions, suggests journaling/CBT techniques
- Psychiatrist screens for body dysmorphic disorder, discusses when clinical intervention helps
- Personal Trainer explains body composition vs. weight, promotes body-positive fitness
- Doctor rules out medical causes (thyroid, etc.), discusses nutrition's role in mental health
- Psychologist provides research-backed interventions for body image

**Peer Review Shows:** Therapist and Psychologist perspectives ranked highest for addressing core cognitive/behavioral issues. Doctor's medical screening noted as important preliminary step.

**Integrative Recommendation:** Combines cognitive restructuring (therapy), medical screening (doctor), evidence-based techniques (psychologist), and healthy relationship with fitness (trainer).

### Scenario 2: Relationship Anxiety
**Question:** *"I have a feeling that my boyfriend doesn't like me anymore, how can I find out without asking him directly?"*

**What You Get:**
- Therapist explores attachment styles, communication patterns, fear of vulnerability
- Psychiatrist considers anxiety disorders, relationship anxiety symptoms
- Personal Trainer discusses physical intimacy and shared activities
- Doctor asks about hormonal changes that might affect mood/perception
- Psychologist explains confirmation bias, provides reality-testing techniques

**Peer Review Shows:** Psychologist and Therapist perspectives ranked highest for addressing the cognitive and relational aspects. Doctor's hormonal consideration noted as worth exploring but likely secondary.

**Integrative Recommendation:** Primary focus on anxiety/attachment (therapist + psychologist), with medical ruling out (doctor) and relationship-building activities (trainer). Challenges the premise—why not ask directly? Explores underlying fear of communication.

---

## Technical Architecture

### Backend (Python/FastAPI)
- **5 Council Models:** Each assigned a professional role via system prompts
- **Role-Specific Prompts:** Detailed personas defining expertise, focus areas, and approach
- **Crisis Detection:** Keyword scanning triggers crisis resource display
- **Anonymous Peer Review:** Stage 2 anonymizes responses as "Response A, B, C, etc."
- **Aggregate Ranking:** Calculates average position across all peer evaluations

### Frontend (React)
- **Professional Role Badges:** Visual indication of each perspective's specialty
- **Tabbed Interface:** Easy navigation between professionals and peer reviews
- **Medical Disclaimers:** Prominent warnings throughout
- **Crisis Resources Component:** Auto-displays when crisis keywords detected
- **Transparent Evaluation:** Shows raw peer reviews and extracted rankings

---

## Configuration

### Customizing Professional Roles

Edit `backend/config.py` to:
- Change which AI models represent each professional
- Modify role prompts to adjust professional personas
- Add/remove specialties
- Adjust crisis keywords

### Changing the Council Composition

Current setup: 5 professionals (Therapist, Psychiatrist, Personal Trainer, Doctor, Psychologist)

You can modify this to include:
- Nutritionist
- Sleep specialist
- Social worker
- Couples counselor
- Addiction specialist
- etc.

Simply update `COUNCIL_MODELS`, `ROLE_PROMPTS`, and `ROLE_NAMES` in `backend/config.py`.

---

## Ethics & Safety

### What We've Built In

1. **Crisis Detection:** Automatic detection of crisis keywords with prominent resource display
2. **Medical Disclaimers:** Visible on every screen, can't be missed
3. **Non-Directive Framing:** "Wellness reflection tool" not "AI therapist" or "AI doctor"
4. **Professional Care Emphasis:** Stage 3 synthesis always includes when/why to seek real professionals
5. **Transparent Reasoning:** All evaluations visible for scrutiny

### What You Must Add

1. **Legal Review:** Have actual healthcare attorneys review disclaimers for your jurisdiction
2. **User Agreement:** Terms of service making it clear this is not medical care
3. **Age Restrictions:** Consider minimum age requirements
4. **Data Privacy:** HIPAA-compliant storage if handling health information
5. **Professional Oversight:** Consider having licensed professionals review system outputs

### What This Is NOT

- ❌ Telemed
icine or telehealth service
- ❌ Licensed therapy or counseling
- ❌ Medical diagnosis or treatment
- ❌ Prescription or medication management
- ❌ Emergency services
- ❌ Replacement for human healthcare providers

---

## Limitations

### AI Limitations
- AI cannot detect non-verbal cues, body language, or subtle indicators
- AI lacks human empathy and lived experience
- AI may hallucinate or provide inaccurate information
- AI cannot perform physical exams or diagnostic tests
- AI cannot legally prescribe or diagnose

### Systemic Limitations
- No accountability or liability like licensed professionals have
- No continuity of care or long-term relationship
- No ability to hospitalize or intervene in emergencies
- No insurance coverage or treatment records
- No professional licensing or oversight

### Use Case Limitations
- Not suitable for emergency situations
- Not suitable for complex psychiatric conditions
- Not suitable for medication management
- Not suitable for diagnosis of any condition
- Not suitable for legal/court-mandated treatment

---

## Installation & Setup

### Prerequisites
- Python 3.8+
- Node.js 16+
- OpenRouter API key

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# Add your OPENROUTER_API_KEY to .env
python -m backend.main
```

Backend runs on **http://localhost:8001**

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

Frontend runs on **http://localhost:5173**

### Environment Variables
```
OPENROUTER_API_KEY=your_key_here
```

---

## Future Enhancements

### Potential Features
- **Follow-Up Questions:** Allow users to ask specific professionals follow-up questions
- **Conversation History Analysis:** Track patterns over time (with user consent)
- **Resource Library:** Links to vetted mental health resources, exercises, worksheets
- **Professional Referral Network:** Connect users with actual licensed professionals in their area
- **Multi-Language Support:** Serve diverse populations
- **Accessibility Features:** Screen reader optimization, high contrast modes
- **Export Functionality:** Save conversations for discussion with real healthcare providers

### Research Opportunities
- Study whether multidisciplinary AI perspectives improve help-seeking behavior
- Measure if users feel more prepared for actual healthcare appointments
- Analyze which professional perspectives users find most valuable for different concerns
- Evaluate if peer review improves advice quality vs. single-model approaches

---

## Development Notes

### Adding a New Professional Role

1. **Choose a model** in `backend/config.py`:
   ```python
   COUNCIL_MODELS = [
       # ... existing models
       "anthropic/claude-sonnet-4.5",  # New role
   ]
   ```

2. **Create role prompt**:
   ```python
   ROLE_PROMPTS = {
       "anthropic/claude-sonnet-4.5": """You are a certified nutritionist...

       Focus on:
       - Dietary patterns and nutrition
       - Meal planning
       - etc.
       """
   }
   ```

3. **Add role name**:
   ```python
   ROLE_NAMES = {
       "anthropic/claude-sonnet-4.5": "Nutritionist"
   }
   ```

4. No frontend changes needed—it automatically displays the new role!

### Testing Different Prompts

Use the conversation history to A/B test different role prompts. Track which prompt variations:
- Receive higher peer review rankings
- Provide more actionable advice
- Better balance safety with empowerment

---

## Contributing

This is a sensitive application dealing with human wellbeing. If contributing:

1. **Safety First:** Any PR must maintain or improve safety features
2. **Ethical Review:** Consider ethical implications of changes
3. **Medical Accuracy:** Consult healthcare professionals when appropriate
4. **Inclusive Design:** Consider diverse populations and needs
5. **Transparent Communication:** Never hide system limitations

---

## License & Attribution

Based on the LLM Council architecture. Adapted for wellness/healthcare education and reflection.

**Remember:** This is a tool for exploration and reflection, not a replacement for human healthcare professionals. Always seek professional help for medical, mental health, or wellness concerns.

---

## Support & Feedback

If you're struggling with mental health, please reach out to:
- **988 Suicide & Crisis Lifeline:** Call or text **988**
- **SAMHSA National Helpline:** 1-800-662-4357
- **Crisis Text Line:** Text HOME to 741741

For technical issues or feedback about this tool, please contact [your contact method].

---

**Built with care for human wellbeing. Used responsibly, this tool can help people organize their thoughts and explore wellness from multiple angles before seeking professional care.**
