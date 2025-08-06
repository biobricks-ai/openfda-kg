#!/bin/bash

# Download script for files from NCBI PubChem and other sources
# This script downloads files to the ./stages/aux/ directory

set -e  # Exit on any error

# Define variables
TARGET_DIR="./stages/aux"

# Array of URLs to download
# Add more URLs here as needed
URLS=(
    "https://ftp.ncbi.nlm.nih.gov/pubchem/Compound/Extras/CID-Synonym-filtered.gz"
    # Add more URLs here, for example:
    # "https://example.com/file1.gz"
    # "https://example.com/file2.txt"
)

echo "Starting download of ${#URLS[@]} file(s)..."

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Function to download a single file
download_file() {
    local url="$1"
    local filename=$(basename "$url")
    local target_path="$TARGET_DIR/$filename"
    
    # Check if file already exists
    if [ -f "$target_path" ] || [ -f "${target_path%.gz}" ]; then
        echo "File already in specified directory: $TARGET_DIR"
        return 0
    fi
    
    # Download the file using wget or curl
    if command -v wget >/dev/null 2>&1; then
        wget -O "$target_path" "$url" -q --show-progress
    elif command -v curl >/dev/null 2>&1; then
        curl -L -o "$target_path" "$url"
    else
        return 1
    fi
    
    # Unzip .gz files if they exist
    if [[ "$filename" == *.gz ]]; then
        gunzip -f "$target_path"
    fi
}

# Download each file in the array
for url in "${URLS[@]}"; do
    if [ -n "$url" ]; then  # Skip empty lines
        download_file "$url"
    fi
done

echo "Download script completed and unzipped. Processed ${#URLS[@]} file(s)."
