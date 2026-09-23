# Bitrix24 Demo Stand / Scenario Simulator

A reproducible demo environment for Bitrix24 CRM scenarios.

The project prepares a Bitrix24 portal for a presentation by generating synthetic candidates, creating CRM deals, filling the required fields, and running predefined scenarios instead of preparing demo data manually.

## What it solves

A CRM demo is much easier to run when the starting state is reproducible.

Instead of manually creating candidates and deals before every presentation, the Demo Stand generates synthetic data and prepares Bitrix24 for a predefined scenario.

## Architecture

```
Scenario Simulator
       |
       | REST / HTTP
       v
Bitrix24 Connector
       |
       | Bitrix24 REST API / Open Lines
       v
    Bitrix24
```

The project contains two cooperating components:

- **Scenario Simulator** — generates demo data and runs predefined CRM scenarios.
- **Bitrix24 Connector** — integration component used by the simulator for the communication flow with Bitrix24 and Open Lines.

## Scenario Simulator

The simulator can:

- generate synthetic candidate data;
- create CRM deals;
- populate candidate and process fields;
- place deals into required pipeline stages;
- generate different candidate states for a presentation;
- prepare SLA-related data;
- run repeatable demo scenarios;
- clear previously generated demo data;
- run health checks for the demo environment.

Generated records use dedicated demo markers so they can be identified and cleaned up without affecting unrelated CRM data.

## Bitrix24 Connector

The connector is a separate component of the demo stand.

It provides the integration layer required by the presentation scenario, including interaction with Bitrix24 REST API and Open Lines.

The connector is located in `connector/`.

## Example flow

```
Run scenario
     ↓
Generate synthetic candidate
     ↓
Create / update CRM deal
     ↓
Populate scenario fields
     ↓
Prepare Open Line / CRM state
     ↓
Bitrix24 is ready for demonstration
```

## Project structure

```
bitrix24-demo-stand/
├── demo-stand/
│   ├── main.py
│   ├── demo.py
│   ├── staffflow_simulator.py
│   ├── ai_position_demo.py
│   ├── sla_demo.py
│   ├── bitrix.py
│   ├── config.py
│   ├── schema.py
│   ├── setup.py
│   └── restore.py
│
├── connector/
│   ├── app.py
│   ├── requirements.txt
│   └── .env.example
│
├── README.md
└── .gitignore
```

## Requirements

- Python 3.10+
- Bitrix24 portal with REST access
- Bitrix24 webhook for the simulator
- GigaChat credentials for the AI demonstration
- VPS or another reachable host for the connector

## Configuration

Create local `.env` files using the provided examples.

Real credentials, tokens, logs and local environment files are intentionally excluded from the repository.

## Status

Working demonstration project used to prepare and run Bitrix24 CRM presentation scenarios.
