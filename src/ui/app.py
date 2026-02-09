from datetime import datetime
from flask import Flask, render_template, request, jsonify
import os
import logging
from dataset_manager import DatasetManager
from constants import PHARMACY_ANOMALY_DATASET, PHARMACY_MALICIOUS_DATASET

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Configuration
AGENT_API_URL = os.getenv("AGENT_API_URL", "http://localhost:8001")

# Initialize dataset manager
# Reads ARIZE_API_KEY and ARIZE_SPACE_ID from environment variables
dataset_manager = DatasetManager()


# Initialize on startup - just log dataset status, don't sync
logger.info("Checking Arize datasets on startup...")
try:
    info = dataset_manager.get_dataset_info(
        [PHARMACY_ANOMALY_DATASET, PHARMACY_MALICIOUS_DATASET]
    )
    logger.info(f"Dataset info: {info}")
except Exception as e:
    logger.error(f"Failed to check datasets: {e}")


@app.route("/")
def index():
    """Serve the main UI page"""
    return render_template("index.html")


@app.route("/health")
def health():
    """Health check endpoint"""
    return jsonify({"status": "healthy"})


@app.route("/datasets/info")
def datasets_info():
    """Get information about Arize datasets"""
    try:
        info = dataset_manager.get_dataset_info(
            [
                PHARMACY_ANOMALY_DATASET,
                PHARMACY_MALICIOUS_DATASET,
            ]
        )
        return jsonify(info)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/datasets/sync", methods=["POST"])
def sync_datasets():
    """Manually trigger dataset synchronization from Arize to vector store"""
    try:
        # Sync both datasets
        anomaly_result = dataset_manager.sync_dataset_to_vector_store(
            "anomaly", PHARMACY_ANOMALY_DATASET
        )
        malicious_result = dataset_manager.sync_dataset_to_vector_store(
            "malicious", PHARMACY_MALICIOUS_DATASET
        )

        return jsonify(
            {
                "status": "success",
                "results": {"anomaly": anomaly_result, "malicious": malicious_result},
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/datasets/add", methods=["POST"])
def add_to_dataset():
    """Add an entry to a Phoenix dataset"""
    try:
        data = request.get_json()
        dataset_type = data.get("dataset_type")  # 'anomaly' or 'malicious'
        text = data.get("text")
        timestamp = data.get("timestamp")

        if not all([dataset_type, text, timestamp]):
            return jsonify({"error": "Missing required fields"}), 400

        # Map dataset_type to actual dataset name
        if dataset_type == "anomaly":
            dataset_name = PHARMACY_ANOMALY_DATASET
        elif dataset_type == "malicious":
            dataset_name = PHARMACY_MALICIOUS_DATASET
        else:
            return jsonify({"error": f"Invalid dataset_type: {dataset_type}"}), 400

        success = dataset_manager.add_to_dataset(dataset_name, text, timestamp)

        if success:
            return jsonify(
                {"status": "success", "message": f"Added to {dataset_type} dataset"}
            )
        else:
            return (
                jsonify({"status": "error", "error": "Failed to add to dataset"}),
                500,
            )

    except Exception as e:
        return jsonify({"status": "error", "error": str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
