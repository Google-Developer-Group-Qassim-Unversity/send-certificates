# Environment Variables

This project uses [Infisical](https://infisical.com/) for secrets management, with support for local overrides via `.env.local` during development.

This document explains how environment variables are loaded and managed in this project

## How It Works

### Priority Order (highest to lowest)

1. **`.env.local`** - Local overrides for development
2. **Infisical cloud secrets** - Shared team secrets

When running `run.py`, the command:

```bash
infisical run --path=/emails-backend --env=dev -- python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

1. Fetches secrets from Infisical cloud
2. Starts the server
3. the server loads `.env.local` and **overrides** any conflicting values

## Setup

### 1. Install Infisical CLI

```bash
# Windows
winget install infisical

# macOS/Linux
brew install infisical/get-cli/infisical

# Arch Linux
yay -S infisical-bin

# Ubuntu
# 1. Add Infisical repository
curl -1sLf 'https://artifacts-cli.infisical.com/setup.deb.sh' | sudo -E bash
# 2. install CLI
sudo apt-get update && sudo apt-get install -y infisical

# Or visit https://infisical.com/docs/cli/overview

```

### 2. Login to Infisical

1. `infisical login`
2. Select ` ▸ Self-Hosting or Dedicated Instance`
3. Select ` ▸ Add a new domain`
4. add `https://infisical.albrrak773.com`

### 3. Create Local Overrides (Optional)

Create a `.env.local` file in the project root:

```env
# Override AWS/SES config for local development
AWS_REGION=eu-north-1
SES_ACCESS_KEY_ID=your_access_key_id
SES_SECRET_ACCESS_KEY=your_secret_access_key
SES_FROM_ADDRESS=certificates@gdg-q.com
```

## Secrets

The following secrets are managed in Infisical under the path `/emails-backend`:

| Variable | Description |
| --- | --- |
| `AWS_REGION` | AWS region the SES domain identity is verified in -- must match exactly, SES identities are per-region |
| `SES_ACCESS_KEY_ID` | Access key for the IAM user scoped to SES sending. Named `SES_*` (not `AWS_*`) so it's never picked up by boto3's ambient `AWS_ACCESS_KEY_ID` credential discovery and can't be confused with any other AWS-shaped credentials in this project (see `R2_*` below, same reasoning) |
| `SES_SECRET_ACCESS_KEY` | Secret key for the same IAM user |
| `SES_FROM_ADDRESS` | Verified sending address, e.g. `certificates@gdg-q.com` -- domain verification covers any address on the domain |

## Infisical Dashboard

you can see and manage the secrets in the [link here](https://infisical.albrrak773.com/organizations/de21a8c1-87e7-4f92-9e3b-253791905f8e/projects/secret-management/300b1e97-7e52-4a4e-872d-053b9082cac5/overview)
