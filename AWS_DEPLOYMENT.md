# AWS Deployment Guide

This guide deploys the AI Sales Orchestrator on **AWS EC2**, with the product catalog and inventory data stored in **Amazon S3**.

## Architecture

```
                    ┌──────────────────────── EC2 instance ────────────────────────┐
  Browser ──HTTP──► │  Nginx (port 80)                                              │
                    │   ├─ /            → frontend/ (static HTML, CSS, JS)          │
                    │   ├─ /api/*       → Uvicorn :8000 (FastAPI)                   │
                    │   └─ /ws/*        → Uvicorn :8000 (WebSocket upgrade)         │
                    │                                                               │
                    │  systemd service: syncs data from S3, then starts Uvicorn     │
                    └───────────────────────────────┬───────────────────────────────┘
                                                    │ aws s3 sync (IAM role, read-only)
                                          ┌─────────▼─────────┐
                                          │  S3 bucket        │
                                          │  products.json    │
                                          │  stores.json      │
                                          │  customers.json   │
                                          └───────────────────┘
```

- **S3** is the source of truth for catalog and inventory data. To update products or stock, upload new files to S3 and restart the service.
- **EC2** runs the FastAPI backend and serves the frontend through Nginx. On every start, the service pulls the latest data from S3 into `backend/data/`.
- `sessions.json` is runtime state. It stays on the instance and is never overwritten by the sync.

---

## Prerequisites

- An AWS account and the [AWS CLI](https://docs.aws.amazon.com/cli/) configured locally
- An EC2 key pair for SSH
- An Anthropic API key

---

## 1. Upload the data to S3

```bash
aws s3 mb s3://<your-bucket-name> --region ap-south-1

aws s3 cp backend/data/products.json  s3://<your-bucket-name>/data/
aws s3 cp backend/data/stores.json    s3://<your-bucket-name>/data/
aws s3 cp backend/data/customers.json s3://<your-bucket-name>/data/
```

Keep the bucket private. Block Public Access stays on, since the instance reads it through an IAM role.

## 2. Create an IAM role for the instance

Create an EC2 role with read-only access to the bucket, so no AWS keys are stored on the server:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket"],
      "Resource": [
        "arn:aws:s3:::<your-bucket-name>",
        "arn:aws:s3:::<your-bucket-name>/*"
      ]
    }
  ]
}
```

## 3. Launch the EC2 instance

- **AMI:** Ubuntu 22.04 LTS
- **Instance type:** t3.small (t3.micro works for demos)
- **IAM role:** the role from step 2
- **Security group inbound rules:**
  - SSH (22) from your IP only
  - HTTP (80) from anywhere

Port 8000 does **not** need to be open. Nginx proxies to Uvicorn locally.

## 4. Install the application

```bash
ssh -i <key>.pem ubuntu@<ec2-public-ip>

sudo apt update && sudo apt install -y python3-venv git nginx awscli
git clone https://github.com/Varsha-1605/AI-Sales-Orchestrator.git
cd AI-Sales-Orchestrator/backend

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create `backend/.env`:

```env
ANTHROPIC_API_KEY=your-key
ANTHROPIC_MODEL=claude-sonnet-4-20250514
FASTAPI_HOST=127.0.0.1
FASTAPI_PORT=8000
DEBUG_MODE=False
ALLOWED_ORIGINS=http://<ec2-public-ip>
```

## 5. Point the frontend at the server

The frontend pages call `http://localhost:8000`. Replace it with the instance address so requests go through Nginx:

```bash
cd ~/AI-Sales-Orchestrator/frontend
sed -i "s#http://localhost:8000#http://<ec2-public-ip>#g; s#ws://localhost:8000#ws://<ec2-public-ip>#g" *.html
```

## 6. Run the backend as a service

Create `/etc/systemd/system/orchestrator.service`:

```ini
[Unit]
Description=AI Sales Orchestrator (FastAPI)
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/AI-Sales-Orchestrator/backend
# Pull the latest catalog and inventory data from S3 before every start
ExecStartPre=/usr/bin/aws s3 sync s3://<your-bucket-name>/data/ /home/ubuntu/AI-Sales-Orchestrator/backend/data/ --exclude sessions.json
ExecStart=/home/ubuntu/AI-Sales-Orchestrator/backend/venv/bin/uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

The backend must run from the `backend/` directory, because it loads data from relative `data/` paths.

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now orchestrator
```

## 7. Configure Nginx

Create `/etc/nginx/sites-available/orchestrator`:

```nginx
server {
    listen 80;
    server_name _;

    # Frontend
    root /home/ubuntu/AI-Sales-Orchestrator/frontend;
    index index.html;

    # REST API
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # WebSocket
    location /ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/orchestrator /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo chmod o+x /home/ubuntu          # let Nginx read the frontend folder
sudo nginx -t && sudo systemctl reload nginx
```

Open `http://<ec2-public-ip>/index.html`.

---

## Updating catalog or inventory data

```bash
aws s3 cp backend/data/products.json s3://<your-bucket-name>/data/
ssh ubuntu@<ec2-public-ip> "sudo systemctl restart orchestrator"   # re-syncs from S3 on start
```

## Operations

| Task | Command |
|---|---|
| Health check | `curl http://<ec2-public-ip>/health` |
| Backend logs | `sudo journalctl -u orchestrator -f` |
| Restart backend | `sudo systemctl restart orchestrator` |
| Nginx logs | `sudo tail -f /var/log/nginx/error.log` |

## Security notes

- The instance reads S3 through an **IAM role**; no AWS access keys live on the server.
- The S3 bucket is private, and SSH is limited to your IP.
- Uvicorn listens on `127.0.0.1` only, so the API is reachable only through Nginx.
- Keep `.env` out of git. It's covered by `.gitignore`.
- For production, add HTTPS with Let's Encrypt (`sudo apt install certbot python3-certbot-nginx && sudo certbot --nginx`). The browser voice features (Web Speech API) need a secure context outside localhost.
