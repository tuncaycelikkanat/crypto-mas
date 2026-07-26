#!/usr/bin/env bash
# Crypto-MAS 1-Click Automated Server Deployment Script

set -e

echo "=========================================================="
echo "      Crypto-MAS - Automated 1-Click Setup Engine"
echo "=========================================================="

# 1. Setup .env automatically if missing
if [ ! -f .env ]; then
    echo "[+] Creating .env from .env.example..."
    cp .env.example .env
    # Auto-configure for SQLite and localhost redis by default
    sed -i 's|postgresql+psycopg://crypto:crypto@postgres:5432/crypto_mas|sqlite:///crypto_mas.db|g' .env
    sed -i 's|redis://redis:6379/0|redis://localhost:6379/0|g' .env
    echo "[+] .env configured with default SQLite database."
else
    echo "[✓] .env already exists."
fi

# 2. Check Docker availability & install if missing on Ubuntu/Debian
if ! command -v docker &> /dev/null; then
    echo "[!] Docker is not installed. Installing Docker & Docker Compose automatically..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y docker.io docker-compose-v2
    else
        echo "[ERROR] Please install Docker manually on this operating system."
        exit 1
    fi
else
    echo "[✓] Docker is already installed."
fi

# 3. Stop existing standalone uvicorn processes if any
if pgrep -f "uvicorn crypto_mas" > /dev/null; then
    echo "[+] Stopping standalone uvicorn processes to free port 8000..."
    pkill -f "uvicorn crypto_mas" || true
fi

# 4. Build & Launch in Docker (automatically compiles Frontend & runs Alembic migrations)
echo "[+] Starting Crypto-MAS containers (building frontend & backend)..."
docker compose up -d --build

echo "=========================================================="
echo " [✓] Crypto-MAS successfully deployed & running 24/7!"
echo " [*] Dashboard available at port :8000"
echo " [*] To view live logs: docker compose logs -f"
echo "=========================================================="
