import logging
import random
import string
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

def is_valid_url(url):
    """
    Check if a URL is valid.
    
    Args:
        url (str): URL to check
        
    Returns:
        bool: True if valid, False otherwise
    """
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception as e:
        logger.error(f"Error validating URL: {e}")
        return False

def sanitize_input(input_string):
    """
    Sanitize input to prevent injection attacks.
    
    Args:
        input_string (str): Input to sanitize
        
    Returns:
        str: Sanitized input
    """
    if not input_string:
        return ""
    # Remove potentially dangerous characters
    sanitized = re.sub(r'[<>\'";()]', '', input_string)
    return sanitized

def generate_random_string(length=10):
    """
    Generate a random string of specified length.
    
    Args:
        length (int): Length of string to generate
        
    Returns:
        str: Random string
    """
    letters = string.ascii_letters + string.digits
    return ''.join(random.choice(letters) for i in range(length))

def format_prediction_result(prediction, confidence, url):
    """
    Format prediction result for client display.
    
    Args:
        prediction (str): Prediction result ('Phishing' or 'Legitimate')
        confidence (float): Confidence score
        url (str): URL that was checked
        
    Returns:
        dict: Formatted result
    """
    return {
        "result": prediction,
        "confidence": round(confidence, 4),
        "url": url,
        "timestamp": None  # Will be set by client
    }
