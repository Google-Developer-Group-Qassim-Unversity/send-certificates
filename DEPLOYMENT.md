# Certificate API - Environment Configuration

## Quick Start

### Production Mode (default)
```bash
# Jobs saved to $HOME/GDG-certificates
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Development Mode
```bash
# Jobs saved to ./jobs relative to current directory
ENVIRONMENT=development uvicorn main:app --reload
```

## Environment Variables

Create a `.env` file with the following (only 2 variables needed):

```env
# Gmail App Password (required)
APP_PASSWORD=your-app-password-here

# Environment: production (default) or development
ENVIRONMENT=production
```

**Note:** All other configuration (email, SMTP, templates, etc.) is hardcoded in `config.py`.

## Storage Locations

| Environment | Jobs Folder |
|-------------|-------------|
| `production` (default) | `$HOME/GDG-certificates` |
| `development` | `./jobs` (relative to startup directory) |

## Hardcoded Configuration

The following settings are hardcoded in `config.py`:

- **Email:** `gdg.qu1@gmail.com`
- **SMTP:** `smtp.gmail.com:587`
- **Templates:** `certificate.pptx` (official), `certificate unofficial.pptx` (unofficial)
- **Retry Settings:** 3 retries, 4 seconds delay
- **LibreOffice:** Auto-detected based on OS

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Systemd Service (Production)

Create `/etc/systemd/system/certificate-api.service`:

```ini
[Unit]
Description=Certificate API Server
After=network.target

[Service]
Type=simple
User=gdg
WorkingDirectory=/path/to/send-certificates
Environment="ENVIRONMENT=production"
EnvironmentFile=/path/to/send-certificates/.env
ExecStart=/path/to/send-certificates/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable certificate-api
sudo systemctl start certificate-api
sudo systemctl status certificate-api
```
