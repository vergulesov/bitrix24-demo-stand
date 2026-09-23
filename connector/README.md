# Bitrix24 Connector

Working integration component for the Bitrix24 Demo Stand.

The connector sits between the presentation simulator and Bitrix24. It registers the connector in Bitrix24, sends external candidate messages through Open Lines, performs AI-based position recognition with GigaChat, and updates the resulting CRM deal.

## Responsibilities

- Register and activate the Bitrix24 connector.
- Configure connector data for an Open Line.
- Receive external demo messages through `/send`.
- Send messages to Bitrix24 Open Lines.
- Diagnose the Open Line session and CRM entity created by Bitrix24.
- Recognize the candidate's desired position with GigaChat.
- Update only the AI-related CRM fields after qualification.
- Keep SLA / priority / urgency workflow data untouched by the AI update.

## Runtime

The connector is a small Python HTTP service based on `http.server`.

Default local listener:

```text
127.0.0.1:8093
```

The Bitrix24 application handler must be exposed through HTTPS.

## Configuration

Create the environment configuration from:

```text
.env.example → .env
```

Required secret:

```text
GIGACHAT_AUTH_KEY
```

Do not commit real credentials.

The external `/send` endpoint also validates a send token stored by the deployed connector environment.

## Endpoints

### GET /

Health / handler page.

### POST /send

Accepts a JSON demo message and sends it through the configured Bitrix24 Open Line.

The simulator uses this endpoint as the external entry point for the candidate scenario.

### POST /bitrix/app

Bitrix24 application / connector handler.

## Important implementation detail

The connector does not create a second CRM deal when Bitrix24 has already created one through the Open Line.

Instead:

1. The message is delivered to Bitrix24.
2. The connector reads the resulting Open Line diagnostic.
3. If a CRM deal is found, AI qualification updates that existing deal.
4. Only AI-related fields are changed.
5. SLA and workflow fields are left intact.

This keeps the demo flow close to a real integration instead of maintaining a parallel CRM record.

## Deployment

The connector is intended to run on a VPS or another publicly reachable server behind HTTPS.

The production deployment used for the demo is external to this repository; this repository contains the application code and configuration template, not server credentials or private deployment files.
