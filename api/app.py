from flask import Flask, request, jsonify, render_template
import pickle
import numpy as np
from urllib.parse import urlparse
import os
from flask_cors import CORS
import logging
from feature_extractor import extract_url_features

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))

# Define paths relative to the current directory
model_path = os.path.join(current_dir, 'model.pkl')
scaler_path = os.path.join(current_dir, 'scaler.pkl')

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev_key_only")

# Enable CORS with specific settings
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Accept"]
    }
})

# Load the pre-trained model and scaler
try:
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    with open(scaler_path, 'rb') as f:
        scaler = pickle.load(f)
    logger.info("Model and scaler loaded successfully!")
except Exception as e:
    logger.error(f"Error loading model or scaler: {e}")
    model = None
    scaler = None

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/predict', methods=['POST', 'OPTIONS'])
def predict():
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response

    try:
        logger.debug("Received request headers: %s", request.headers)
        logger.debug("Received request data: %s", request.get_data())
        
        # Get the URL from the POST request
        data = request.get_json()
        logger.debug("Parsed JSON data: %s", data)
        
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
        
        # Determine the result based on the prediction
        result = "Legitimate" if prediction[0] == 1 else "Phishing"
        
        # Override the result if confidence is below 0.9
        if confidence < 0.9:
            result = "Phishing"
            logger.info(f"Confidence below 0.9, flagging as Phishing: {url}")
        
        response_data = {
            "result": result,
            "confidence": confidence,
            "url": url
        }
        logger.info(f"Prediction for {url}: {result} with confidence {confidence:.2f}")
        logger.debug(f"Sending response: {response_data}")
        
        return jsonify(response_data)
    
    except Exception as e:
        logger.error(f"Error in prediction: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Make sure to bind to 0.0.0.0 to allow external connections
    app.run(host='0.0.0.0', port=5000, debug=True)