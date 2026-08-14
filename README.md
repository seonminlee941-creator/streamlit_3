This is a demo project for circuit stream AI & Machine Learning Level 2 bootcamp in summer 2026 that combines several AI-powered tools using the Groq API.

Features:
1. Summarizer (txt/PDF file summary)
  Upload a .txt or .pdf file, or type/paste text directly
  Choose summary length (Short / Medium / Long)
  Download the summary as a .txt file
  Uploaded documents are chunked and stored in ChromaDB — ask a question and the app retrieves relevant chunks and answers using the LLM (RAG)
2. AI Chatbot
  Conversational chatbot powered by the Groq API
  Chat history persists for the duration of the session
3. Jackpot (Dice Game)
  Push the button and earn badges for special combinations:
  7-7-7: Jackpot
  Two 7s: Double Seven
  One 7
  Consecutive numbers (e.g. 4-5-6)
  All three digits match
  3-6-9: 369 badge
  Earned badges are saved for the session (no duplicate badges)

To go to the main page or to move though each features, use the side bar. 

Requirements:
1. You'll need a Groq API key. 
  For local development (.env): GROQ_API_KEY=your_api_key_here
  For Streamlit Cloud deployment (secrets.toml): GROQ_API_KEY = "your_api_key_here"
2. Installation
  Streamlit 
  Groq 
  ChromaDB
  pypdf
