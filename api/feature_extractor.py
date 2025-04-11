import numpy as np
from urllib.parse import urlparse
import re
import logging

logger = logging.getLogger(__name__)

def extract_url_features(url, domain=None):
    """
    Extract features from the URL for phishing detection.
    
    Args:
        url (str): The URL to analyze
        domain (str, optional): The domain name. If not provided, it will be extracted.
        
    Returns:
        numpy.ndarray: Array of features
    """
    try:
        if domain is None:
            domain = urlparse(url).netloc
            
        features = []
        
        # 1. URL length
        features.append(len(url))
        
        # 2. Number of dots in URL
        features.append(url.count('.'))
        
        # 3. HTTPS check
        features.append(1 if 'https' in url else 0)
        
        # 4. Special characters count (excluding dots)
        features.append(sum(1 for char in url if not char.isalnum() and char != '.'))
        
        # 5. Digits count in URL
        features.append(sum(c.isdigit() for c in url))
        
        # 6. If domain has IP
        features.append(1 if any(c.isdigit() for c in domain) else 0)
        
        # 7. Domain length
        features.append(len(domain))
        
        # 8. Number of subdomains
        features.append(domain.count('.'))
        
        # 9. URL shortening service check
        features.append(1 if 'bit.ly' in url or 'goo.gl' in url or 't.co' in url or 'tinyurl' in url else 0)
        
        # 10. Obfuscation ratio (special chars / length)
        features.append(sum(1 for char in url if not char.isalnum() and char != '.') / len(url) if len(url) > 0 else 0)
        
        # Additional features for better detection

        # 11. Number of hyphens in domain
        features.append(domain.count('-'))
        
        # 12. Length of longest word in domain
        domain_without_tld = domain.split('.')
        domain_words = re.split(r'[^a-zA-Z]', domain_without_tld[0]) if domain_without_tld else []
        longest_word = max([len(word) for word in domain_words]) if domain_words else 0
        features.append(longest_word)
        
        # 13. Presence of '@' symbol in URL
        features.append(1 if '@' in url else 0)
        
        # 14. Presence of double slash not in protocol
        double_slash_position = url.find('//')
        features.append(1 if double_slash_position > 7 or (double_slash_position > -1 and 'http' not in url[:double_slash_position]) else 0)
        
        # 15. Presence of suspicious TLD
        suspicious_tlds = ['.xyz', '.top', '.club', '.online', '.site']
        features.append(1 if any(tld in domain for tld in suspicious_tlds) else 0)
        
        logger.debug(f"Extracted features: {features}")
        return np.array(features).reshape(1, -1)
        
    except Exception as e:
        logger.error(f"Error extracting features: {e}", exc_info=True)
        # Return default features in case of error
        return np.zeros((1, 15))
