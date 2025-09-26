#!/bin/bash
# Fix ZshRC Script - Apply Ultra-Minimal Configuration
# This script will backup current ~/.zshrc and apply ultra-minimal version

echo "🔧 FIXING ZSHRC CONFIGURATION"
echo "=" * 50

# Check if backup already exists
if [ -f ~/.zshrc.backup ]; then
    echo "📋 Backup already exists at ~/.zshrc.backup"
    read -p "Do you want to overwrite the backup? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Aborted. Please rename or move ~/.zshrc.backup first."
        exit 1
    fi
fi

# Backup current ~/.zshrc
echo "📦 Creating backup of current ~/.zshrc..."
cp ~/.zshrc ~/.zshrc.backup
echo "✅ Backup created at ~/.zshrc.backup"

# Apply ultra-minimal version
echo "🚀 Applying ultra-minimal ~/.zshrc..."
if [ -f ".zshrc.ultra-minimal" ]; then
    cp .zshrc.ultra-minimal ~/.zshrc
    echo "✅ Ultra-minimal ~/.zshrc applied!"
else
    echo "❌ Error: .zshrc.ultra-minimal not found!"
    exit 1
fi

echo ""
echo "🎉 ZSHRC FIX COMPLETE!"
echo "=" * 50
echo ""
echo "📋 WHAT HAPPENED:"
echo "  • Your slow ~/.zshrc has been backed up to ~/.zshrc.backup"
echo "  • Ultra-minimal ~/.zshrc has been applied"
echo "  • Terminal should now startup in <0.5 seconds"
echo ""
echo "🔄 NEXT STEPS:"
echo "  1. Restart your terminal/Cursor"
echo "  2. Terminal should be blazing fast now!"
echo "  3. Test with: gh auth status"
echo "  4. If you need heavy tools, they'll load when first used"
echo ""
echo "🛠️  TOOLS AVAILABLE:"
echo "  • gh, git, terraform (immediate)"
echo "  • gcloud, python, conda, docker (lazy-loaded)"
echo ""
echo "💡 TROUBLESHOOTING:"
echo "  • If issues: ./restore_backup.sh"
echo "  • Check cache: cache-status"
echo "  • Refresh keys: refresh-keys"
