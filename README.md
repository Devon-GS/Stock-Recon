# Inventory Usage App

A small Flask app backed by SQLite that compares:

`opening stock + purchases - sales`

against the uploaded closing stock file, grouped by stock code.

## CSV column mapping

The app reads the files by column position, using the following 1-based columns:

- Opening stock
  - Column 1: description
  - Column 2: stock code
  - Column 8: stock on hand amount
- Closing stock
  - Column 1: description
  - Column 2: stock code
  - Column 8: stock on hand amount
- Purchases
  - Column 1: description
  - Column 2: stock code
  - Column 7: quantity purchased
- Sales
  - Column 1: description
  - Column 2: stock code
  - Column 6: quantity sold

## Run locally

```bash
pip install -r requirements.txt
python app.py
```

Then open the Flask server in your browser and upload the four CSV files.

## Behavior

- The app replaces the current dataset when a new set of CSV files is uploaded.
- Rows are grouped by stock code.
- The comparison table shows opening, purchases, sales, expected closing, actual closing, and variance.
