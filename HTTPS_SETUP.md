# HTTPS Setup Guide

This project now supports HTTPS for secure communications between client and server.

## Quick Start - Development

### 1. Generate Self-Signed Certificates

Run the certificate generation script:

```bash
chmod +x generate-certs.sh
./generate-certs.sh
```

This creates:
- `certs/cert.pem` - SSL certificate
- `certs/key.pem` - Private key

### 2. Start the Project

```bash
docker-compose up -d
```

The frontend will be available at:
- **HTTPS**: https://localhost (frontend + reverse proxy)
- **HTTP**: http://localhost (redirects to HTTPS)

### 3. Accept Self-Signed Certificate

When accessing the application, your browser will show a security warning because the certificate is self-signed. This is normal for development:
- Chrome/Edge: Click "Advanced" → "Proceed to localhost (unsafe)"
- Firefox: Click "Accept the Risk and Continue"

## Production - Let's Encrypt

For production deployments, use Let's Encrypt for free SSL certificates:

### Option 1: Using Certbot in Docker

```bash
docker run -it --rm \
  -v $(pwd)/certs:/etc/letsencrypt \
  -v $(pwd)/certs/www:/var/www/certbot \
  certbot/certbot certonly --standalone \
  -d yourdomain.com \
  -d www.yourdomain.com
```

### Option 2: Using Certbot Directly

```bash
sudo apt-get install certbot
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com
```

Then copy certificates to the project:
```bash
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem certs/cert.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem certs/key.pem
sudo chown $(whoami) certs/cert.pem certs/key.pem
```

### Option 3: Docker Compose with Certbot Auto-Renewal

Add to docker-compose.yaml:
```yaml
  certbot:
    image: certbot/certbot
    volumes:
      - ./certs:/etc/letsencrypt
      - ./certs/www:/var/www/certbot
    entrypoint: "/bin/sh -c 'trap exit TERM; while :; do certbot renew --webroot -w /var/www/certbot; sleep 12h & wait $${!}; done;'"
```

## SSL Configuration

The HTTPS configuration includes:
- **TLS 1.2 & 1.3** support
- **HSTS** (Strict-Transport-Security) header for automatic HTTPS redirection
- **Security headers** to prevent XSS, clickjacking, and MIME-type sniffing
- **HTTP/2** support for better performance

## Certificate Structure

```
certs/
├── cert.pem          # Public certificate (copy to servers)
└── key.pem           # Private key (KEEP SECURE)
```

## Environment Variables

Make sure your frontend environment variables use HTTPS URLs:

```env
VUE_APP_API_URL=https://api_app:8000
VUE_APP_ML_API_URL=https://api_ml:8001
```

These are automatically set in docker-compose.yaml.

## Troubleshooting

### Certificate not found error
```bash
# Regenerate certificates
./generate-certs.sh
docker-compose restart frontend
```

### HTTPS not working
1. Verify certificates exist: `ls -la certs/`
2. Check nginx logs: `docker-compose logs frontend`
3. Restart containers: `docker-compose down && docker-compose up -d`

### Mixed content warnings
Ensure all API calls use HTTPS URLs. Update frontend API configuration if needed.

## API Services (Internal HTTPS)

For enhanced security, the internal API services (api_app and api_ml) can also be configured for HTTPS. Currently they use HTTP internally since they're behind nginx reverse proxy on a private network. To add HTTPS to APIs:

1. Generate separate certificates for each API
2. Update the FastAPI apps to use uvicorn with SSL:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --ssl-keyfile=/path/to/key.pem --ssl-certfile=/path/to/cert.pem
   ```

## Security Notes

- **Self-signed certificates**: Suitable for development and internal networks only
- **Let's Encrypt certificates**: Free, automated, and trusted - recommended for production
- **Certificate renewal**: Set up cron jobs or use certbot's renewal service for automatic updates
- **Key protection**: Keep private keys (`key.pem`) secure and never commit them to version control
