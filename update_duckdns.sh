#!/bin/bash
# DuckDNS Auto-Update Script for gaugescylladb.duckdns.org
# Beatriz's IoT Infrastructure Remote Access

DOMAIN="gaugescylladb"
TOKEN="8da13fbb-5c6d-414f-b6ab-d8c32eef57aa" 

# Get current public IPv4 address (force IPv4)
PUBLIC_IP=$(curl -s -4 ifconfig.me)

# Validate IP format
if [[ $PUBLIC_IP =~ ^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$ ]]; then
    # Update DuckDNS
    RESPONSE=$(curl -s "https://www.duckdns.org/update?domains=${DOMAIN}&token=${TOKEN}&ip=${PUBLIC_IP}")
    
    # Log the update
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    echo "$TIMESTAMP: Updated gaugescylladb.duckdns.org to IP $PUBLIC_IP - Response: $RESPONSE" >> ~/duckdns.log
    
    if [ "$RESPONSE" = "OK" ]; then
        echo "✅ DuckDNS updated successfully: $PUBLIC_IP"
    else
        echo "❌ DuckDNS update failed: $RESPONSE"
        exit 1
    fi
else
    echo "❌ Failed to get valid IPv4 address. Got: $PUBLIC_IP"
    echo "$(date): Failed to get valid IP - Got: $PUBLIC_IP" >> ~/duckdns.log
    exit 1
fi

