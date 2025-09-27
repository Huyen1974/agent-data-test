#!/bin/bash
# Restore Backup ~/.zshrc Script

echo "🔄 RESTORING BACKUP ~/.zshrc"
echo "=" * 40

if [ -f ~/.zshrc.backup ]; then
    echo "📋 Found backup file at ~/.zshrc.backup"
    cp ~/.zshrc ~/.zshrc.before_restore
    cp ~/.zshrc.backup ~/.zshrc
    echo "✅ Restored original ~/.zshrc from backup"
    echo "💡 Previous ~/.zshrc saved as ~/.zshrc.before_restore"
    echo ""
    echo "⚠️  WARNING: Terminal may be slow again due to network calls"
    echo "🔧 To fix again: ./fix_zshrc.sh"
else
    echo "❌ No backup file found at ~/.zshrc.backup"
    echo "💡 Available files:"
    ls -la ~/.zshrc*
fi