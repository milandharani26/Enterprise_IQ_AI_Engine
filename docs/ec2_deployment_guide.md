# AWS EC2 Docker Deployment Guide (All-in-One Container)

This guide walks you through the step-by-step setup to host the EnterpriseIQ application on an AWS EC2 instance using a single Docker container. 

In this architecture, the entire application stack—including the FastAPI backend (serving the statically exported React frontend), Celery Worker, PostgreSQL (with pgvector), and Redis—runs inside a single unified Docker container managed by `supervisord`. **Nginx** is used as a reverse proxy on the host to route public port `80` traffic to FastAPI (port `8000`).

---

## Prerequisites

- An AWS EC2 instance running **Ubuntu 22.04 LTS** (t3.medium or larger recommended).
- An Elastic IP associated with your EC2 instance.
- Inbound security group rules configured to allow:
  - `SSH` (Port 22)
  - `HTTP` (Port 80)
  - `HTTPS` (Port 443) (if using SSL)
  - (Optional) `PostgreSQL` (Port 5433) (if you want to access the DB directly from outside using port 5433)

---

## Step 1: Install & Configure Nginx on EC2

Nginx will serve as the reverse proxy.

SSH into your EC2 instance:
```bash
ssh -i /path/to/key.pem ubuntu@your-ec2-ip
```

Update system packages and install Nginx:
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install nginx -y
```

Remove the default Nginx page:
```bash
sudo rm /etc/nginx/sites-enabled/default
```

Create a site configuration file:
```bash
sudo nano /etc/nginx/sites-available/enterpriseiq.conf
```

Paste the following configuration:
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

## Step 2: Configure GitHub Repository Secrets

Automated builds and deployments are managed by GitHub Actions. Go to your repository on GitHub and navigate to **Settings > Secrets and variables > Actions > New repository secret**.

Add the following secrets:

1. **`EC2_HOST`**: The public Elastic IP of your EC2 instance (e.g. `54.210.xx.xx`).
2. **`EC2_USER`**: The SSH user, which is `ubuntu` by default on Ubuntu AMIs.
3. **`EC2_SSH_KEY`**: The complete private SSH key (`.pem` file contents) used to authenticate. Include the header and footer.
4. **`ENV_FILE_CONTENT`**: The contents of the production `.env` file that will reside at the root of the project.
   
Example `ENV_FILE_CONTENT`:
```env
ENV=production
DATABASE_URL=postgresql+asyncpg://postgres:priyank%403220@localhost:5433/enterpriseiq_aii
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1
SECRETS_ENCRYPTION_KEY=api_key_encryption
# Add other backend configurations such as OPENAI_API_KEY, GOOGLE_API_KEY, etc.
```

---

## Step 3: Run Your First Deployment

Push a commit to the `main` branch:
```bash
git add .
git commit -m "Configure Dockerized unified monolith deployment"
git push origin main
```

The GitHub Actions workflow will:
1. Build the unified Docker image with Next.js compiled static files inside.
2. Push the Docker image to GitHub Container Registry (GHCR).
3. SSH into EC2, install Docker if missing, log into GHCR, create/update `.env`, and start the container.

---

## Step 4: Verify and Troubleshoot

### Check Container Status
Connect to your EC2 instance and run:
```bash
docker ps
```
You should see `enterpriseiq-ai` running.

### Check Integrated Service Logs
To view logs from supervisor, which manages PostgreSQL, Redis, Celery, and Uvicorn inside the container:
```bash
docker logs enterpriseiq-ai
```

### Accessing PostgreSQL/Redis from the Host
Because the container maps the internal database port to host port `5433` and Redis to host port `6379`, you can query them directly from the EC2 host:
```bash
# Connect to PostgreSQL container on port 5433
psql -h localhost -p 5433 -U postgres -d enterpriseiq_aii

# Connect to Redis
redis-cli -p 6379 ping
```
*(All Postgres data is persisted under the `enterpriseiq-db-data` Docker volume on the host)*
