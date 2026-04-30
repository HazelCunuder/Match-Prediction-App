#!/bin/bash

# Generate self-signed SSL certificates for development

mkdir -p certs

# Generate private key and certificate (valid for 365 days)
openssl req -x509 -newkey rsa:4096 -keyout certs/key.pem -out certs/cert.pem \
  -days 365 -nodes \
  -subj "/C=FR/ST=State/L=City/O=Organization/CN=localhost"

echo "✓ Self-signed certificates generated successfully"
echo "  Certificate: certs/cert.pem"
echo "  Private key: certs/key.pem"
echo ""
echo "Note: These are self-signed certificates for development only."
echo "For production, use Let's Encrypt or a trusted certificate authority."
