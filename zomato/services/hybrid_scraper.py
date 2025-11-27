import asyncio
import aiohttp
from bs4 import BeautifulSoup
from typing import List, Dict
import re
import json
import os
from googlesearch import search
import requests

# Fix for Groq compatibility
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except Exception as e:
    print(f"⚠️ Groq import error: {e}")
    GROQ_AVAILABLE = False

class HybridRestaurantFinder:
    """
    Uses Google Search to find real restaurants, then Groq AI for menu data
    """
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Initialize Groq with error handling
        self.groq_client = None
        if GROQ_AVAILABLE:
            try:
                api_key = os.getenv("GROQ_API_KEY")
                if api_key:
                    self.groq_client = Groq(
                        api_key=api_key,
                        timeout=30.0  # Add timeout
                    )
                    self.model = "llama-3.1-70b-versatile"
                    print("✅ Groq initialized successfully")
            except Exception as e:
                print(f"⚠️ Groq initialization failed: {e}")
                self.groq_client = None