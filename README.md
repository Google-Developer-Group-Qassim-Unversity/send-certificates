# Send Certificates

A FastAPI microservice for **certificate generation and email delivery** for Google Developer Groups (GDG) Qassim.

Generates personalized attendance certificates from SVG templates, converts them to PNG, and emails them to attendees. Also supports sending blast (broadcast) emails.

## Features

- Certificate generation from SVG templates (Arabic & English, official & unofficial)
- PNG conversion via `rsvg-convert`
- Email delivery via Gmail SMTP (two sender accounts)
- Blast email support (broadcast to multiple recipients via BCC)
- Health check endpoint (verifies `rsvg-convert` and SMTP connectivity)

## API Endpoints

| Method   | Path                    | Description                             |
| -------- | ----------------------- | --------------------------------------- |
| `GET`  | `/health`             | Health check (rsvg-convert + SMTP)      |
| `POST` | `/emails/certificate` | Generate & email a certificate          |
| `POST` | `/blasts`             | Send blast email to multiple recipients |

## Prerequisites

- **Python >= 3.13**
- **[uv](https://docs.astral.sh/uv/)** — Python package manager
- **[rsvg-convert](https://wiki.gnome.org/Projects/LibRsvg)** — SVG to PNG conversion
- **[Infisical CLI](https://infisical.com/docs/cli/overview)** — Secrets management

### Installing rsvg-convert

```bash
# Ubuntu/Debian
sudo apt-get install -y librsvg2-bin

# macOS
brew install librsvg

# Arch Linux
pacman -S librsvg
```

### Setting up Infisical

See [`docs/ENVIRONMENT_VARIABLES.md`](docs/ENVIRONMENT_VARIABLES.md) for full setup instructions.

## Running Locally

```bash
# Install dependencies
uv sync

# Start the server (fetches secrets from Infisical)
python run.py
```

The server runs on `http://0.0.0.0:8000`.

Alternatively, without Infisical (if secrets are already in your environment):

```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Deployment

Pushing to `main` triggers a GitHub Actions workflow that deploys to the VPS via SSH. Secrets are injected at runtime using Infisical in production mode.

## Required Secrets

| Variable                    | Description                                    |
| --------------------------- | ---------------------------------------------- |
| `APP_PASSWORD_KERNELTICS` | Gmail App Password for `info@kerneltics.com` |
| `APP_PASSWORD_GDG_QASSIM` | Gmail App Password for `gdg.qu1@gmail.com`   |
