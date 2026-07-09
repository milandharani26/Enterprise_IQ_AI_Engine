# AWS EC2 Monolithic Deployment Guide (Without Docker)

This guide walks you through the step-by-step setup to host the EnterpriseIQ application on an AWS EC2 instance without Docker. 

In this architecture, the frontend Next.js application is statically exported (`cpanel/out`) and served directly by the FastAPI backend. FastAPI acts as the single backend+frontend entrypoint running locally on port `8000`, and **Nginx** is used as a reverse proxy to route public port `80` traffic to FastAPI.

---

## Prerequisites

- An AWS EC2 instance running **Ubuntu 22.04 LTS** (t3.medium or larger recommended).
- An Elastic IP associated with your EC2 instance.
- Inbound security group rules configured to allow:
  - `SSH` (Port 22)
  - `HTTP` (Port 80)
  - `HTTPS` (Port 443) (if using SSL)

---

## Step 1: Prepare the EC2 Instance

SSH into your EC2 instance:
```bash
ssh -i /path/to/key.pem ubuntu@your-ec2-ip
```

Update system packages:
```bash
sudo apt update && sudo apt upgrade -y
```

### Install Python and Poetry
Install python3-pip, python3-venv, and other build essentials:
```bash
sudo apt install python3-pip python3-venv build-essential git curl -y
```

Install Poetry globally for the `ubuntu` user:
```bash
curl -sSL https://install.python-poetry.org | python3 -
export PATH="/home/ubuntu/.local/bin:$PATH"
echo 'export PATH="/home/ubuntu/.local/bin:$PATH"' >> ~/.bashrc
```

Verify Poetry is installed:
```bash
poetry --version
```

### Install & Configure PostgreSQL (with pgvector)
FastAPI checks for a database connection with pgvector support.

Install PostgreSQL:
```bash
sudo apt install postgresql postgresql-contrib -y
```

Install pgvector build dependencies and build pgvector:
```bash
sudo apt install postgresql-server-dev-all -y
cd /tmp
git clone --branch v0.4.0 https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
```

Configure PostgreSQL database and user:
```bash
sudo -i -u postgres psql
```
In the PostgreSQL terminal, run:
```sql
CREATE DATABASE enterpriseiq_db;
CREATE USER enterpriseiq_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE enterpriseiq_db TO enterpriseiq_user;
\c enterpriseiq_db;
CREATE EXTENSION IF NOT EXISTS vector;
\q
```

---

## Step 2: Install and Configure Nginx

Nginx will serve as the reverse proxy.

Install Nginx:
```bash
sudo apt install nginx -y
```

Remove the default Nginx page:
```bash
sudo rm /etc/nginx/sites-enabled/default
```

Copy the Nginx configuration file from the repository (once deployment copies files) or create it manually:
```bash
sudo nano /etc/nginx/sites-available/enterpriseiq.conf
```
Paste the following content (or use the one in `infra/ec2/nginx.conf`):
```nginx
server {
    listen 80;
    server_name _; # Replace with your domain name if configured

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSockets support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";

        # Timeouts for longer migrations/ingestion
        proxy_read_timeout 300s;
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
    }
}
```

Enable the configuration and restart Nginx:
```bash
sudo ln -s /etc/nginx/sites-available/enterpriseiq.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## Step 3: Register the Systemd Service

Create the directory for the project source code on the EC2 host:
```bash
mkdir -p /home/ubuntu/enterpriseiq_ai
```

Create the systemd service file:
```bash
sudo nano /etc/systemd/system/enterpriseiq.service
```
Paste the service configuration:
```ini
[Unit]
Description=EnterpriseIQ AI FastAPI Monolith Service
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/enterpriseiq_ai
ExecStart=/home/ubuntu/enterpriseiq_ai/.venv/bin/python -m uvicorn main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=enterpriseiq

[Install]
WantedBy=multi-user.target
```

Enable the systemd service (it will start failing initially until files are deployed):
```bash
sudo systemctl daemon-reload
sudo systemctl enable enterpriseiq
```

---

## Step 4: Configure GitHub Repository Secrets

To enable automated deployments via GitHub Actions, navigate to your repository on GitHub and go to **Settings > Secrets and variables > Actions > New repository secret**.

Add the following secrets:

1. **`EC2_HOST`**: The public Elastic IP of your EC2 instance (e.g. `54.210.xx.xx`).
2. **`EC2_USER`**: The SSH user, which is `ubuntu` by default on Ubuntu AMIs.
3. **`EC2_SSH_KEY`**: The complete private SSH key (`.pem` file contents) used to authenticate. Include the header and footer (`-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----`).
4. **`ENV_FILE_CONTENT`**: The contents of the production `.env` file that will reside at the root of the project.
   
Example `ENV_FILE_CONTENT`:
```env
DATABASE_URL=postgresql+asyncpg://enterpriseiq_user:your_secure_password@localhost:5432/enterpriseiq_db
ENV=production
# Add other backend configurations such as OPENAI_API_KEY, AWS keys, etc.
```

---

## Step 5: Run Your First Deployment

Push a commit to the `main` branch:
```bash
git add .
git commit -m "Configure EC2 deployment and systemd"
git push origin main
```

Navigate to the **Actions** tab in your GitHub repository to monitor the run. Once completed:
1. The static frontend will be built on the runner.
2. Codebase files (excluding node_modules and Next.js source files) and the built `cpanel/out` directory will copy to `/home/ubuntu/enterpriseiq_ai`.
3. Poetry will initialize a local virtual environment and install dependencies.
4. Database migrations will execute automatically.
5. The `enterpriseiq` systemd service will restart.

---

## Step 6: Verify and Troubleshoot

### Check Application Logs
To verify that the application is running successfully on the EC2 host:
```bash
sudo journalctl -u enterpriseiq -f -n 50
```

### Check Nginx Status
If the server returns a `502 Bad Gateway`, verify that Nginx is running and FastAPI is serving on port 8000:
```bash
sudo systemctl status nginx
curl -I http://127.0.0.1:8000/api/v1/health
```
*(Verify your health check endpoint matches the routes configured in FastAPI)*
