#!/bin/bash
# Generate self-signed SSL certificate for development

mkdir -p ssl

openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/key.pem \
    -out ssl/cert.pem \
    -subj "/C=GH/ST=Accra/L=Accra/O=NFCC/CN=api.nfcc.gov.gh"

echo "✅ Self-signed SSL certificate generated"
echo "   Certificate: ssl/cert.pem"
echo "   Private key: ssl/key.pem"
