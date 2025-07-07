
#  Travel Buddy – AI-Powered Travel Assistant

Travel Buddy is an AI-powered assistant built with **Streamlit** and **LangChain**, designed to help travelers discover, plan, and personalize their journeys with ease.

---

## Features

 **Conversational AI Assistant**
- Ask questions about destinations, packing tips, logistics, and more.
- Combines retrieval-augmented generation (RAG) with your own travel guides (PDFs, Markdown).

 **Personalized Travel Profiles**
- Save user profiles with:
  - Name and email
  - Preferred budget and travel style
  - Favorite destinations
- Profiles automatically enrich your chat responses.

 **Dynamic Travel Summaries**
- Generate a **JSON summary** of each conversation.
- Summaries include trip interests, preferences, and questions.
- Summaries saved with timestamps for easy retrieval.

 **Web Search Integration**
- For up-to-date queries (weather, alerts, news), the assistant can query real-time sources.

 **Suggestions**
- After every response, receive tailored follow-up questions to keep planning simple.

 **Streamlit UI**
- Clean, side-by-side layout:
  - Chat on the right
  - Profile management & summaries on the left sidebar.

---

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/travel-buddy.git
   cd travel-buddy

2. Install dependencies:
  ```bash
   pip install -r requirements.txt
   ```
4. Set your API keys (create a .env or export them as environment variables):
   - OPENAI_API_KEY for GPT models.
   - TAVILY_API_KEY (optional) for web search.
   
##  Running the App
     streamlit run test.py
##  Future Ideas
  - Multi-user authentication and profile management
  - Rich trip itinerary generation
  - Booking integrations (flights, hotels)
  - Email export of summaries
  - Trip recommendation engine
   
