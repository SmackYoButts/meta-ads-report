#!/bin/bash
# Installs or uninstalls the ads report background service.
# Usage: ./install_service.sh [install|uninstall]

PLIST_SRC="/Users/mr.levin/Desktop/Claude Code/meta_ads_report/com.adsreport.weekly.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.adsreport.weekly.plist"

case "${1:-install}" in
  install)
    echo "Installing background service..."
    cp "$PLIST_SRC" "$PLIST_DEST"
    launchctl load "$PLIST_DEST"
    echo "✅ Service installed and started."
    echo "   It will automatically restart on login and run every Thursday at 09:00."
    echo ""
    echo "To check it's running:  launchctl list | grep adsreport"
    echo "To view logs:           tail -f \"$(dirname "$PLIST_SRC")/report.log\""
    ;;
  uninstall)
    echo "Removing background service..."
    launchctl unload "$PLIST_DEST" 2>/dev/null
    rm -f "$PLIST_DEST"
    echo "✅ Service removed."
    ;;
  *)
    echo "Usage: $0 [install|uninstall]"
    exit 1
    ;;
esac
