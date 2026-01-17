# Bicameral Deployment Quickstart

Deploy the Bicameral collaboration system on a new machine in 5 minutes.

---

## One-Command Setup

```bash
# Clone repository
git clone https://github.com/your-org/rapid-nova.git
cd rapid-nova

# Run automated setup
./scripts/setup_bicameral.sh
```

That's it! The setup wizard will:
1. Check prerequisites (Python, Docker)
2. Install dependencies (redis, python-dotenv, rich)
3. Create configuration (~/.bicameral/.env)
4. Generate secure passwords
5. Start local Redis
6. Test the system
7. Show next steps

**Time:** ~3-5 minutes

---

## Manual Setup (If Needed)

### Prerequisites

- Python 3.10+
- Docker
- Tailscale (optional, for VPS sync)

### Steps

```bash
# 1. Install Python packages
pip install redis python-dotenv rich

# 2. Create directories
mkdir -p ~/.bicameral/{bin,config,logs,notifications}

# 3. Create configuration
cat > ~/.bicameral/.env << 'EOF'
LOCAL_REDIS_HOST=localhost
LOCAL_REDIS_PORT=6379
LOCAL_REDIS_PASSWORD=$(openssl rand -base64 32)

REDIS_HOST=100.111.230.6
REDIS_PORT=6379
REDIS_PASSWORD=bicameral_vps_secret

GATEWAY_API=https://api.rhncrs.com
GATEWAY_TOKEN=$(openssl rand -hex 32)

STREAM_KEY=bicameral:stream:collab
EOF

# 4. Start Redis
docker run -d \
  --name bicameral-redis \
  --restart unless-stopped \
  -p 6379:6379 \
  redis:7-alpine \
  redis-server --appendonly yes --requirepass "$(grep LOCAL_REDIS_PASSWORD ~/.bicameral/.env | cut -d= -f2)"

# 5. Test
python3 scripts/bicameral_client.py claude test "Hello!"
```

---

## Validation

```bash
# Run deployment validator
./scripts/validate_deployment.sh

# Expected output:
# ✅ Passed: 10/10
# ✅ ALL TESTS PASSED!
```

---

## Quick Commands

### Send Message
```bash
python3 scripts/bicameral_client.py claude message "Hello Gemini!"
```

### Start Monitor
```bash
python3 scripts/monitor_collab_v2.py
```

### Start Sync Daemon (for VPS sync)
```bash
python3 scripts/redis_sync_daemon.py &
```

### Interactive Menu
```bash
./scripts/start_bicameral.sh
```

---

## Troubleshooting

### "Could not connect to Redis"
```bash
# Check if Redis is running
docker ps | grep redis

# Start if not running
docker start bicameral-redis
```

### "Python package not found"
```bash
pip install redis python-dotenv rich
```

### "Permission denied"
```bash
chmod +x scripts/*.sh scripts/*.py
```

---

## Next Steps

1. **Start sync daemon** (for VPS sync):
   ```bash
   python3 scripts/redis_sync_daemon.py &
   ```

2. **Install auto-start service** (optional):
   ```bash
   ./scripts/install_sync_service.sh
   ```

3. **Read documentation**:
   - Full audit: `BICAMERAL-INFRASTRUCTURE-AUDIT-2026-01-17.md`
   - Quick reference: `QUICK-REFERENCE.md`
   - Architecture: `LOCAL-FIRST-ARCHITECTURE.md`

---

## System Requirements

**Minimum:**
- 2 GB RAM
- 1 GB disk space
- Python 3.10+
- Docker

**Recommended:**
- 4 GB RAM
- 5 GB disk space (for logs/data)
- Python 3.12+
- Docker + Docker Compose
- Tailscale (for VPS sync)

---

## Architecture Overview

```
┌─────────────────────┐
│  Your Machine       │
│  ┌───────────────┐  │
│  │ Claude/Gemini │  │
│  └───────┬───────┘  │
│          ↓          │
│  ┌───────────────┐  │
│  │ Local Redis   │  │
│  │ (PRIMARY)     │  │
│  └───────┬───────┘  │
│          ↓          │
│  ┌───────────────┐  │
│  │ Sync Daemon   │  │
│  └───────┬───────┘  │
└──────────┼──────────┘
           ↓ Tailscale
┌──────────┼──────────┐
│  VPS     ↓          │
│  ┌───────────────┐  │
│  │ VPS Redis     │  │
│  │ (SYNC TARGET) │  │
│  └───────────────┘  │
└─────────────────────┘
```

**Features:**
- ⚡ <1ms notifications (Pub/Sub)
- 💾 Zero data loss (Streams + disk fallback)
- 🔄 Automatic sync (every 2 seconds)
- 🛡️ Resilient (works offline)
- 📱 Cross-device (iOS, desktop)

---

**Version:** 2.0 (Local-First)
**Status:** ✅ Production Ready
**Support:** See BICAMERAL-INFRASTRUCTURE-AUDIT-2026-01-17.md
