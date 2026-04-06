# Hub-and-Spoke Architecture

## Overview
This architecture implements a **Hub-and-Spoke** pattern where:
- **Core Service** (Hub): Central orchestration with service registry, event bus, and config management
- **Vertical Services** (Spokes): Modular, independently scalable services for specific capabilities
- **Infrastructure Services**: Gateway, Privacy, BIM Ingestion, Orchestration

## Service Map

### Core Infrastructure
| Service | Port | Purpose |
|---------|------|---------|
| `core` | 3000 | Central hub - registry, events, config |
| `gateway` | 8000 | API gateway & policy engine |
| `privacy` | 3010 | PII redaction & privacy tiers |
| `bim-ingestion` | 8001 | BIM file processing |
| `orchestration` | 8002 | Workflow execution |

### Vertical Services
| Service | Port | Purpose |
|---------|------|---------|
| `omniscale` | 3040 | Central dashboard & metrics |
| `ai-consistency` | 3050 | AI model testing & validation |
| `workflow-architect` | 3060 | Workflow design & planning |
| `cyberscribe` | 3070 | Code anomaly detection |
| `public-beta` | 3080 | Feature preview management |
| `autopitch` | 3090 | Idea submission & tracking |
| `digital-it-girl` | 3100 | Emerging tech trends |

## Quick Start

```bash
# Start all services
docker-compose up -d

# View service status
docker-compose ps

# Check Core service logs
docker-compose logs -f core

# Access Omniscale Dashboard
open http://localhost:3040
```

## Core API Endpoints

### Service Registry (`/registry`)
- `POST /register` - Register a new service
- `POST /heartbeat/{service_id}` - Update service heartbeat
- `GET /services` - List all services
- `GET /services/{service_id}` - Get service details
- `DELETE /services/{service_id}` - Unregister service
- `POST /discover` - Discover services by capability

### Event Bus (`/events`)
- `POST /publish` - Publish an event
- `POST /subscribe` - Subscribe to event types
- `DELETE /unsubscribe/{service_id}` - Unsubscribe
- `GET /events` - Retrieve events

### Configuration (`/config`)
- `GET /config` - Get configuration
- `PUT /config` - Update configuration
- `POST /verticals` - Register vertical
- `GET /verticals` - List verticals
- `DELETE /verticals/{vertical_id}` - Unregister vertical

## Adding New Verticals

### Option A: Scaffold Script (recommended)

```bash
./infra/scripts/new_vertical.sh my_vertical 3110 search analytics
```

This creates the full directory structure, Dockerfile, requirements.txt, a `main.py`
wired to `VerticalBase`, and appends the service to `docker-compose.yml`.

### Option B: Manual Setup

1. Create directory structure:
```bash
mkdir -p services/verticals/new_vertical/app
touch services/verticals/new_vertical/app/__init__.py
```

2. Add main.py using VerticalBase:
```python
from packages.vertical_base import EventPayload, VerticalBase

vertical = VerticalBase(
    service_id="new_vertical",
    port=8000,
    capabilities=["search", "analytics"],
    event_subscriptions=["workflow.completed"],
)
app = vertical.app

@vertical.on_event("workflow.completed")
async def handle_workflow(event: EventPayload):
    print(f"Workflow done: {event.payload}")

@app.get("/")
async def root():
    return {"service": "new_vertical", "status": "operational"}
```

3. Add requirements.txt:
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
httpx==0.26.0
```

4. Add Dockerfile (copy from existing vertical)

5. Add to docker-compose.yml

### What VerticalBase gives you automatically

- **Self-registration**: on startup, registers with Core's service registry
- **Event subscription**: subscribes to event types with a callback URL
- **Event receiving**: `POST /events/receive` endpoint auto-mounted
- **Event handlers**: `@vertical.on_event("type")` decorator for clean handler registration
- **Event publishing**: `await vertical.publish_event("type", payload)` from anywhere
- **Health check**: `GET /health` auto-mounted
- **Clean shutdown**: unregisters and unsubscribes on container stop

### Accessing verticals via the Gateway

Once registered, verticals are reachable through the gateway proxy:

```bash
# Direct access (within docker network)
curl http://new_vertical:8000/

# Via gateway (external access)
curl http://localhost:8000/v1/verticals/new_vertical/

# Any sub-path is proxied
curl http://localhost:8000/v1/verticals/new_vertical/metrics
```

## Architecture Principles

1. **Modularity**: Each vertical is independent and can be extracted to separate repo
2. **Discovery**: Services register with Core for dynamic routing
3. **Event-Driven**: Inter-service communication via event bus
4. **Configurable**: Centralized config management
5. **Clean Infrastructure**: Minimal dependencies between services

## Next Steps

- [ ] Implement Redis Pub/Sub for production event bus
- [ ] Add service-to-service authentication
- [ ] Implement health check aggregation in Omniscale
- [ ] Add metrics collection and visualization
- [ ] Create CI/CD pipelines for independent deployment
