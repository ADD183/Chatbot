
import os
import time
from typing import List, Optional
from dotenv import load_dotenv

try:
    from google import genai
    from google.genai import types
except Exception:
    genai = None
    types = None
import requests
import json
import logging
import re

# ---------------------------------------------------
# ENV SETUP
# ---------------------------------------------------
load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MOCK_GEMINI = os.getenv("MOCK_GEMINI", "false").lower() in ("1", "true", "yes")

# Safe defaults
EMBED_MODEL_DEFAULT = "models/gemini-embedding-001"
CHAT_MODEL_DEFAULT = "models/gemini-2.0-flash"

# Create client
client = None
if GEMINI_API_KEY and genai is not None:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
    except Exception as e:
        print("gemini_service: client init failed:", e)
        client = None

# If we successfully initialized a real genai client, always prefer real calls
EFFECTIVE_MOCK = True
if client is not None:
    EFFECTIVE_MOCK = False
else:
    EFFECTIVE_MOCK = MOCK_GEMINI

logger.info("gemini_service init: GEMINI_API_KEY set=%s, MOCK_GEMINI=%s, EFFECTIVE_MOCK=%s", bool(GEMINI_API_KEY), MOCK_GEMINI, EFFECTIVE_MOCK)


class GeminiService:

    def __init__(self):
        self.embed_model = "models/gemini-embedding-001"
        self.chat_model = "models/gemini-2.0-flash"
        self.max_retries = 3

    def _discover_models(self):
        """Discover available models and pick best defaults."""
        try:
            models = client.models.list()
            for m in models:
                name = m.name or ""
                # Pick latest flash for chat
                if "gemini-2.0-flash" in name:
                    self.chat_model = name
                # Pick embedding model
                if "embedding-001" in name:
                    self.embed_model = name
            logger.debug("Discovered: Chat=%s, Embed=%s", self.chat_model, self.embed_model)
        except Exception as e:
            logger.warning("Model discovery failed, using defaults: %s", e)

    def generate_embedding(self, text: str) -> List[float]:
        if EFFECTIVE_MOCK or not client:
            return [0.1] * 3072

        for attempt in range(self.max_retries):
            try:
                result = client.models.embed_content(
                    model=self.embed_model,
                    contents=text
                )
                return result.embeddings[0].values
            except Exception as e:
                logger.debug("Embedding retry %s: %s", attempt, e)
                time.sleep(1)
        raise Exception("Embedding failed after retries")

    def generate_query_embedding(self, query: str) -> List[float]:
        return self.generate_embedding(query)

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a batch of texts.

        Returns a list of embedding vectors (list of floats) aligned with `texts`.
        Falls back to per-item embedding calls on error.
        """
        if EFFECTIVE_MOCK or not client:
            return [[0.1] * 3072 for _ in texts]

        try:
            # Try batch call
            result = client.models.embed_content(
                model=self.embed_model,
                contents=texts
            )

            # result.embeddings should be a sequence
            embeddings = []
            for emb in result.embeddings:
                vals = getattr(emb, 'values', None)
                if vals is None:
                    # try dict access
                    vals = emb.get('values') if isinstance(emb, dict) else None
                embeddings.append([float(x) for x in vals])

            if len(embeddings) == len(texts):
                return embeddings
        except Exception as e:
            logger.warning("Batch embedding failed, falling back to single calls: %s", e)

        # Fallback: per-text embedding
        out = []
        for t in texts:
            out.append(self.generate_embedding(t))
        return out

    def generate_chat_response(
        self,
        user_message: str,
        context: Optional[List[str]] = None,
        chat_history: Optional[List[dict]] = None
    ) -> dict:
        if not user_message.strip():
            raise ValueError("Empty message")

        if EFFECTIVE_MOCK:
            return {"response": "Service unavailable: Gemini client not configured.", "tokens_used": 0}

        # ----------------------------
        # STRICT SYSTEM PROMPT
        # ----------------------------
        context_text = "\n\n".join(context) if context else "No relevant documents found."
        
        system_instruction = f"""
                You are a specialized Knowledge Base Assistant.

                STRICT RULES:
                1. Answer ONLY using the provided CONTEXT.
                2. If the answer is not in the context, say EXACTLY: "I don't have that information in the provided documents."
                3. DO NOT use outside knowledge.

                FORMATTING RULES (ENFORCED):
                - NEVER include time-of-day salutations or casual greetings at the start (e.g., "Good morning", "Hello", "Hi").
                - DO NOT include closing courtesies or generic closers such as "How may I assist you?" or "How can I help?".
                - When listing types, categories, features, advantages, steps, or differences → RETURN ONLY A BULLETED LIST when there are multiple items.
                    * Use short, concise bullet items (one sentence each).
                    * If a brief explanation is necessary, include at most one short sentence (no more than 20 words) before the bullets.
                - Avoid long paragraphs. If the answer is a single short sentence, return it as-is (no more than 25 words).
                - Use markdown-friendly bullets (`- `) and do not use emoji or decorative characters.
                - Do not invent examples or recommendations beyond the provided CONTEXT.

                CONTEXT:
                {context_text}
                """

        # ----------------------------
        # PREPARE MESSAGE HISTORY
        # ----------------------------
        contents = []
        if chat_history:
            # Add last 6 messages to contents in the new SDK format
            for msg in chat_history[-6:]:
                contents.append(types.Content(role="user", parts=[types.Part.from_text(text=msg['user'])]))
                contents.append(types.Content(role="model", parts=[types.Part.from_text(text=msg['assistant'])]))

        # Add current message
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

        # ----------------------------
        # CALL GENAI
        # ----------------------------
        for attempt in range(self.max_retries):
            # Try current model, then try a fallback on last attempts
            current_model = self.chat_model if attempt < 1 else "gemini-1.5-flash-latest"
            if attempt >= 2:
                 current_model = "gemini-pro"

            try:
                response = client.models.generate_content(
                    model=current_model,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.6,
                        top_p=0.9,
                        max_output_tokens=1500
                    )
                )
                
                # Post-process response to enforce no salutations/closers and prefer bullet formatting.
                resp_text = response.text or ""

                # 1) Remove leading salutations like "Good Morning", "Hello", etc.
                resp_text = re.sub(r'^(?:\s)*(?:good\s+morning|good\s+afternoon|good\s+evening|hello|hi|hey)[^\n\.\!\?]*[\.\!\?]?\s*', '', resp_text, flags=re.IGNORECASE)

                # 2) Remove trailing closers such as "How may I assist you?" or similar.
                resp_text = re.sub(r"\s*(?:How may I assist you(?: today)?\??|How can I help(?: you)?\??|How may I help\??|Let me know if you need anything\.?\s*)$", '', resp_text.strip(), flags=re.IGNORECASE)

                # 3) Normalize replacement characters and bold markers
                resp_text = resp_text.replace('\ufffd', '-')
                resp_text = resp_text.replace('**', '')

                # 4) Split into candidate sentences/lines and filter out short salutations
                parts = re.split(r'(?<=[\.\!\?])\s+(?=[A-Z0-9])', resp_text.strip()) if resp_text.strip() else []
                cleaned_parts = []
                for p in parts:
                    s = p.strip()
                    if not s:
                        continue
                    # Skip lines that are just greetings or closers
                    if re.match(r'^(?:good\s+morning|good\s+afternoon|good\s+evening|hello|hi|hey)\b', s, flags=re.IGNORECASE):
                        continue
                    if re.search(r'how (may|can) (i|we) (assist|help)', s, flags=re.IGNORECASE):
                        continue
                    cleaned_parts.append(s)

                # 5) If there are multiple substantive parts, produce bullets
                if len(cleaned_parts) >= 2:
                    bullets = '\n\n'.join(f'- {re.sub(r"^[\-*+\s]+", "", p)}' for p in cleaned_parts)
                    resp_text = bullets

                # 6) Final sanitization: normalize '*' to '-' list markers and remove stray markdown
                resp_text = re.sub(r'^\s*\*\s*', '- ', resp_text, flags=re.M)
                resp_text = resp_text.replace('\n* ', '\n- ')
                resp_text = resp_text.replace('**', '')
                resp_text = re.sub(r'\s+\n', '\n', resp_text)

                # 7) Small trim
                resp_text = resp_text.strip()

                return {
                    "response": resp_text,
                    "tokens_used": getattr(response.usage_metadata, 'total_token_count', 0)
                }
            except Exception as e:
                logger.warning("Chat fail on %s (attempt %s): %s", current_model, attempt, str(e))
                time.sleep(1)

        return {
            "response": "I'm having trouble connecting to my brain. This is usually due to a temporary API issue or an invalid model name. Please check the backend logs for details.",
            "tokens_used": 0
        }

gemini_service = GeminiService()
