import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
    MODEL_NAME = "gpt-3.5-turbo"
    TEMPERATURE = 0.7
    MAX_TOKENS = 100
    
    @staticmethod
    def validate_keys():
        if not Config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set in .env file")
        if not Config.TAVILY_API_KEY:
            print("Warning: TAVILY_API_KEY not set. Web search disabled")