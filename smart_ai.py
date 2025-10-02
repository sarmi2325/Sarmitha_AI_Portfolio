import os
import json
import numpy as np
import faiss
import pickle
from openai import OpenAI
from rank_bm25 import BM25Okapi
from deep_translator import GoogleTranslator
import requests
from typing import List, Tuple, Dict, Any
import time

class SmartAIPortfolio:
    def __init__(self):
        """Initialize the Smart AI Portfolio System with GPT-4o and BM25 fallback."""
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.db_path = "db/resume_sections.json"
        self.faiss_path = "db/resume_faiss.index"
        self.embeddings_path = "db/resume_embeddings.npy"
        self.bm25_path = "db/bm25.pkl"
        
        # Load or initialize components
        self.resume_data = self._load_resume_data()
        self.faiss_index = self._load_faiss_index()
        self.bm25_data = self._load_bm25_data()
        
        # System prompt (optimized and reduced)
        self.system_prompt = """You are Sarmitha, a 21-year-old AI/ML Engineer from Coimbatore, Tamil Nadu.

CORE IDENTITY:
- Name: Sarmitha, B.E. Electronics & Instrumentation (CGPA: 9.12)
- projects : Interactive Linear Algebra Toolkit, AI for Pneumonia Detection using Deep Learning, AI-Portfolio, TalentSynth-Resume Analyzer
- Hobbies: Sketching, painting, dancing, watching movies/dramas


RESPONSE RULES:
- Always respond in English, regardless of input language
- Maximum 4-5 short lines, use <br> for formatting
- Speak in first person as Sarmitha
- Be warm, professional, and helpful
- Use the retrieved context below to answer questions accurately
- If unsure, say: "I'm not sure about that. Feel free to ask about my work or projects! 😊"
- End with a friendly follow-up question

GUARDRAILS:
- Only discuss your background, skills, projects, education,internship, publications,hackathons,interests,achievements and goals
- Use the retrieved context to provide accurate information
- Never hallucinate information not in your resume or context
- Refuse to answer unrelated questions politely
- Stay in character as Sarmitha"""

    def _load_resume_data(self) -> Dict:
        """Load resume data from JSON file."""
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            pass
            return {}

    def _load_faiss_index(self):
        """Load FAISS index for semantic search."""
        try:
            if os.path.exists(self.faiss_path):
                return faiss.read_index(self.faiss_path)
        except Exception as e:
            pass
        return None

    def _load_bm25_data(self) -> Dict:
        """Load BM25 data for keyword fallback."""
        try:
            if os.path.exists(self.bm25_path):
                with open(self.bm25_path, 'rb') as f:
                    return pickle.load(f)
        except Exception as e:
            pass
        return {}


    def _detect_language(self, text: str) -> str:
        """Detect input language."""
        try:
            return GoogleTranslator(source='auto', target='en').detect(text)[0]
        except:
            return 'en'

    def _translate_to_english(self, text: str) -> str:
        """Translate text to English."""
        try:
            return GoogleTranslator(source='auto', target='en').translate(text)
        except:
            return text

    def _get_openai_embedding(self, text: str) -> np.ndarray:
        """Get OpenAI embedding for text."""
        try:
            response = self.openai_client.embeddings.create(
                model="text-embedding-3-large",  # Match the model used in notion.py
                input=text
            )
            return np.array(response.data[0].embedding, dtype="float32")
        except Exception as e:
            pass
            return None

    def _semantic_retrieve(self, query: str, top_k: int = 5) -> List[str]:
        """Retrieve relevant content using semantic search."""
        if not self.faiss_index or not self.bm25_data:
            return self._bm25_retrieve(query, top_k)

        # Get query embedding
        query_embedding = self._get_openai_embedding(query)
        if query_embedding is None:
            return self._bm25_retrieve(query, top_k)

        try:
            # Search FAISS index
            query_embedding = np.expand_dims(query_embedding, axis=0)
            scores, indices = self.faiss_index.search(query_embedding, top_k)
            
            # Get corresponding text chunks with scores
            flat_resume = self.bm25_data.get('flat_resume', [])
            
            results_with_scores = []
            for i, idx in enumerate(indices[0]):
                if 0 <= idx < len(flat_resume):
                    results_with_scores.append({
                        'content': flat_resume[idx]['content'],
                        'title': flat_resume[idx]['title'],
                        'score': scores[0][i]
                    })
            
            # Sort by relevance score (lower is better for L2 distance)
            results_with_scores.sort(key=lambda x: x['score'])
            
            return [result['content'] for result in results_with_scores]
        except Exception as e:
            pass
            return self._bm25_retrieve(query, top_k)

    def _bm25_retrieve(self, query: str, top_k: int = 5) -> List[str]:
        """Retrieve relevant content using BM25 keyword search."""
        if not self.bm25_data:
            return []

        try:
            bm25 = self.bm25_data.get('bm25')
            flat_resume = self.bm25_data.get('flat_resume', [])
            
            if not bm25 or not flat_resume:
                return []

            # Tokenize query and get scores
            tokenized_query = query.split()
            scores = bm25.get_scores(tokenized_query)
            
            # Get top-k results with scores
            top_indices = np.argsort(scores)[-top_k:][::-1]
            results_with_scores = []
            for idx in top_indices:
                if 0 <= idx < len(flat_resume):
                    results_with_scores.append({
                        'content': flat_resume[idx]['content'],
                        'title': flat_resume[idx]['title'],
                        'score': scores[idx]
                    })
            
            
            return [result['content'] for result in results_with_scores]
        except Exception as e:
            pass
            return []

    def _call_gpt4o(self, messages: List[Dict], context: str = "") -> str:
        """Call GPT-4o with fallback handling."""
        try:
            
            # Prepare messages with system prompt and retrieved context
            system_content = f"{self.system_prompt}"
            if context.strip():
                system_content += f"\n\nIMPORTANT: Use this retrieved context to answer questions accurately:\n{context}"
            
            system_message = {
                "role": "system", 
                "content": system_content
            }
            
            # Use last 5 messages for context (matching our chat_context maxlen=5)
            formatted_messages = [system_message] + messages[-5:]
            
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=formatted_messages,
                max_tokens=500,
                temperature=0.3
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            # Check if it's a quota issue
            if "quota" in str(e).lower() or "rate" in str(e).lower():
                return self._bm25_response(messages, context)
            else:
                return "I'm having trouble processing your request right now. Please try again! 😊"

    def _bm25_response(self, messages: List[Dict], context: str) -> str:
        """Generate response using BM25 retrieval when GPT quota is exhausted."""
        if not messages:
            return "Hi! I'm Sarmitha, an AI/ML Engineer. How can I help you today? 😊"
        
        # Get the latest user message
        user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_message = msg.get("content", "")
                break
        
        if not user_message:
            return "Hi! I'm Sarmitha, an AI/ML Engineer. How can I help you today? 😊"
        
        # Retrieve relevant context (reduced for lower context)
        relevant_content = self._bm25_retrieve(user_message, top_k=2)
        context_text = "\n".join(relevant_content) if relevant_content else ""
        
        # Simple response generation based on keywords
        user_lower = user_message.lower()
        
        if any(word in user_lower for word in ["hello", "hi", "hey", "greetings"]):
            return "Hi! 😊 I'm <b>Sarmitha</b> — an AI/ML enthusiast from Tamil Nadu.<br>Wanna explore my projects, skills, or just chat about tech? 🚀"
        
        elif any(word in user_lower for word in ["project", "work", "built", "developed"]):
            if context_text:
                return f"Here's what I've worked on:<br>{context_text[:200]}...<br>Want to know more about any specific project? 😊"
            else:
                return "I've worked on several AI/ML projects including Pneumonia Detection and Churn Prediction.<br>Which project interests you most? 🚀"
        
        elif any(word in user_lower for word in ["skill", "technology", "programming", "language"]):
            if context_text:
                return f"My technical skills include:<br>{context_text[:200]}...<br>Want to discuss any specific technology? 😊"
            else:
                return "I work with Python, TensorFlow, Keras, Flask, and various ML libraries.<br>What technology would you like to know about? 🚀"
        
        elif any(word in user_lower for word in ["contact", "email", "linkedin", "github"]):
            return "You can reach me at:<br>📧 sarmi8822@gmail.com<br>💼 linkedin.com/in/sarmithas<br>💻 github.com/sarmi2325<br>Let's connect! 😊"
        
        elif any(word in user_lower for word in ["about", "who", "background", "education"]):
            if context_text:
                return f"About me:<br>{context_text[:200]}...<br>Want to know more about my background? 😊"
            else:
                return "I'm a 21-year-old AI/ML Engineer from Coimbatore, Tamil Nadu.<br>Currently pursuing B.E. in Electronics & Instrumentation with 9.15 CGPA.<br>What would you like to know? 🚀"
        
        else:
            return "I'm not sure what you mean. 😊<br>Try asking about my projects, skills, or background!<br>How can I help you today? 🚀"

    def _calculate_context_coverage(self, query: str, retrieved_content: List[str]) -> float:
        """Calculate how much of the context is covered by the query."""
        if not retrieved_content:
            return 0.0
        
        # Simple coverage calculation based on retrieved content length
        total_content_length = sum(len(content) for content in retrieved_content)
        if total_content_length == 0:
            return 0.0
        
        # Normalize to 0-1 range with lower threshold
        coverage = min(total_content_length / 500, 1.0)  # Assume 500 chars = 100% coverage (lower threshold)
        return round(coverage, 2)

    def process_query(self, user_input: str, chat_history: List[Dict] = None) -> Tuple[str, float]:
        """Process user query and return response with context coverage."""
        if chat_history is None:
            chat_history = []
        
        # Detect language and translate to English
        user_lang = self._detect_language(user_input)
        user_msg_en = self._translate_to_english(user_input)
        
        # Retrieve relevant context (reduced from 5 to 3 for lower context)
        relevant_content = self._semantic_retrieve(user_msg_en, top_k=3)
        context_text = "\n".join(relevant_content) if relevant_content else ""
        
        
        # Calculate context coverage based on query count (5 queries = 100%)
        # Count user messages only (each query is a user message)
        user_messages = [msg for msg in chat_history if msg.get("role") == "user"]
        query_count = len(user_messages) + 1  # +1 for current query
        context_coverage = min(query_count / 5.0, 1.0)
        
        # Prepare messages for AI
        messages = chat_history + [{"role": "user", "content": user_msg_en}]
        
        # Get response from GPT-4o with fallback
        response = self._call_gpt4o(messages, context_text)
        
        # Add language note if needed
        if user_lang != "en":
            lang_note = f"<br><i>(I noticed you wrote in {user_lang.upper()}. I replied in English for clarity!)</i>"
            response = response + lang_note
        
        return response, context_coverage


    def _update_embeddings(self):
        """Update embeddings and indices when resume changes."""
        try:
            print("🔄 Starting embedding update process...")
            
            # Re-run the notion.py script to update embeddings
            import subprocess
            print("📥 Fetching latest data from Notion...")
            # Use the same Python interpreter as the current process
            import sys
            python_path = sys.executable
            result = subprocess.run([python_path, "notion.py"], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Notion.py executed successfully")
                print(f"Output: {result.stdout}")
            else:
                print(f"❌ Notion.py failed with return code: {result.returncode}")
                print(f"Error output: {result.stderr}")
                raise Exception(f"notion.py failed: {result.stderr}")
            
            # Reload components
            print("🔄 Reloading components...")
            self.resume_data = self._load_resume_data()
            print(f"✅ Resume data reloaded: {len(self.resume_data)} sections")
            
            self.faiss_index = self._load_faiss_index()
            if self.faiss_index:
                print(f"✅ FAISS index reloaded: {self.faiss_index.ntotal} vectors, {self.faiss_index.d} dimensions")
            else:
                print("⚠️ FAISS index failed to reload")
            
            self.bm25_data = self._load_bm25_data()
            if self.bm25_data:
                flat_resume = self.bm25_data.get('flat_resume', [])
                print(f"✅ BM25 data reloaded: {len(flat_resume)} chunks")
            else:
                print("⚠️ BM25 data failed to reload")
            
            print("✅ Embeddings updated successfully.")
        except Exception as e:
            print(f"⚠️ Failed to update embeddings: {e}")
            import traceback
            traceback.print_exc()

    def get_context_coverage(self, query: str, chat_history: List[Dict] = None) -> float:
        """Get context coverage for a query without processing."""
        if chat_history is None:
            chat_history = []
        # Count user messages only (each query is a user message)
        user_messages = [msg for msg in chat_history if msg.get("role") == "user"]
        query_count = len(user_messages) + 1  # +1 for current query
        return min(query_count / 5.0, 1.0)  # 5 queries = 100% coverage
