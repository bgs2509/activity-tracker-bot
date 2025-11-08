# Prerequisites

**Time**: 5 minutes

**Goal**: Ensure you have all required tools installed.

## Required Software

### 1. Docker & Docker Compose

**Why**: All services run in Docker containers.

**Installation**:

**Linux** (Ubuntu/Debian):
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add your user to docker group
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin

# Verify
docker --version  # Should be 24.0+
docker compose version  # Should be 2.20+
```

**macOS**:
```bash
# Install Docker Desktop
brew install --cask docker

# Start Docker Desktop app

# Verify
docker --version
docker compose version
```

**Windows**:
- Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Verify in PowerShell: `docker --version`

### 2. Git

**Why**: Version control and submodules.

**Installation**:

**Linux**:
```bash
sudo apt-get update
sudo apt-get install git

# Verify
git --version  # Should be 2.40+
```

**macOS**:
```bash
brew install git

# Verify
git --version
```

**Windows**:
- Download and install [Git for Windows](https://git-scm.com/download/win)
- Verify: `git --version`

### 3. Make

**Why**: Convenient development commands.

**Installation**:

**Linux**:
```bash
sudo apt-get install build-essential

# Verify
make --version
```

**macOS**:
```bash
# Already installed with Xcode Command Line Tools
xcode-select --install

# Verify
make --version
```

**Windows**:
```bash
# Install via Chocolatey
choco install make

# Or use Git Bash (comes with Git for Windows)
```

### 4. Text Editor / IDE

**Recommended**:
- **VSCode** - Best Python support, Docker integration
- **PyCharm** - Professional Python IDE
- **Cursor** - AI-powered IDE (built on VSCode)

**VSCode Extensions** (recommended):
```bash
code --install-extension ms-python.python
code --install-extension ms-azuretools.vscode-docker
code --install-extension ms-python.vscode-pylance
code --install-extension charliermarsh.ruff
```

## Optional Tools

### 1. Python 3.12 (optional - for local development)

**Why**: Run tests locally without Docker.

**Installation**:

**Linux**:
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt-get update
sudo apt-get install python3.12 python3.12-venv

# Verify
python3.12 --version
```

**macOS**:
```bash
brew install python@3.12

# Verify
python3.12 --version
```

### 2. PostgreSQL Client (optional - for database inspection)

**Why**: Inspect database directly.

**Installation**:

**Linux**:
```bash
sudo apt-get install postgresql-client

# Verify
psql --version
```

**macOS**:
```bash
brew install postgresql@15

# Verify
psql --version
```

**Note**: You can also use `make shell-db` without installing locally.

### 3. Redis CLI (optional - for FSM inspection)

**Why**: Inspect FSM state in Redis.

**Installation**:

**Linux**:
```bash
sudo apt-get install redis-tools

# Verify
redis-cli --version
```

**macOS**:
```bash
brew install redis

# Verify
redis-cli --version
```

**Note**: You can use `docker exec -it tracker_redis redis-cli` without installing locally.

## Telegram Account

**Why**: You need a Telegram bot token to run the project.

**Steps**:

1. Open Telegram
2. Search for `@BotFather`
3. Send `/newbot`
4. Follow instructions to create bot
5. Copy bot token (format: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`)
6. Keep token safe - you'll need it in setup

**Example**:
```
@BotFather: Alright, a new bot. How are we going to call it?
You: Activity Tracker Bot Test

@BotFather: Good. Now let's choose a username.
You: activity_tracker_test_bot

@BotFather: Done! Your token is:
1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
```

**Security**: NEVER commit bot token to git!

## System Requirements

**Minimum**:
- RAM: 4 GB
- Disk: 5 GB free space
- CPU: 2 cores

**Recommended**:
- RAM: 8 GB
- Disk: 10 GB free space
- CPU: 4 cores

## Verification Checklist

Check all required tools are installed:

```bash
# Docker
docker --version               # ✅ Should output 24.0+
docker compose version         # ✅ Should output 2.20+

# Git
git --version                  # ✅ Should output 2.40+

# Make
make --version                 # ✅ Should output GNU Make

# Telegram Bot Token
echo $TELEGRAM_BOT_TOKEN       # ✅ Should have bot token ready
```

## Troubleshooting

### Docker Permission Denied

**Error**:
```
Got permission denied while trying to connect to the Docker daemon socket
```

**Fix**:
```bash
sudo usermod -aG docker $USER
# Log out and log back in
```

### Docker Compose Not Found

**Error**:
```
docker: 'compose' is not a docker command.
```

**Fix**:
```bash
# Install Docker Compose plugin
sudo apt-get install docker-compose-plugin

# Or use old syntax (compose vs. compose)
alias docker-compose='docker compose'
```

### Make Not Found (Windows)

**Error**:
```
'make' is not recognized as an internal or external command
```

**Fix**:
- Use Git Bash instead of PowerShell
- Or install make via Chocolatey: `choco install make`
- Or run commands directly from Makefile

## Next Step

Once all prerequisites are installed → **Continue to `01-setup.md`**

---

**Last Updated**: 2025-11-08
**Est. Time**: 5 minutes
