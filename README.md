# Inventory Reconciliation App

A lightweight Flask web application designed to help businesses reconcile their inventory. It ingests CSV exports of Opening Stock, Purchases, Sales, and Closing Stock, and automatically calculates variances to highlight inventory discrepancies. 

The application calculates expected inventory using the standard formula:
**`Opening Stock + Purchases - Sales = Expected Closing Stock`**

## Features

- **CSV Upload:** Bulk upload your inventory datasets via a simple web interface.
- **Automatic Reconciliation:** Automatically matches items by `Stock Code` and calculates variances.
- **Discrepancy Highlighting:** Easily identify items where the actual closing stock does not match the expected closing stock.
- **Data Export:** Export the full comparison report or just the mismatched items to a new CSV file.
- **SQLite Database:** Uses a lightweight, local SQLite database to temporarily store and process imports.
- **Docker Ready:** Easily deployable using Docker.

## Expected CSV Format

Because the app is designed to work with specific dataset exports, it expects columns to be in exact positions. **Headers are ignored**, but the data must be in the following columns (0-indexed):

| Dataset Type | Column A (Index 0) | Column B (Index 1) | Quantity Column |
| :--- | :--- | :--- | :--- |
| **Opening Stock** | Description | Stock Code | **Column H** (Index 7) |
| **Purchases** | Description | Stock Code | **Column G** (Index 6) |
| **Sales** | Description | Stock Code | **Column F** (Index 5) |
| **Closing Stock** | Description | Stock Code | **Column H** (Index 7) |

*Note: Blank rows and recognized header rows (e.g., containing "Stock Code" or "Description") are automatically skipped.*

## Running with Docker

Since the app is Docker-ready, you can easily build and run it without installing local Python dependencies.

1. **Build the Docker Image:**
   ```bash
   docker build -t inventory-reconciliation-app .
   ```

2. **Run the Container:**
   ```bash
   docker run -d -p 8000:8000 --name inventory-app inventory-reconciliation-app
   ```

3. **Persistent Database (Optional):**
   If you want the SQLite database to persist between container restarts, mount a volume:
   ```bash
   docker run -d -p 8000:8000 -v $(pwd)/data:/app/data -e INVENTORY_DB_PATH=/app/data/inventory.db --name inventory-app inventory-reconciliation-app
   ```

Access the app by navigating to `http://localhost:8000` in your browser.

## Running Locally (Without Docker)

### Prerequisites
- Python 3.9+
- `pip` (Python package manager)

### Setup Instructions

1. **Clone the repository and navigate to the directory.**
2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install required packages:**
   ```bash
   pip install Flask Werkzeug
   ```
4. **Run the application:**
   ```bash
   python app.py
   ```
5. **Access the application** at `http://localhost:8000`.

## Environment Variables

You can configure the application's behavior using the following environment variables:

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `PORT` | `8000` | The port the Flask server will listen on. |
| `FLASK_RUN_HOST` | `0.0.0.0` | The host IP to bind the server to. |
| `FLASK_DEBUG` | `0` | Set to `1` to enable Flask debug mode. |
| `INVENTORY_DB_PATH` | `./inventory.db` | Absolute or relative path to the SQLite database file. |

## Application Endpoints

- **`GET /`** - The main dashboard to upload files and view the reconciliation table.
- **`POST /upload`** - Endpoint that accepts the 4 required CSV files.
- **`GET /export`** - Downloads a CSV report of the entire reconciled inventory.
- **`GET /export-mismatches`** - Downloads a CSV report containing *only* items with a variance/discrepancy.