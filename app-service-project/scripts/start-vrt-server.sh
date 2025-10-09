#!/bin/bash
# VRT Server Script - Phương án A+
# Purpose: Build and serve app for visual regression testing
# Constitution compliance: HP-CS-02 (Plan A+ implementation)

set -e  # Exit on error

echo "🚀 Starting VRT server setup..."

# Step 1: Set all required environment variables for Vite build
export VITE_FIREBASE_API_KEY=test
export VITE_FIREBASE_AUTH_DOMAIN=test
export VITE_FIREBASE_PROJECT_ID=test
export VITE_FIREBASE_STORAGE_BUCKET=test
export VITE_FIREBASE_MESSAGING_SENDER_ID=test
export VITE_FIREBASE_APP_ID=test
export VITE_KNOWLEDGE_TREE_MOCK=true
export VITE_ENABLE_TEST_API=true

echo "✅ Environment variables set"

# Step 2: Build the application
echo "📦 Building application..."
npm run build -- --mode development

if [ $? -ne 0 ]; then
  echo "❌ Build failed!"
  exit 1
fi

echo "✅ Build completed successfully"

# Step 3: Start preview server
echo "🌐 Starting preview server on port 4173..."
npm run preview -- --host 127.0.0.1 --port 4173
