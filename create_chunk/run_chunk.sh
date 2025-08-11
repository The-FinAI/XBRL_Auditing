#!/bin/bash
# run_chunk.sh
# Script to run the GAAP Taxonomy Excel → JSONL chunks preprocessing

# Configure paths
EXCEL_PATH="GAAP_Taxonomy_2024.xlsx"
OUT_DIR="./us_gaap_2024_chunks"

# Ensure the output directory exists
mkdir -p "$OUT_DIR"

# Run the Python chunking script
python chunk_gaap_taxonomy.py \
  --excel "$EXCEL_PATH" \
  --out_dir "$OUT_DIR" \
  --every 100
