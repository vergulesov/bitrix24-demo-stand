# Bitrix24 Demo Stand

**Reproducible demonstration environment for Bitrix24 CRM, Open Lines, AI qualification and SLA-driven recruitment workflows.**

This project packages the working components needed to prepare and run a repeatable Bitrix24 demonstration without rebuilding the demo data by hand.

The stand is built around a simple idea:

> **Prepare the CRM state → run a realistic scenario → demonstrate the business process.**

## What the stand demonstrates

The current scenario is based on a recruitment agency workflow:

1. A candidate sends an incoming message.
2. The message enters a Bitrix24 Open Line.
3. The connector sends the message into Bitrix24.
4. GigaChat analyzes the incoming text and determines the desired position.
5. Bitrix24 creates or updates the CRM deal.
6. SLA / priority / urgency data remains under the CRM workflow and is not overwritten by AI qualification.
7. The recruiter works with the candidate through the recruitment pipeline.
8. The resulting CRM state can be shown as part of a short presentation.

The project is intentionally a **demo stand**, not a complete HR platform.

## Architecture

```
                    Demo scenario
                         │
                         ▼
                ┌─────────────────┐
                │  Scenario       │
                │  Simulator      │
                └────────┬────────┘
                         │
                         │ HTTP / REST
                         ▼
                ┌─────────────────┐
                │ Bitrix24        │
                │ Connector       │
                └────────┬────────┘
                         │
                         │ Bitrix24 REST API
                         │ Open Lines
                         ▼
                ┌─────────────────┐
                │    Bitrix24     │
                │ CRM + Open Lines│
                └─────────────────┘
                         ▲
                         │
                    GigaChat
                  AI qualification
```

### Components

#### `demo-stand/`

The presentation-side simulator and Bitrix24 setup scripts.

It is responsible for:

- preparing the CRM environment;
- creating synthetic candidates and deals;
- populating demo fields;
- placing records into the required pipeline stages;
- generating repeatable candidate scenarios;
- preparing SLA-related demo states;
- running the scripted presentation flow;
- restoring / cleaning demo data.

The main scenario logic lives in `staffflow_simulator.py`.

#### `connector/`

The working Bitrix24 connector used by the demo.

It provides:

- Bitrix24 connector registration;
- Open Line message delivery;
- interaction with Bitrix24 REST API;
- GigaChat-based position recognition;
- CRM deal creation/update logic;
- Open Line diagnostics;
- an external `/send` endpoint for the simulator.

The connector is deliberately kept separate from the simulator so the integration layer can be demonstrated independently.

## Project structure

```
bitrix24-demo-stand/
├── connector/
│   ├── app.py
│   ├── requirements.txt
│   ├── .env.example
│   └── README.md
│
├── demo-stand/
│   ├── staffflow_simulator.py
│   ├── ai_position_demo.py
│   ├── sla_demo.py
│   ├── main.py
│   ├── demo.py
│   ├── setup.py
│   ├── restore.py
│   ├── bitrix.py
│   ├── config.py
│   ├── schema.py
│   ├── requirements.txt
│   └── .env.example
│
├── README.md
└── .gitignore
```

## Getting started

### 1. Prepare Bitrix24

The demo requires a Bitrix24 portal with:

- REST access;
- the recruitment pipeline used by the scenario;
- the required CRM fields;
- an Open Line configured for the connector.

The setup scripts in `demo-stand/` are intended to prepare the CRM-side demo environment.

### 2. Configure the simulator

Copy:

```text
demo-stand/.env.example → demo-stand/.env
```

Set the Bitrix24 webhook and the connector endpoint/token required by the local environment.

### 3. Configure the connector

Copy:

```text
connector/.env.example → connector/.env
```

Set the GigaChat authorization key.

The connector also needs to be deployed to a publicly reachable host because Bitrix24 must be able to call its handler.

### 4. Install dependencies

For the simulator:

```bash
cd demo-stand
pip install -r requirements.txt
```

For the connector:

```bash
cd connector
pip install -r requirements.txt
```

### 5. Run the scenario

The exact entry point depends on the scenario being demonstrated. The main simulator and individual demo scripts are kept in `demo-stand/`.

## Presentation scenario

The stand was built around a short 5–7 minute demonstration:

```
Problem
   ↓
Incoming candidate
   ↓
AI qualification
   ↓
SLA
   ↓
Recruiter workspace
   ↓
Result
   ↓
Report
   ↓
V2
```

The goal is to show the value of the automation rather than present every possible CRM configuration.

## Safety of demo data

The simulator works with synthetic candidates and dedicated demo markers.

Before using it against a real portal:

- verify the configured webhook;
- verify the pipeline and field IDs;
- check the target Open Line;
- never commit credentials or tokens;
- use a dedicated demo environment where possible.

## Related project

The original setup project remains separate and is not replaced by this repository.

- `bitrix24-quick-setup` — original Bitrix24 setup / automation project.
- `bitrix24-demo-stand` — standalone portfolio-ready demo environment.

## Status

**Working demo project.**

The repository contains the current connector and the demo-stand files used for the Bitrix24 recruitment automation presentation.
