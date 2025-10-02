# AI Portfolio
## Demo  
[AI Portfolio](https://aiportfoliowebsite-production.up.railway.app/))
![AI Portfolio Screenshot](https://github.com/sarmi2325/AI_Portfolio_Website/raw/main/Screenshot/Screenshot.png)
An advanced AI-powered portfolio system featuring hybrid Retrieval-Augmented Generation (RAG) for resume analysis and conversational interaction.
---
## Features

### 1. Hybrid RAG Search
- Combines OpenAI GPT-4o semantic search with FAISS vector similarity and BM25 keyword fallback for robust and accurate retrieval.
- Supports multilingual input with English-only response output.
- Handles retrieval gracefully by switching search strategies based on API quota availability.

### 2. Dynamic Resume Content Management
- Integrates with Notion API to fetch and sync resume content in real-time.
- Automatically regenerates embeddings and updates indices on content change.
- Admin authentication with secure multi-tap access for update operations.

### 3. Context-Aware Conversational AI
- Maintains a 5-message conversation history and visual context coverage indicator.
- Uses optimized system prompts and guardrails to ensure relevant, consistent responses.
- Provides fallback to BM25 keyword search when GPT quota is exceeded.

### 4. Full-Stack Architecture and Deployment
- Flask backend serving RESTful API endpoints with robust error handling.
- Responsive frontend with interactive project showcase modals.
- Production-ready deployment on Railway platform supporting cross-platform compatibility.
---
## Tech Stack

- **Backend & AI:** Flask, OpenAI GPT-4o, FAISS, BM25Okapi, Python
- **Data & Storage:** Notion API, JSON, SQLite
- **Frontend:** HTML5, CSS3, JavaScript, Font Awesome, Google Fonts
- **ML & Utilities:** NumPy, scikit-learn, deep-translator, rank-bm25
- **DevOps:** Railway deployment, Gunicorn, environment variable management
---
## Getting Started

### Prerequisites

- Python 3.x
- Virtual environment (venv or similar)
- API keys for OpenAI and Notion
---
### Installation

1. Clone the repository:
git clone https://github.com/yourusername/AI_Portfolio_Website.git
cd AI_Portfolio_Website

text

2. Create and activate a virtual environment:
python -m venv venv
source venv/bin/activate # Linux/macOS
venv\Scripts\activate # Windows

text

3. Install dependencies:
pip install -r requirements.txt

text

4. Create a `.env` file with your API keys and secrets:
OPENAI_API_KEY=your_openai_api_key
NOTION_API_KEY=your_notion_api_key
FLASK_ENV=development

text

---
## Deployment

This project is configured for deployment on Railway:

- Ensure environment variables are set in Railway project settings.
- Use the start command:
gunicorn app:app

text
- Railway handles containerization and cross-platform deployment.



---

Built with ❤️ by [Your Name]
