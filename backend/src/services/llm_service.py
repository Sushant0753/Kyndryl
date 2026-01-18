from openai import AzureOpenAI
from configs.config import AzureOpenAISettings
from lib.logger import logger


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

    def generate_response_with_context(self, query: str, context: str) -> str:
        """
        Generate response using RAG context

        Args:
            query: User's question
            context: Retrieved document context

        Returns:
            str: AI-generated response
        """
        system_prompt = """You are a friendly and trustworthy banking assistant who understands the Indian banking system well.

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

CUSTOMER FIRST:
- Point out fees, timelines, or documents only if relevant to the question.
- Mention common mistakes briefly if they matter.
- Respect Indian realities (branch visits, KYC, Aadhaar/PAN, digital confusion).

IMPORTANT RULE:
If the answer is getting long, STOP and summarize. Let the user ask follow-up questions.

Always end by gently offering help:
“Let me know if you want this explained more simply or step-by-step.”
 """

        user_message = f"""Context from documents:
{context}

User Question: {query}

Please provide a clear, accurate answer based on the context above."""

        try:
            response = self.client.chat.completions.create(
                model=self.settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message}
                ],
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

    def generate_banking_response(self, query: str) -> str:
        """
        Generate response for general banking questions (no RAG)

        Args:
            query: User's banking question

        Returns:
            str: AI-generated response
        """
        system_prompt = """You are a friendly, trustworthy banking assistant for Indian customers.

Your job is to make banking feel simple, safe, and stress-free — like a knowledgeable friend helping out.
Assume common Indian banks such as SBI, HDFC Bank, ICICI Bank, Axis Bank, and similar RBI-regulated institutions.

Your guidance should always assume the Indian banking environment, including:
- RBI-regulated banks and financial institutions
- Public sector and private sector banks commonly used in India
- Indian documentation and compliance (Aadhaar, PAN, KYC)
- Indian digital payments and transfer systems (UPI, NEFT, IMPS, RTGS)

HOW TO RESPOND:
- Keep answers short and clear by default.
- Explain only what the user asks. Do not give extra information unless it’s important.
- Use simple, everyday English (Indian-friendly).
- If something is confusing, explain it calmly and step-by-step.
- Avoid formal, policy-style language.
- Do not sound like a textbook, lawyer, or RBI circular.

LENGTH RULE (VERY IMPORTANT):
- Most answers should be under 120–150 words.
- If more detail is needed, give a brief summary first and let the user ask more.
- If the answer is getting long, stop and summarize.

DOCUMENT RULES:
- Use ONLY the information provided in the given documents.
- Do not add outside knowledge.
- If the document doesn’t contain the answer, say so clearly and politely.

TONE:
- Calm, reassuring, and human
- No fear, no pressure
- No heavy formatting
- At most one emoji, only if it feels natural

Always end gently, for example:
“Tell me if you want this explained more simply or step-by-step.”
 r."""

        try:
            response = self.client.chat.completions.create(
                model=self.settings.AZURE_OPENAI_CHAT_DEPLOYMENT,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query}
                ],
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
