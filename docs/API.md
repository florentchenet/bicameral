# Bicameral Quick Reference Card

## 🚀 One-Command Start

```bash
./scripts/start_bicameral.sh
```

Interactive menu for:
- Monitor collaboration
- View logs
- Send messages
- Check history
- Stop daemon

## 📨 Send Messages

```bash
# Claude
python3 scripts/bicameral_client.py claude <type> "message"

# Gemini
python3 scripts/bicameral_client.py gemini <type> "message"

# Types: status, task, response, question, urgent, demo, test
```

**Examples:**
```bash
python3 scripts/bicameral_client.py claude status "Quantum Mode fixed!"
python3 scripts/bicameral_client.py gemini response "Looks great!"
python3 scripts/bicameral_client.py claude urgent "Need help with X"
```

## 👀 Monitor

```bash
# Visual monitor (recommended)
python3 scripts/monitor_collab_v2.py

# View history
python3 -c "from scripts.bicameral_client import BicameralClient; [print(f\"{m['from']} → {m['message'][:50]}\") for m in BicameralClient('x').get_history(10)]"
```

## 🔄 Sync Daemon

```bash
# Start
python3 scripts/redis_sync_daemon.py &

# Check if running
ps aux | grep redis_sync_daemon

# View logs
tail -f ~/.bicameral/sync_daemon.log

# Stop
pkill -f redis_sync_daemon
```

## 🐳 Docker Services

```bash
# Start local Redis
docker compose up -d redis

# Check status
docker ps | grep redis

# View logs
docker logs -f minimal-redis-1
```

## 🔧 Troubleshooting

### Can't connect?
```bash
# Check Redis
redis-cli -h 100.111.230.6 -p 6379 -a bicameral_vps_secret ping

# Check Tailscale
tailscale status

# Check config
cat ~/.bicameral/.env
```

### Monitor not showing messages?
```bash
# Restart monitor (picks up new config)
# Ctrl+C then restart: python3 scripts/monitor_collab_v2.py
```

### Which Redis am I using?
```bash
# Client shows on connect:
python3 scripts/bicameral_client.py claude test "test"
# Shows: ✅ Connected: Local Redis (PRIMARY)
#    or: ✅ Connected: VPS via Tailscale (FALLBACK)
```

## 📁 Key Files

| File | Purpose |
|------|---------|
| `scripts/bicameral_client.py` | Universal client library |
| `scripts/monitor_collab_v2.py` | Visual collaboration monitor |
| `scripts/redis_sync_daemon.py` | Local ↔ VPS sync |
| `scripts/start_bicameral.sh` | One-command startup |
| `~/.bicameral/.env` | Unified configuration |
| `~/.bicameral/sync_daemon.log` | Sync daemon logs |
| `~/.bicameral/client.log` | Client logs |

## 🏗️ Architecture

```
Local Machine:
  Claude/Gemini → Local Redis → Sync Daemon → VPS Redis
                      ↓
                  Monitor

iOS/Remote:
  Claude Code → VPS Redis → Sync Daemon → Local Redis
```

## 💡 Tips

**Message History:**
```bash
redis-cli -h 100.111.230.6 -p 6379 -a bicameral_vps_secret \
  XREVRANGE bicameral:stream:collab + - COUNT 20
```

**Clear Messages (careful!):**
```bash
# Local
redis-cli -a bicameral_vps_secret XTRIM bicameral:stream:collab MAXLEN 0

# VPS
redis-cli -h 100.111.230.6 -p 6379 -a bicameral_vps_secret \
  XTRIM bicameral:stream:collab MAXLEN 0
```

**Backup Messages:**
```bash
redis-cli -h 100.111.230.6 -p 6379 -a bicameral_vps_secret \
  --rdb /tmp/bicameral_backup.rdb
```

## 🎯 Common Workflows

### Daily Work
```bash
# 1. Start system
./scripts/start_bicameral.sh

# 2. Choose option 1 (monitor)
# Keep this running in Terminal 1

# 3. Work normally
# Claude Code and Gemini send messages automatically
```

### Send Manual Message
```bash
python3 scripts/bicameral_client.py claude status "Starting work on feature X"
```

### Check What's Happening
```bash
# Option 1: Visual monitor (prettiest)
python3 scripts/monitor_collab_v2.py

# Option 2: Quick history (fastest)
python3 -c "from scripts.bicameral_client import BicameralClient; [print(m['message']) for m in BicameralClient('x').get_history(5)]"

# Option 3: Raw Redis (most detail)
redis-cli -h 100.111.230.6 -p 6379 -a bicameral_vps_secret XREVRANGE bicameral:stream:collab + - COUNT 5
```

### Sync Not Working?
```bash
# 1. Check daemon is running
ps aux | grep redis_sync_daemon

# 2. If not, start it
python3 scripts/redis_sync_daemon.py &

# 3. Check logs
tail -f ~/.bicameral/sync_daemon.log

# 4. Test sync
python3 scripts/bicameral_client.py claude test "sync test"
# Wait 3 seconds, then check VPS has it
```

## 📚 Full Documentation

- **UNIFIED-COMMUNICATION.md** - Communication system overview
- **LOCAL-FIRST-ARCHITECTURE.md** - Local-first design details
- **UNIFICATION-PLAN.md** - Original unification plan
- **COMPLETE-INFRASTRUCTURE-AUDIT-2026-01-17.md** - Infrastructure status

## 🆘 Emergency

**System completely broken?**
```bash
# 1. Stop everything
pkill -f redis_sync_daemon
docker compose down

# 2. Fresh start
docker compose up -d redis
python3 scripts/redis_sync_daemon.py &

# 3. Test
python3 scripts/bicameral_client.py claude test "recovery test"
python3 scripts/monitor_collab_v2.py
```

**Lost messages?**
Messages are persistent in Redis Streams - they don't disappear unless manually deleted.

```bash
# Check message count
redis-cli -h 100.111.230.6 -p 6379 -a bicameral_vps_secret \
  XLEN bicameral:stream:collab
```

## 📞 Message Format

```json
{
  "id": "uuid",
  "timestamp": "2026-01-17T11:15:45.261Z",
  "from": "claude",
  "to": "all",
  "type": "status",
  "message": "Your message here"
}
```

## 🎨 Monitor Colors

- **Magenta** 👤 = Claude
- **Blue** 🤖 = Gemini
- **Green** 🧠 = Daemon
- **White** ⚡ = Other

---

**Remember:** The system is local-first and resilient. Even if VPS is down, work continues locally!
