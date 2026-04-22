# GitHub Webhook Monitoring System

A production-grade asynchronous pipeline for detecting and notifying suspicious behavior in GitHub organizations.

## 🌟 Overview

This system provides a modular, scalable, and resilient infrastructure for monitoring GitHub webhook events. It implements a **Decoupled Architecture** where event ingestion and event processing are separated via Redis, ensuring high throughput and reliability.

## 🏗️ Architecture

The system is built on four pillars of modern backend engineering:

1.  **Ingestion Layer (FastAPI)**: A high-performance API that validates incoming webhooks, ensures idempotency using Redis keys, and pushes events to durable streams.
2.  **Orchestration Layer (Redis Streams & Sorted Sets)**:
    *   **Streams**: Provides per-organization event persistence and history.
    *   **Global Fair Scheduler**: A Sorted Set based orchestrator that ensures "Noisy Neighbors" (large orgs) do not block processing for smaller organizations.
3.  **Processing Layer (Worker Service)**: An asynchronous worker that implements a "Lock-Process-Reschedule" loop. It processes events in batches to ensure system-wide fairness.
4.  **Resilience Layer (Recovery Task)**: A background task that automatically repairs the system state if a worker crashes, ensuring no event is ever left unprocessed.

## 🔍 Suspicious Behaviors Detected

The system comes pre-configured with three sophisticated detectors:
1.  **Push Time**: Identifies code pushes occurring between 14:00 and 16:00 UTC (configurable).
2.  **Hacker Teams**: Monitors for new teams created with names starting with "hacker".
3.  **Fast Deletion**: Detects repositories that are created and then deleted in less than 10 minutes, using Redis-backed state management.

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9+
- Docker & Docker Compose (for Redis)
- [ngrok](https://ngrok.com/) (for local webhook testing)

### 2. Installation
```bash
# Clone the repository
git clone <your-repo-url>
cd legit

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Environment Configuration
Copy the template and adjust your settings:
```bash
cp .env.example .env
```

### 4. Start Infrastructure
Start the Redis server using Docker:
```bash
docker-compose up -d
```

### 5. Run the Application
The system requires two components to be running simultaneously:

**Terminal 1: Webhook Server**
```bash
python -m app.webhook_server
```

**Terminal 2: Processing Worker**
```bash
python -m app.worker
```

## 🧪 Testing & Demos

### Automated Tests
Run the comprehensive test suite (unit and integration tests):
```bash
pytest
```


## 🛠️ Design Patterns Used
- **Strategy Pattern**: For modular and extensible detectors.
- **Distributed Locking**: Using Redis `SET NX` to ensure atomic processing per organization.
- **Idempotency Pattern**: Leveraging GitHub's `X-GitHub-Delivery` ID to prevent duplicate processing.
- **Fair Queuing**: Implementing a round-robin scheduler via Redis Sorted Sets.

---
Built with ❤️ for the Legit Security Challenge.
