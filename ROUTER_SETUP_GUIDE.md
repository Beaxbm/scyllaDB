# 🌐 Router Setup for DuckDNS Remote Access

## Complete Guide for `gaugescylladb.duckdns.org`

### 📋 Quick Setup Checklist

- [ ] Find your router's admin panel
- [ ] Get your computer's local IP address
- [ ] Configure port forwarding rules
- [ ] Update DuckDNS with your public IP
- [ ] Test external connectivity
- [ ] Set up automatic IP updates

---

## 🔧 Step 1: Find Your Router Admin Panel

### Method 1: Automatic Detection
```bash
# Find your router's IP (gateway)
netstat -rn | grep default
```

### Method 2: Network Settings
- **macOS**: System Preferences → Network → Advanced → TCP/IP
- **Common Router IPs**:
  - `192.168.1.1` (Most common)
  - `192.168.0.1` (Alternative)
  - `10.0.0.1` (Some ISPs)
  - `192.168.100.1` (Fiber connections)

### Access Your Router
1. Open browser and go to your router IP
2. **Common login credentials**:
   - Username: `admin`, Password: `admin`
   - Username: `admin`, Password: `password` 
   - Username: `admin`, Password: (blank)
   - Check router label for default credentials

---

## 🖥️ Step 2: Get Your Computer's Local IP

Your IoT services need to be accessible from the router. Find your Mac's local IP:

```bash
# Get your Mac's local IP address
ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{print $2}'
```

**Example output**: `192.168.1.100`

**Write this down - you'll need it for port forwarding rules!**

---

## 🔀 Step 3: Configure Port Forwarding Rules

Navigate to **Port Forwarding** section in your router (usually under Advanced → NAT → Port Forwarding)

### Required Port Forwarding Rules:

#### Rule 1: MQTT Real-time Data
```
Service Name: IoT-MQTT
Protocol: TCP
External Port: 1883
Internal IP: [Your Mac IP from Step 2]
Internal Port: 1883
Description: Real-time sensor data (MQTT)
```

#### Rule 2: ScyllaDB API
```
Service Name: IoT-API
Protocol: TCP  
External Port: 8001
Internal IP: [Your Mac IP from Step 2]
Internal Port: 8001
Description: Historical data API (REST)
```

#### Rule 3: Home Assistant UI (Optional)
```
Service Name: IoT-Dashboard
Protocol: TCP
External Port: 8123
Internal IP: [Your Mac IP from Step 2] 
Internal Port: 8123
Description: IoT management dashboard
```

#### Rule 4: Zigbee2MQTT UI (Optional)
```
Service Name: Zigbee-UI
Protocol: TCP
External Port: 8080
Internal IP: [Your Mac IP from Step 2]
Internal Port: 8080  
Description: Zigbee device management
```

### Router-Specific Instructions:

#### **TP-Link Routers**
1. Advanced → NAT Forwarding → Port Forwarding
2. Click "Add" for each rule
3. Set Protocol: TCP
4. External/Internal ports as above
5. Save & Restart router

#### **Netgear Routers**  
1. Advanced → Dynamic DNS → Port Forwarding/Port Triggering
2. Add Custom Service
3. Use TCP protocol for all rules
4. Apply settings

#### **Linksys Routers**
1. Smart Wi-Fi Tools → Port Range Forward  
2. Add new range for each service
3. Device IP = Your Mac's local IP
4. Save Configuration

#### **ASUS Routers**
1. Adaptive QoS → Port Forwarding
2. Enable Port Forwarding: Yes
3. Add each service with TCP protocol
4. Apply settings

---

## 🌐 Step 4: Update DuckDNS Configuration

### Get Your Public IP
```bash
# Check your current public IP
curl ifconfig.me
```

### Update DuckDNS (Manual)
1. Go to **https://duckdns.org**
2. Sign in to your account  
3. Find your domain: `gaugescylladb`
4. Click "update ip" or enter your public IP manually
5. Save changes

### Automatic IP Updates (Recommended)
Create a script to keep your IP updated:

```bash
# Create update script
nano ~/update_duckdns.sh
```

Add this content (replace YOUR_TOKEN with your actual DuckDNS token):
```bash
#!/bin/bash
# DuckDNS Auto-Update Script for gaugescylladb.duckdns.org

DOMAIN="gaugescylladb"
TOKEN="YOUR_DUCKDNS_TOKEN_HERE"  # Get from duckdns.org account page

# Get current public IP
PUBLIC_IP=$(curl -s ifconfig.me)

# Update DuckDNS
RESPONSE=$(curl -s "https://www.duckdns.org/update?domains=${DOMAIN}&token=${TOKEN}&ip=${PUBLIC_IP}")

# Log the update
echo "$(date): Updated gaugescylladb.duckdns.org to IP ${PUBLIC_IP} - Response: ${RESPONSE}" >> ~/duckdns.log

if [ "$RESPONSE" = "OK" ]; then
    echo "✅ DuckDNS updated successfully: ${PUBLIC_IP}"
else
    echo "❌ DuckDNS update failed: ${RESPONSE}"
fi
```

Make it executable:
```bash
chmod +x ~/update_duckdns.sh
```

### Set Up Automatic Updates (Cron Job)
```bash
# Edit crontab
crontab -e

# Add this line to update every 5 minutes:
*/5 * * * * /Users/$(whoami)/update_duckdns.sh

# Or update every hour:
0 * * * * /Users/$(whoami)/update_duckdns.sh
```

---

## 🧪 Step 5: Test External Connectivity

### Test From External Network
**Important**: These tests must be done from OUTSIDE your local network (use mobile hotspot or ask someone else to test)

#### Test 1: MQTT Connection
```bash
# From external network, test MQTT
telnet gaugescylladb.duckdns.org 1883

# Should connect successfully
# Press Ctrl+C to exit
```

#### Test 2: API Health Check  
```bash
# Test API endpoint
curl http://gaugescylladb.duckdns.org:8001/health

# Expected response:
# {"status":"healthy","scylla":"connected"}
```

#### Test 3: Get Live Sensor Data
```bash
# Test real-time sensor access
curl "http://gaugescylladb.duckdns.org:8001/sensors" | head -20

# Should return JSON with sensor list
```

### Test From Your Network (Verification)
```bash
# Verify local services still work
curl http://localhost:8001/health
python3 working_mqtt_client.py  # Should connect to localhost:1883
```

---

## 🔍 Step 6: Troubleshooting Common Issues

### Issue 1: "Connection Refused" from External Network
**Cause**: Port forwarding not working
**Solutions**:
- Double-check router port forwarding rules
- Ensure internal IP address is correct
- Restart router after configuration
- Check if ISP blocks certain ports

### Issue 2: "Domain Not Found" 
**Cause**: DuckDNS not updated or DNS propagation
**Solutions**:
- Verify DuckDNS domain shows your current public IP
- Run manual update: `~/update_duckdns.sh`
- Wait 5-10 minutes for DNS propagation
- Test with direct IP: `curl http://YOUR_PUBLIC_IP:8001/health`

### Issue 3: "Timeout" Errors
**Cause**: Firewall or ISP port blocking  
**Solutions**:
- Check macOS firewall settings (System Preferences → Security)
- Try different external ports (8001 → 8002, 1883 → 1884)
- Contact ISP about port blocking policies
- Test with port checker: `telnet gaugescylladb.duckdns.org 8001`

### Issue 4: Works Sometimes, Not Others
**Cause**: Dynamic IP changes
**Solutions**:
- Ensure cron job is running: `crontab -l`
- Check update log: `tail ~/duckdns.log`
- Verify router doesn't change your Mac's internal IP
- Consider setting static IP for your Mac

---

## 🔒 Step 7: Security Recommendations

### Basic Security (Minimum)
1. **Change router admin password** from default
2. **Enable WPA3/WPA2** on WiFi if not already
3. **Disable WPS** (WiFi Protected Setup)
4. **Update router firmware** to latest version

### Advanced Security (Production)  
1. **Add authentication** to MQTT broker:
```bash
# In mosquitto container, add password file
docker exec mosquitto mosquitto_passwd -c /mosquitto/config/passwd hexahealth
```

2. **Set up SSL/TLS** certificates:
```bash  
# Use Let's Encrypt for free SSL
# Configure MQTT on port 8883 (SSL)
# Configure API with HTTPS
```

3. **Rate limiting** in router firewall
4. **VPN access** for sensitive operations

---

## 📱 Step 8: Mobile Testing Script

Create this script to test from mobile hotspot:

```bash
# Save as test_remote_access.sh
#!/bin/bash

DOMAIN="gaugescylladb.duckdns.org"

echo "🧪 Testing Remote Access to $DOMAIN"
echo "=================================="

echo "📡 Testing DNS resolution..."
nslookup $DOMAIN

echo -e "\n🏥 Testing API Health..."
curl -s -w "\nResponse time: %{time_total}s\n" http://$DOMAIN:8001/health

echo -e "\n📊 Testing Sensor Data..."  
curl -s http://$DOMAIN:8001/sensors | head -5

echo -e "\n🔌 Testing MQTT Connection..."
timeout 5 bash -c "</dev/tcp/$DOMAIN/1883" && echo "✅ MQTT port open" || echo "❌ MQTT connection failed"

echo -e "\n🌐 Testing Web UI (optional)..."
curl -s -o /dev/null -w "Home Assistant: %{http_code}\n" http://$DOMAIN:8123

echo -e "\n✅ Remote access test complete!"
```

---

## 🎯 Final Verification Checklist

### ✅ Router Configuration
- [ ] Port forwarding rules created for ports 1883, 8001, 8123
- [ ] Internal IP points to your Mac 
- [ ] Router restarted after configuration
- [ ] Admin password changed from default

### ✅ DuckDNS Configuration  
- [ ] Domain `gaugescylladb` points to your public IP
- [ ] Automatic update script created and tested
- [ ] Cron job scheduled for regular updates
- [ ] Update log file created: `~/duckdns.log`

### ✅ External Testing
- [ ] API health check works from external network
- [ ] MQTT connection succeeds from outside network
- [ ] Sensor data accessible via `gaugescylladb.duckdns.org:8001`
- [ ] Local services still work (localhost testing)

### ✅ HexaHealth Integration Ready
- [ ] Remote data manager can connect: `gaugescylladb.duckdns.org:1883`
- [ ] REST API accessible: `http://gaugescylladb.duckdns.org:8001`
- [ ] Real-time sensor data streaming successfully
- [ ] Documentation provided to development team

---

## 🚀 Next Steps for HexaHealth Team

Once router setup is complete, your team can:

1. **Use the integration code**:
   ```python
   # Update environment in hexahealth_simple_integration.py
   iot_client = HexaHealthIoTClient(environment="development")
   # Will connect to gaugescylladb.duckdns.org automatically
   ```

2. **Access real-time data from anywhere**:
   - MQTT: `gaugescylladb.duckdns.org:1883`
   - API: `http://gaugescylladb.duckdns.org:8001`

3. **Integrate with your product**:
   - Use provided React components
   - Connect Django/Flask backend
   - Implement health monitoring features

**Your IoT infrastructure will be globally accessible for HexaHealth product integration!** 🌍🏥