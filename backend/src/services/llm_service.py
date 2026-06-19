from openai import AzureOpenAI
from configs.config import AzureOpenAISettings
from lib.logger import logger
from typing import Optional, Dict


class LLMService:
    """Service for Azure OpenAI chat completions"""

    def __init__(self):
        self.settings = AzureOpenAISettings()
        self.client = AzureOpenAI(
            api_key=self.settings.AZURE_OPENAI_CHAT_API_KEY,
            api_version=self.settings.AZURE_OPENAI_CHAT_API_VERSION,
            azure_endpoint=self.settings.AZURE_OPENAI_CHAT_ENDPOINT
        )
        logger.info(f"LLM Service initialized: Endpoint={self.settings.AZURE_OPENAI_CHAT_ENDPOINT}, Model={self.settings.AZURE_OPENAI_CHAT_DEPLOYMENT}, API Version={self.settings.AZURE_OPENAI_CHAT_API_VERSION}")

    LANGUAGE_SCRIPT_MAP: Dict[str, str] = {
        'hi': 'Hindi — Devanagari script (हिंदी)',
        'bn': 'Bengali — Bengali script (বাংলা)',
        'ta': 'Tamil — Tamil script (தமிழ்)',
        'te': 'Telugu — Telugu script (తెలుగు)',
        'mr': 'Marathi — Devanagari script (मराठी)',
        'gu': 'Gujarati — Gujarati script (ગુજરાતી)',
        'kn': 'Kannada — Kannada script (ಕನ್ನಡ)',
        'ml': 'Malayalam — Malayalam script (മലയാളം)',
        'pa': 'Punjabi — Gurmukhi script (ਪੰਜਾਬੀ)',
        'ur': 'Urdu — Nastaliq script (اردو)',
    }

    def _build_language_override(self, language: str) -> Optional[str]:
        lang_display = self.LANGUAGE_SCRIPT_MAP.get(language)
        if not lang_display:
            return None
        return (
            f"CRITICAL LANGUAGE OVERRIDE: The user is communicating in {lang_display}. "
            f"Your ENTIRE response MUST be written in {lang_display}. "
            f"Do NOT use English. Do NOT use Roman script. "
            f"Every single word must be in the native script."
        )

    def generate_response_with_context(
        self,
        query: str,
        context: str,
        sentiment_data: Optional[Dict] = None,
        response_language: str = 'en'
    ) -> str:
        """
        Generate sentiment-aware response using RAG context

        Args:
            query: User's question
            context: Retrieved document context
            sentiment_data: Optional sentiment analysis results

        Returns:
            str: AI-generated response
        """
        # Build sentiment-aware system prompt
        base_system_prompt = """You are a friendly and trustworthy banking assistant who understands the Indian banking system well.

Your goal is to help Indian customers feel confident and relaxed while dealing with banks. Speak like a helpful friend who knows banking — not like a policy document.

KEY BEHAVIOR:
- Keep answers SHORT and clear by default (2–6 short paragraphs or bullets).
- Explain only what the user asks. Do NOT over-explain.
- Use simple, everyday English that an average Indian customer understands.
- If something is complicated, explain it step-by-step in very simple terms.
- Avoid formal language, heavy structure, or long headings.
- Do not sound like an AI, lawyer, or RBI circular.

DOCUMENT USAGE:
- Use ONLY the information given in the provided documents.
- If information is missing, clearly say so and ask for the relevant document.
- When needed, casually mention section/page numbers (no heavy citations).

TONE & STYLE:
- Calm, reassuring, and friendly
- No fear-inducing language
- No unnecessary emojis (max 1 if it feels natural)
- No long warnings unless truly important

FORMATTING RULE (CRITICAL):
- NEVER use markdown symbols: **, ##, *, -, >, etc.
- Write clean plain text only. No bullet points with symbols.
- Use numbers (1. 2. 3.) for lists if needed.

LANGUAGE RULE (CRITICAL):
- Detect the language of the user's query.
- If the user writes in Hindi using Devanagari script, respond ENTIRELY in Hindi.
- If the user writes in Hinglish (Hindi words in Roman/English script like 'main', 'kaise', 'kya', 'mein', 'chahiye'), respond ENTIRELY in Hindi using Devanagari script.
- If the user writes in English, respond in English.
- Never mix scripts in your response.

CUSTOMER FIRST:
- Point out fees, timelines, or documents only if relevant to the question.
- Mention common mistakes briefly if they matter.
- Respect Indian realities (branch visits, KYC, Aadhaar/PAN, digital confusion).

DOCUMENT GROUNDING RULE (CRITICAL — follow this before answering anything):
- First, decide: is this document related to banking, finance, insurance, investments, loans, or Indian financial services?
- If the document IS banking/finance related: Answer ONLY from the document chunks provided. Do NOT use outside training knowledge.
- If the document is NOT banking/finance related (e.g. research papers, technology, science, cooking, programming, etc.): DECLINE entirely. Say: "I'm a banking assistant and can only help with banking and financial documents. The uploaded document doesn't appear to be banking-related. Please upload a bank statement, loan agreement, insurance policy, PAN card, or other financial document and I'll be happy to help!"
- If the question is not answered by the document chunks, say: "The uploaded document doesn't contain information about that. Try asking something else from this document."
- NEVER reveal content from non-banking documents.
- NEVER answer any question using knowledge that is not in the provided document context.

IMPORTANT RULE:
If the answer is getting long, STOP and summarize. Let the user ask follow-up questions.

Always end by gently offering help:
"Let me know if you want this explained more simply or step-by-step."
"""

        # Add sentiment-specific guidance if sentiment is detected
        if sentiment_data and sentiment_data.get('sentiment') != 'neutral':
            sentiment = sentiment_data['sentiment']
            tone_guide = sentiment_data.get('tone_guide', '')
            depth = sentiment_data.get('explanation_depth', 'moderate')
            empathy_prefix = sentiment_data.get('empathy_level', '')

            sentiment_guidance = f"""

🎭 CUSTOMER EMOTIONAL STATE: {sentiment.upper()}
{tone_guide}

EXPLANATION DEPTH: {depth}
- simple: Use very basic language, avoid technical terms
- moderate: Balance detail with clarity
- detailed: Step-by-step explanations with examples
- brief: Concise and to the point

EMPATHY LEVEL: {empathy_prefix}
- Start your response with understanding and empathy
- {
    "Acknowledge their frustration and focus on solutions" if sentiment == 'frustrated'
    else "Be extra patient and break down concepts clearly" if sentiment == 'confused'
    else "Reinforce their positive experience warmly" if sentiment == 'satisfied'
    else ""
}
"""
            system_prompt = base_system_prompt + sentiment_guidance
        else:
            system_prompt = base_system_prompt

        user_message = f"""Context from documents:
{context}

User Question: {query}

Please provide a clear, accurate answer based on the context above."""

        messages = [{"role": "system", "content": system_prompt}]
        lang_override = self._build_language_override(response_language)
        if lang_override:
            messages.append({"role": "system", "content": lang_override})
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.chat.completions.create(
                model=self.settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
                messages=messages,
                temperature=0.3
                # max_completion_tokens=4000
            )

            answer = response.choices[0].message.content

            # Check if answer is None or empty
            if answer is None or answer == "":
                logger.warning("Empty response received from LLM")
                answer = "I apologize, but I wasn't able to generate a complete response. Please try rephrasing your question or asking something more specific."

            logger.info(f"Generated RAG response: {len(answer)} characters")
            return answer

        except Exception as e:
            logger.error(f"Failed to generate response with context: {e}", exc_info=True)
            raise

    def generate_banking_response(self, query: str, sentiment_data: Optional[Dict] = None, response_language: str = 'en') -> str:
        """
        Generate sentiment-aware response for general banking questions (no RAG)

        Args:
            query: User's banking question
            sentiment_data: Optional sentiment analysis results

        Returns:
            str: AI-generated response
        """
        base_system_prompt = """You are a friendly, trustworthy banking assistant for Indian customers.

Your job is to make banking feel simple, safe, and stress-free — like a knowledgeable friend helping out.
Assume common Indian banks such as SBI, HDFC Bank, ICICI Bank, Axis Bank, and similar RBI-regulated institutions.

Your guidance should always assume the Indian banking environment, including:
- RBI-regulated banks and financial institutions
- Public sector and private sector banks commonly used in India
- Indian documentation and compliance (Aadhaar, PAN, KYC)
- Indian digital payments and transfer systems (UPI, NEFT, IMPS, RTGS)

HOW TO RESPOND:
- Keep answers short and clear by default.
- Explain only what the user asks. Do not give extra information unless it's important.
- Use simple, everyday English (Indian-friendly).
- If something is confusing, explain it calmly and step-by-step.
- Avoid formal, policy-style language.
- Do not sound like a textbook, lawyer, or RBI circular.

LENGTH RULE (VERY IMPORTANT):
- Most answers should be under 120–150 words.
- If more detail is needed, give a brief summary first and let the user ask more.
- If the answer is getting long, stop and summarize.

TONE:
- Calm, reassuring, and human
- No fear, no pressure
- No heavy formatting
- At most one emoji, only if it feels natural

FORMATTING RULE (CRITICAL):
- NEVER use markdown symbols: **, ##, *, -, >, etc.
- Write clean plain text only. No bullet points with symbols.
- Use numbers (1. 2. 3.) for lists if needed.

LANGUAGE RULE (CRITICAL):
- Detect the language of the user's query.
- If the user writes in Hindi using Devanagari script, respond ENTIRELY in Hindi.
- If the user writes in Hinglish (Hindi words in Roman/English script like 'main', 'kaise', 'kya', 'mein', 'chahiye'), respond ENTIRELY in Hindi using Devanagari script.
- If the user writes in English, respond in English.
- Never mix scripts in your response.

SCOPE RULE (STRICT — follow this before answering anything):
- You ONLY answer questions about Indian banking, financial services, accounts, loans, UPI, NEFT, IMPS, RTGS, KYC, Aadhaar, PAN, and related financial topics.
- If the user asks about anything unrelated to banking or finance (research papers, science, technology, cooking, programming, relationships, etc.), politely decline: "I'm a banking assistant and can only help with banking and financial questions. Is there something about your account, loans, or financial services I can help with?"
- Do not answer off-topic questions even if you know the answer.
- If the user tries to use you as a general assistant, gently redirect them to banking topics.

Always end gently, for example:
"Tell me if you want this explained more simply or step-by-step."
"""

        # Add sentiment-specific guidance if sentiment is detected
        if sentiment_data and sentiment_data.get('sentiment') != 'neutral':
            sentiment = sentiment_data['sentiment']
            tone_guide = sentiment_data.get('tone_guide', '')
            depth = sentiment_data.get('explanation_depth', 'moderate')
            empathy_level = sentiment_data.get('empathy_level', '')

            sentiment_guidance = f"""

🎭 CUSTOMER EMOTIONAL STATE: {sentiment.upper()}
{tone_guide}

EXPLANATION DEPTH: {depth}
- simple: Use very basic language, avoid all technical terms, focus on actionable steps
- moderate: Balance detail with clarity
- detailed: Provide comprehensive step-by-step guidance with examples
- brief: Keep it concise and direct

EMPATHY LEVEL: {empathy_level}
- {
    "Begin with acknowledgment of their frustration. Be solution-focused and reassuring." if sentiment == 'frustrated'
    else "Be extra patient. Break down concepts into small, digestible pieces. Use analogies." if sentiment == 'confused'
    else "Acknowledge their positive sentiment. Maintain the warm, supportive tone." if sentiment == 'satisfied'
    else ""
}
"""
            system_prompt = base_system_prompt + sentiment_guidance
        else:
            system_prompt = base_system_prompt

        messages = [{"role": "system", "content": system_prompt}]
        lang_override = self._build_language_override(response_language)
        if lang_override:
            messages.append({"role": "system", "content": lang_override})
        messages.append({"role": "user", "content": query})

        try:
            response = self.client.chat.completions.create(
                model=self.settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
                messages=messages,
                temperature=0.5,
                # max_completion_tokens=4000
            )

            answer = response.choices[0].message.content

            # Check if answer is None or empty
            if answer is None or answer == "":
                logger.warning("Empty response received from LLM")
                answer = "I apologize, but I wasn't able to generate a complete response. Please try rephrasing your question or asking something more specific."

            logger.info(f"Generated general banking response: {len(answer)} characters")
            return answer

        except Exception as e:
            logger.error(f"Failed to generate banking response: {e}", exc_info=True)
            raise
