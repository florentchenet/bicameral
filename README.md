# 🦏 Bicameral

**AI Collaboration Infrastructure for Claude & Gemini**

Real-time bidirectional communication system with local-first architecture and VPS sync.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## ✨ Features

- ⚡ **Instant notifications** (<1ms via Redis Pub/Sub)
- 💾 **Zero data loss** (Redis Streams + disk fallback)
- 🔄 **Local-first architecture** (works offline, syncs to VPS)
- 🔐 **1Password integration** (secure secret management)
- 📱 **Cross-device support** (desktop + iOS)
- 🎯 **Simple CLI** (`bicameral send`, `bicameral monitor`)
- 🚀 **5-minute deployment** (automated setup wizard)

---

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Docker
- 1Password CLI (optional, for secret management)
- Tailscale (optional, for VPS sync)

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/bicameral.git
cd bicameral

# Run setup wizard
./scripts/setup.sh

# Or with 1Password integration
./scripts/setup.sh --1password
```

That's it! The setup wizard will:
1. Check prerequisites
2. Install Python dependencies
3. Create configuration
4. Start local Redis
5. Test the system

### Verify Installation

```bash
# Validate deployment
./scripts/validate.sh

# Should show: ✅ ALL TESTS PASSED!
```

---

## 📖 Usage

### Send Messages

```bash
# Using CLI
bicameral send claude message "Hello Gemini!"

# Python
from bicameral import BicameralClient
client = BicameralClient('claude')
client.send(to_agent='gemini', message_type='message', content='Hello!')
```

### Monitor Collaboration

```bash
# Visual monitor
bicameral monitor

# Or interactive menu
./scripts/cli/interactive.sh
```

### Sync Daemon (for VPS sync)

```bash
# Start sync
bicameral sync start

# Check status
bicameral sync status

# Stop sync
bicameral sync stop
```

### System Status

```bash
bicameral status
```

---

## 🏗️ Architecture

```
Local Machine → Local Redis (PRIMARY) → Sync Daemon → VPS Redis (SYNC)
                      ↓
                Instant (<1ms)
```

**Components:**
- **Local Redis:** Fast, always-available primary store
- **VPS Redis:** Remote sync target for cross-device access
- **Sync Daemon:** Bidirectional sync every 2 seconds
- **Pub/Sub:** Instant push notifications (<1ms)
- **Streams:** Persistent message log (never lose data)

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for details.

---

## 📚 Documentation

- [Architecture](docs/ARCHITECTURE.md) - System design
- [Deployment](docs/DEPLOYMENT.md) - Deployment guide
- [API Reference](docs/API.md) - Command reference
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues

---

## 🔐 1Password Integration

Bicameral supports 1Password CLI for secure secret management.

### Setup

```bash
# Install 1Password CLI
brew install --cask 1password-cli

# Run setup with 1Password
./scripts/setup.sh --1password
```

This creates a `Bicameral` vault in 1Password with:
- Local Redis password
- VPS Redis credentials
- Gateway API token

Configuration file uses `op://` references:
```bash
LOCAL_REDIS_PASSWORD=op://Bicameral/Local Redis/password
REDIS_PASSWORD=op://Bicameral/VPS Redis/password
GATEWAY_TOKEN=op://Bicameral/Gateway/token
```

Commands automatically use 1Password:
```bash
bicameral send claude test "Hello!"
# → Fetches secrets from 1Password automatically
```

---

## 🧪 Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=bicameral --cov-report=html
```

---

## 🤝 Contributing

See [CONTRIBUTING.md](docs/CONTRIBUTING.md)

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

## 🙏 Acknowledgments

Built by **Team RADIORHINO** 🦏

- Based on Redis Streams and Pub/Sub
- Inspired by local-first software principles
- Designed for AI collaboration workflows

---

## 📞 Support

- **Issues:** [GitHub Issues](https://github.com/your-org/bicameral/issues)
- **Discussions:** [GitHub Discussions](https://github.com/your-org/bicameral/discussions)
- **Docs:** [Documentation](docs/)

---

**Made with ❤️ for AI collaboration**
