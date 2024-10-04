#!/bin/bash

# Script to create a Lambda layer for the requests library

# Create directory structure
mkdir -p layer/python

# Change to the layer directory
cd layer

# Install requests library
pip install -t python requests

# Create zip file
zip -r12 layers.zip python

echo "Lambda layer created successfully: layers.zip"
echo "You can now upload this file to your Lambda function."

