from flask import Flask, request, jsonify
import pickle
import numpy as np
from urllib.parse import urlparse
import os
from flask_cors import CORS
import logging
import sys

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add api directory to the path so we can import modules from it
sys.path.append(os.path.join(os.path.dirname(__file__), 'api'))

try:
    from feature_extractor import extract_url_features
except ImportError as e:
    logger.error(f"Error importing feature_extractor: {e}")
    # Define a placeholder function if import fails
    def extract_url_features(url, domain=None):
        logger.warning("Using placeholder feature extractor")
        return np.zeros((1, 15))

# Define paths relative to the current directory
model_path = os.path.join(os.path.dirname(__file__), 'api', 'model.pkl')
scaler_path = os.path.join(os.path.dirname(__file__), 'api', 'scaler.pkl')

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Load the pre-trained model and scaler
try:
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)
    logger.info("Model and scaler loaded successfully!")
except Exception as e:
    logger.error(f"Error loading model or scaler: {e}")
    # Initialize empty model and scaler for demonstration if loading fails
    model = None
    scaler = None

@app.route('/predict', methods=['POST'])
def predict():
    try:
        # Get the URL from the POST request
        data = request.get_json()
        
        if not data or 'url' not in data:
            logger.warning("Missing 'url' in request body")
            return jsonify({"error": "Missing 'url' in request body"}), 400
            
        url = data['url']
        logger.debug(f"Received URL for analysis: {url}")
        
        domain = urlparse(url).netloc
        
        # Handle invalid URLs
        if not domain:
            logger.warning(f"Invalid URL: {url}")
            return jsonify({"error": "Invalid URL"}), 400
        
        # For demonstration, if model failed to load
        if model is None or scaler is None:
            # Return a random prediction for demonstration
            import random
            result = "Phishing" if random.random() > 0.7 else "Legitimate"
            logger.warning("Using random prediction (model not loaded)")
            return jsonify({
                "result": result, 
                "note": "Using random prediction (model not loaded)",
                "confidence": random.random()
            })
        
        # Extract features and scale them
        url_features = extract_url_features(url, domain)
        scaled_features = scaler.transform(url_features)
        
        # Make the prediction
        prediction = model.predict(scaled_features)
        
        # Get prediction probability if available
        confidence = 0.95  # Default high confidence
        if hasattr(model, 'predict_proba'):
            try:
                proba = model.predict_proba(scaled_features)
                # Get the probability of the predicted class
                confidence = float(proba[0][int(prediction[0])])
            except Exception as e:
                logger.warning(f"Could not get prediction probability: {e}")
        
        # Return result based on the prediction
        result = "Legitimate" if prediction[0] == 1 else "Phishing"
        logger.info(f"Prediction for {url}: {result} with confidence {confidence:.2f}")
        
        return jsonify({
            "result": result,
            "confidence": confidence,
            "url": url
        })
    
    except Exception as e:
        logger.error(f"Error in prediction: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Add a simple health check endpoint
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "API is running", 
        "endpoints": ["/predict"],
        "model_loaded": model is not None,
        "scaler_loaded": scaler is not None
    })

if __name__ == '__main__':
    # Make sure to bind to 0.0.0.0 to allow external connections
    app.run(host='0.0.0.0', port=5000, debug=True)