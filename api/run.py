import os
import sys
import logging
import subprocess
import time

logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_dependencies():
    """Check if required packages are installed and install them if not."""
    required_packages = ['flask', 'flask-cors', 'numpy', 'scikit-learn']
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            logger.info(f"✓ {package} is installed")
        except ImportError:
            logger.info(f"Installing {package}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                logger.info(f"✓ {package} installed successfully")
            except Exception as e:
                logger.error(f"Failed to install {package}: {e}")
                return False
    return True

def check_model_files():
    """Check if the model and scaler files exist and create them if not."""
    model_path = os.path.join("api", "model.pkl")
    scaler_path = os.path.join("api", "scaler.pkl")
    
    if not os.path.exists(model_path) or not os.path.exists(scaler_path):
        logger.info("Model or scaler file not found. Attempting to train a new model...")
        os.chdir("api")
        try:
            from model_trainer import train_model
            success = train_model()
            if not success:
                logger.warning("Model training failed, using fallback random predictions.")
            os.chdir("..")
        except Exception as e:
            logger.error(f"Error running model trainer: {e}")
            os.chdir("..")
    else:
        logger.info("Model and scaler files found.")

def run_api():
    """Run the Flask API."""
    try:
        logger.info("Starting Phishing Detector API...")
        logger.info("API will be available at http://localhost:5000")
        logger.info("Press Ctrl+C to stop the server")
        
        # Start the Flask app
        os.chdir("api")
        os.system(f"{sys.executable} app.py")
    except KeyboardInterrupt:
        logger.info("\nShutting down API server...")
    except Exception as e:
        logger.error(f"Error starting API: {e}")
        try:
            # Try an alternative port
            logger.info("Trying port 5001 instead...")
            os.environ['FLASK_APP'] = 'app.py'
            os.environ['FLASK_RUN_PORT'] = '5001'
            os.system(f"{sys.executable} -m flask run --host=0.0.0.0")
        except Exception as e2:
            logger.error(f"Alternative approach also failed: {e2}")

if __name__ == "__main__":
    logger.info("Initializing Phishing Detector...")
    
    if not check_dependencies():
        logger.error("Failed to install required dependencies. Exiting...")
        sys.exit(1)
    
    check_model_files()
    run_api()
