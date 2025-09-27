#!/bin/bash
# Test Terminal Functionality Script
# Run this after applying ultra-minimal ~/.zshrc

echo "🧪 TESTING TERMINAL FUNCTIONALITY"
echo "=" * 50

echo "⏱️  Testing shell startup time..."
time zsh -c "exit" 2>&1 | grep real | awk '{print "   Startup time: " $2}'

echo ""
echo "🔧 Testing essential tools..."
echo "   gh version: $(gh --version 2>/dev/null | head -1 || echo "❌ Not available")"
echo "   git version: $(git --version 2>/dev/null || echo "❌ Not available")"
echo "   terraform version: $(terraform version 2>/dev/null | head -1 || echo "❌ Not available")"
echo "   python3 version: $(python3 --version 2>/dev/null || echo "❌ Not available")"

echo ""
echo "🔑 Testing API keys (from cache)..."
echo "   OPENAI_API_KEY: $(if [ -n "$OPENAI_API_KEY" ]; then echo "✅ Set (length: ${#OPENAI_API_KEY})"; else echo "❌ Not set"; fi)"
echo "   QDRANT_API_KEY: $(if [ -n "$QDRANT_API_KEY" ]; then echo "✅ Set (length: ${#QDRANT_API_KEY})"; else echo "❌ Not set"; fi)"

echo ""
echo "🐌 Testing lazy-loaded tools (these will load when first used)..."
echo "   gcloud version: $(gcloud --version 2>/dev/null | head -1 || echo "⏳ Will load on first use")"
echo "   python version: $(python --version 2>/dev/null || echo "⏳ Will load on first use")"
echo "   docker version: $(docker --version 2>/dev/null || echo "⏳ Will load on first use")"

echo ""
echo "📊 Cache status:"
cache-status 2>/dev/null || echo "   ℹ️  Cache status function available after loading tools"

echo ""
echo "🎉 TEST COMPLETE!"
echo "💡 If all essential tools work and startup is fast, you're good to go!"
echo "🔧 If you need more tools: source zsh_helper.sh"
