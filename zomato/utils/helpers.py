from typing import List, Dict
import json

def format_restaurant_data(restaurants: List[Dict]) -> str:
    """
    Format restaurant data for display
    """
    return json.dumps(restaurants, indent=2, ensure_ascii=False)

def validate_city(city: str) -> bool:
    """
    Validate city name
    """
    if not city or len(city.strip()) < 2:
        return False
    return True

def validate_restrictions(restrictions: str) -> bool:
    """
    Validate dietary restrictions input
    """
    if not restrictions or len(restrictions.strip()) < 2:
        return False
    return True

def sanitize_input(text: str) -> str:
    """
    Sanitize user input
    """
    return text.strip().lower()