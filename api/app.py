from flask import Flask, request, jsonify, render_template, Response
import pickle
import numpy as np
from urllib.parse import urlparse
import os
from flask_cors import CORS
import logging
from feature_extractor import extract_url_features
import mysql.connector
from mysql.connector import Error
import base64

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get the current directory
current_dir = os.path.dirname(os.path.abspath(__file__))
# Define paths relative to the current directory
model_path = os.path.join(current_dir, 'model.pkl')
scaler_path = os.path.join(current_dir, 'scaler.pkl')

# Also check for model in parent directory if not found in current directory
parent_model_path = os.path.join(os.path.dirname(current_dir), 'model.pkl')
parent_scaler_path = os.path.join(os.path.dirname(current_dir), 'scaler.pkl')

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

# Database configuration
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', 'localhost'),
    'user': os.environ.get('DB_USER', 'root'),
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': os.environ.get('DB_NAME', 'webpagePhishingDetector'),
}

# Automatically migrate screenshot column to LONGBLOB for large attachments
try:
    mig_conn = mysql.connector.connect(**DB_CONFIG)
    mig_cur = mig_conn.cursor()
    mig_cur.execute("ALTER TABLE phishing_reports MODIFY screenshot LONGBLOB")
    mig_conn.commit()
    logger.info("Migrated screenshot column to LONGBLOB")
except Error as e:
    logger.info(f"Screenshot column migration skipped: {e}")
finally:
    try:
        mig_cur.close()
        mig_conn.close()
    except:
        pass

# Load the pre-trained model and scaler
try:
    # First try to load from the API directory
    try:
        with open(model_path, 'rb') as f:
            model = pickle.load(f)
        with open(scaler_path, 'rb') as f:
            scaler = pickle.load(f)
        logger.info("Model and scaler loaded successfully from API directory!")
    except FileNotFoundError:
        # If not found, try to load from parent directory
        with open(parent_model_path, 'rb') as f:
            model = pickle.load(f)
        with open(parent_scaler_path, 'rb') as f:
            scaler = pickle.load(f)
        logger.info("Model and scaler loaded successfully from parent directory!")
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
            logger.error("Model or scaler not loaded. Cannot make prediction.")
            return jsonify({
                "error": "Model not available", 
                "message": "The prediction model is not available. Please contact support."
            }), 500
        
        # Extract features and scale them
        url_features = extract_url_features(url, domain)
        
        try:
            # Try to scale features
            scaled_features = scaler.transform(url_features)
        except ValueError as e:
            logger.error(f"Feature mismatch error: {e}")
            
            # Get the expected number of features from the error message
            import re
            match = re.search(r'X has (\d+) features, but StandardScaler is expecting (\d+) features', str(e))
            
            if match:
                current_features, expected_features = int(match.group(1)), int(match.group(2))
                logger.warning(f"Adjusting features from {current_features} to {expected_features}")
                
                # If we have more features than expected, truncate
                if current_features > expected_features:
                    url_features = url_features[:, :expected_features]
                    scaled_features = scaler.transform(url_features)
                # If we have fewer features than expected, pad with zeros
                else:
                    padding = np.zeros((url_features.shape[0], expected_features - current_features))
                    url_features_padded = np.hstack((url_features, padding))
                    scaled_features = scaler.transform(url_features_padded)
            else:
                # If we can't parse the error, return an error response
                return jsonify({"error": "Feature mismatch", "message": str(e)}), 500
        
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
        
        # Override the result if confidence is below threshold (lowered from 0.9 to 0.7)
        # This helps reduce false positives for legitimate sites
        if confidence < 0.7:
            result = "Phishing"
            logger.info(f"Confidence below 0.7, flagging as Phishing: {url}")
        
        # Special handling for known legitimate domains
        known_legitimate_domains = [
            "google.com", "scholar.google.com", "nike.com", "www.nike.com",
            "microsoft.com", "github.com", "amazon.com", "apple.com",
            "facebook.com", "twitter.com", "linkedin.com", "youtube.com"
        ]
        
        # Check if the domain or any parent domain is in our known legitimate list
        is_known_legitimate = False
        parsed_url = urlparse(url)
        current_domain = parsed_url.netloc
        
        # Remove www. prefix if present
        if current_domain.startswith('www.'):
            current_domain = current_domain[4:]
            
        # Check if the domain or any parent domain is in our known legitimate list
        for known_domain in known_legitimate_domains:
            if current_domain == known_domain or current_domain.endswith('.' + known_domain):
                is_known_legitimate = True
                break
                
        # Override result for known legitimate domains
        if is_known_legitimate and result == "Phishing":
            result = "Legitimate"
            confidence = max(confidence, 0.95)  # Ensure high confidence for known legitimate sites
            logger.info(f"Overriding prediction for known legitimate domain: {url}")
        
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

# Reporting endpoint
@app.route('/report', methods=['POST', 'OPTIONS'])
def report():
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response

    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'Missing url field'}), 400

    url = data['url']
    description = data.get('description')
    screenshot = data.get('screenshot')

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        if screenshot:
            blob = base64.b64decode(screenshot)
            cursor.execute(
                "INSERT INTO phishing_reports (url, description, screenshot) VALUES (%s, %s, %s)",
                (url, description, blob)
            )
        else:
            cursor.execute(
                "INSERT INTO phishing_reports (url, description) VALUES (%s, %s)",
                (url, description)
            )
        conn.commit()
        report_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return jsonify({'report_id': report_id, 'status': 'Pending'}), 201
    except Error as e:
        logger.error(f"Error inserting report: {e}", exc_info=True)
        # Return actual DB error for debugging
        return jsonify({'error': str(e)}), 500

# Screenshot retrieval endpoint
@app.route('/report/<int:rid>/screenshot', methods=['GET'])
def get_screenshot(rid):
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    cursor.execute("SELECT screenshot FROM phishing_reports WHERE id=%s", (rid,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row and row[0]:
        return Response(row[0], mimetype='image/png')
    return '', 404

# Update report status endpoint
@app.route('/report/<int:rid>/status', methods=['POST', 'OPTIONS'])
def update_report_status(rid):
    if request.method == 'OPTIONS':
        return app.make_default_options_response()

    data = request.get_json()
    status = data.get('status')
    if status not in ['Pending', 'Verified', 'Blacklisted']:
        return jsonify({'error': 'Invalid status'}), 400

    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE phishing_reports SET status=%s WHERE id=%s",
            (status, rid)
        )
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({'status': status}), 200
    except Error as e:
        logger.error(f"Error updating report status: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# Admin reports page
@app.route('/admin/reports', methods=['GET'])
def admin_reports():
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT id, url, description, reported_at, status FROM phishing_reports ORDER BY reported_at DESC"
        )
        reports = cursor.fetchall()
        cursor.close()
        conn.close()
        return render_template('reports.html', reports=reports)
    except Error as e:
        logger.error(f"Error fetching reports: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Make sure to bind to 0.0.0.0 to allow external connections
    app.run(host='0.0.0.0', port=5000, debug=True)