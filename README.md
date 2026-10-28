# Event-Driven Notification System

A compact event-driven backend built with **FastAPI, RabbitMQ, Python workers, and Docker Compose**. It demonstrates asynchronous notification processing, multi-channel dispatch, structured logging, dead-letter handling, and containerized local development.

This repository consolidates the final state of a four-step personal project:

- **Day 1:** FastAPI producer + RabbitMQ + worker
- **Day 2:** structured logs, failure handling, TTL and DLX foundation
- **Day 3:** Dead Letter Queue and dedicated DLQ worker
- **Day 4:** email/SMS/push routing through channel-specific handlers

## Architecture

```text
Client
  |
  v
FastAPI  --publish-->  notifications queue  -->  Worker
                                             |       |
                                             |       +--> email
                                             |       +--> sms
                                             |       +--> push
                                             |
                                      rejected/expired
                                             |
                                             v
                                     dlx.notifications
                                             |
                                             v
                                     notifications.dlq
                                             |
                                             v
                                         DLQ Worker
```

> The delivery handlers are intentionally simulated with logs. The project focuses on messaging architecture rather than external email/SMS providers.

## Features

- FastAPI `POST /notifications` endpoint
- Input validation for `email`, `sms`, and `push`
- Durable RabbitMQ queues and persistent messages
- Publisher confirms
- Structured worker logs
- Channel-based dispatch
- RabbitMQ message TTL (30 seconds)
- Dead Letter Exchange (`dlx.notifications`)
- Dead Letter Queue (`notifications.dlq`)
- Dedicated DLQ consumer
- Docker Compose health checks and service ordering
- `force_fail` switch for deterministic DLQ testing

## Project structure

```text
.
├── api/
│   ├── Dockerfile
│   ├── main.py
│   └── requirements.txt
├── worker/
│   ├── Dockerfile
│   ├── worker.py
│   └── requirements.txt
├── dlq-worker/
│   ├── Dockerfile
│   ├── worker.py
│   └── requirements.txt
├── docker-compose.yml
├── rabbitmq-definitions.json
├── .gitignore
├── LICENSE
└── README.md
```

## Run locally

Requirements: Docker with Docker Compose.

```bash
docker compose up --build
```

Services:

- API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- RabbitMQ Management: `http://localhost:15672` (`guest` / `guest`, local demo only)

## Test the API

### Email

```bash
curl -X POST http://localhost:8000/notifications \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u1","channel":"email","message":"Hello via email"}'
```

### SMS

```bash
curl -X POST http://localhost:8000/notifications \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u2","channel":"sms","message":"Hello via SMS"}'
```

### Push

```bash
curl -X POST http://localhost:8000/notifications \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u3","channel":"push","message":"Hello via push"}'
```

### Route a message to the DLQ

```bash
curl -X POST http://localhost:8000/notifications \
  -H "Content-Type: application/json" \
  -d '{"user_id":"u4","channel":"email","message":"Simulated failure","force_fail":true}'
```

`force_fail=true` makes the worker reject the message without requeue. RabbitMQ then routes it through the configured DLX to `notifications.dlq`, where the DLQ worker logs and acknowledges it.

## Health check

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## Reliability notes

RabbitMQ topology is provisioned from `rabbitmq-definitions.json`. Application code deliberately does **not** redeclare the main queue with conflicting arguments. Messages are published as persistent and publisher confirms are enabled.

The project demonstrates the DLQ path directly for deterministic local testing. A production retry strategy would normally add bounded retries/backoff (for example with retry queues or delayed delivery) before sending a message to the final DLQ.

## Security note

The default `guest/guest` RabbitMQ credentials are included only for local development. Do not expose the management port or use these credentials in a deployed environment.

## License

MIT
