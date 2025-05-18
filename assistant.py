import os
from typing import List, Dict, Optional

import streamlit as st
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationSummaryMemory
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain.agents import initialize_agent, AgentType
from langchain_core.runnables import RunnableLambda

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, UnstructuredMarkdownLoader
from langchain_community.tools.tavily_search import TavilySearchResults

from config import Config

import json


class TravelAssistant:
    def __init__(self):
        Config.validate_keys()
        self.llm = ChatOpenAI(
            model="gpt-4-turbo-preview", temperature=0.7, api_key=Config.OPENAI_API_KEY
        )
        self.embeddings = OpenAIEmbeddings(api_key=Config.OPENAI_API_KEY)
        self.memory = ConversationSummaryMemory(
            llm=self.llm,
            memory_key="chat_history",
            return_messages=True,
            input_key="question",
            output_key="answer",
        )
        self._setup_rag_chain()
        self._setup_web_search()
        self._setup_prompts()

    def _load_documents(self):
        loaders = [
            PyPDFLoader("data/Colette Worldwide Travel Guide 2021-2023.pdf"),
            PyPDFLoader("data/Colette Worldwide Travel Guide 2025-2026.pdf"),
            UnstructuredMarkdownLoader("data/budget_travel.md"),
        ]
        docs = []
        for loader in loaders:
            docs.extend(loader.load())

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        return text_splitter.split_documents(docs)

    def _setup_rag_chain(self):
        docs = self._load_documents()
        self.vectorstore = FAISS.from_documents(docs, self.embeddings)

        base_chain = ConversationalRetrievalChain.from_llm(
            self.llm,
            retriever=self.vectorstore.as_retriever(search_kwargs={"k": 4}),
            memory=self.memory,
            return_source_documents=True,
            verbose=False,
        )

        def transform_output(inputs):
            result = base_chain.invoke(inputs)
            return {"answer": result["answer"]}

        self.qa_chain = RunnableLambda(transform_output)
        self.base_qa_chain = base_chain

    def _setup_web_search(self):
        if Config.TAVILY_API_KEY:
            self.search_tool = TavilySearchResults(api_key=Config.TAVILY_API_KEY, k=3)
            self.search_agent = initialize_agent(
                [self.search_tool],
                self.llm,
                agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
                verbose=False,
            )
        else:
            self.search_agent = None

    def _setup_prompts(self):
        self.base_qa_chain.combine_docs_chain.llm_chain.prompt = PromptTemplate(
            input_variables=["context", "chat_history", "question"],
            template="""As a friendly Travel Buddy, use this context to give helpful advice:
            {context}
            Conversation history:
            {chat_history}

            Guidelines:
            1. Answer concisely using the context when possible
            2. If unsure, say: "Let me check online for the latest info..."
            3. For web searches, always include the source link so that user can visit the link
            4. End with one relevant follow-up question

            Current query: {question}
            Travel Buddy:""",
        )

    def _needs_web_search(self, query: str) -> bool:
        time_phrases = [
            "current",
            "today",
            "now",
            "live",
            "this week",
            "right now",
            "at the moment",
        ]
        info_types = [
            "weather",
            "forecast",
            "temperature",
            "open",
            "closed",
            "hours",
            "schedule",
            "status",
            "delay",
            "cancel",
            "advisory",
            "alert",
            "news",
            "update",
            "exchange rate",
        ]
        question_words = [
            "is there",
            "are there",
            "what's happening",
            "what are the current",
            "any recent",
        ]

        query_lower = query.lower()
        return (
            any(phrase in query_lower for phrase in time_phrases)
            or any(info in query_lower for info in info_types)
            or any(q_word in query_lower for q_word in question_words)
        )

    def generate_response(self, user_input: str) -> Dict:
        rag_result = self.qa_chain.invoke({"question": user_input})
        answer = rag_result["answer"]
        sources = self._extract_sources(rag_result)

        web_results = None
        if (
            "don't know" in answer.lower()
            or "unsure" in answer.lower()
            or "check online" in answer.lower()
        ) and self.search_agent:

            with st.spinner("🔍 Searching Web for the latest information..."):
                web_results = self.search_agent.run(user_input)
                answer += f"\n\nHere's what I found online:\n{web_results}"
                sources.append(
                    {"type": "web_search", "content": web_results[:500] + "..."}
                )

        suggestions = self._generate_followups(user_input, answer)

        return {
            "response": answer,
            "suggestions": suggestions,
            "sources": sources,
            "web_results": web_results,
        }

    def _generate_followups(self, question: str, answer: str) -> List[str]:
        prompt = f"""Generate 3-4 perfect follow-up questions for a travel assistant based on:

        **Conversation Context**:
        Q: {question}
        A: {answer}

        **Strict Rules**:
        1. Question Types (include ALL of these):
          a) 1 practical question (logistics/planning)
          b) 1 local insight question (hidden gems/culture)
          c) 1 time-sensitive question (current conditions)
          d) 1 personalized suggestion (based on answer)

        2. Formatting Requirements:
          - One question per line
          - Start each with "- " 
          - 6-12 words maximum
          - Include 1 relevant emoji in 2+ questions
          - Never repeat concepts

        3. Content Guidelines:
          - Must be answerable by either:
             - Your knowledge base
             - Real-time web search
          - Should advance trip planning
          - Avoid yes/no questions

        **Excellent Examples**:
          - What's the best month for hiking in USA? 
          - Where do locals eat near the Golden Temple?
          - Would a food tour or cooking class suit me better?

        Generate now:"""

        try:
            response = self.llm.invoke(prompt)
            questions = []
            for line in response.content.split("\n"):
                line = line.strip()
                if line.startswith(("-", "*", "•")):
                    line = line[1:].strip()
                if line and not line.startswith("`") and 6 <= len(line.split()) <= 12:
                    questions.append(line)

            if len(questions) >= 4:
                return questions[:4]
            return self._get_fallback_followups(question, answer)

        except Exception as e:
            print(f"Error generating follow-ups: {e}")
            return self._get_fallback_followups(question, answer)

    def _get_fallback_followups(self, question: str, answer: str) -> List[str]:
        return [
            "Would you like more details about this aspect?",
            "Should I check current conditions for this?",
            "What specific part interests you most?",
            "Would you prefer budget or luxury options?",
        ]

    def _extract_sources(self, result) -> List[Dict]:
        if "source_documents" not in result:
            return []

        sources = []
        for doc in result["source_documents"]:
            source = {
<<<<<<< HEAD
                "content": doc.page_content[:300] + "..." if len(doc.page_content) > 300 else doc.page_content,
                "source": os.path.basename(doc.metadata.get("source", "data")),
                "page": doc.metadata.get("page", "N/A")
=======
                "content": (
                    doc.page_content[:300] + "..."
                    if len(doc.page_content) > 300
                    else doc.page_content
                ),
                "source": os.path.basename(doc.metadata.get("source", "Travel Guide")),
                "page": doc.metadata.get("page", "N/A"),
>>>>>>> master
            }
            sources.append(source)
        return sources

    def generate_user_summary_json(self) -> Dict:
        Summary_prompt: f"""
You are Travel Buddy, an intelligent and friendly travel assistant.

Based on the full chat history below, summarize the user's travel preferences and questions
in a structured JSON format with keys:
- "destinations": list of places the user is interested in
- "interests": list of things they care about (e.g. food, hiking, budget travel)
- "constraints": list of constraints (dates, budget, safety, visa)
- "questions_asked": list of distinct questions the user asked
- "intent": what the user seems to be planning or deciding

Chat history:
{formatted_history}

Return **only** valid JSON with no extra text.
"""
        try:
            chat_history = self.memory.buffer_as_str
            prompt_text = summary_prompt.format(chat_history=chat_history)
            rsponse = self.llm.invoke(prompt_text)

            json_start = response.content.find("{")
            json_end = response.content.rfind("}") + 1
            json_text = response.content[json_start:json_end]

            return json.loads(json_text)

        except Exception as e:
            print(f"Error generating JSON")
            return {"error": str(e)}
