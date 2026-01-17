#!/bin/bash
# Install Bicameral Sync Daemon as macOS Launch Agent
# Auto-starts on login and keeps running

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLIST_PATH="$HOME/Library/LaunchAgents/com.bicameral.sync.plist"

echo "🔧 Installing Bicameral Sync Daemon service..."
echo ""

# Create plist
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.bicameral.sync</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>${SCRIPT_DIR}/redis_sync_daemon.py</string>
    </array>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>${HOME}/.bicameral/sync_stdout.log</string>

    <key>StandardErrorPath</key>
    <string>${HOME}/.bicameral/sync_stderr.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
    </dict>
</dict>
</plist>
EOF

echo "✅ Created plist: $PLIST_PATH"

# Load service
launchctl unload "$PLIST_PATH" 2>/dev/null || true
launchctl load "$PLIST_PATH"

echo "✅ Service loaded"
echo ""

# Check status
sleep 2
if launchctl list | grep -q "com.bicameral.sync"; then
    echo "✅ Service is running!"
    echo ""
    echo "📋 Service Info:"
    echo "   Label:  com.bicameral.sync"
    echo "   Status: $(launchctl list | grep com.bicameral.sync | awk '{print $1}')"
    echo "   Logs:   ~/.bicameral/sync_daemon.log"
    echo "           ~/.bicameral/sync_stdout.log"
    echo "           ~/.bicameral/sync_stderr.log"
    echo ""
    echo "🎯 Commands:"
    echo "   Stop:    launchctl stop com.bicameral.sync"
    echo "   Start:   launchctl start com.bicameral.sync"
    echo "   Restart: launchctl kickstart -k gui/$(id -u)/com.bicameral.sync"
    echo "   Unload:  launchctl unload $PLIST_PATH"
    echo "   Logs:    tail -f ~/.bicameral/sync_daemon.log"
else
    echo "❌ Service failed to start"
    echo ""
    echo "Check logs:"
    echo "  tail ~/.bicameral/sync_stderr.log"
    exit 1
fi
