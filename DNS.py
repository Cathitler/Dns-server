from flask import Flask, request, jsonify
from dnslib.server import DNSServer
from dnslib import DNSRecord, QTYPE
import json
import threading

# Flask app for DDNS API
app = Flask(__name__)

# Dictionary to store domain-IP mappings (persistent storage in a file)
DOMAINS_FILE = "domains.json"
try:
    with open(DOMAINS_FILE, "r") as f:
        DOMAIN_IPS = json.load(f)
except FileNotFoundError:
    DOMAIN_IPS = {}

# Update domains.json file
def save_domains():
    with open(DOMAINS_FILE, "w") as f:
        json.dump(DOMAIN_IPS, f)

# Route to update a domain's IP
@app.route('/update', methods=['GET'])
def update():
    domain = request.args.get("domain")
    ip = request.args.get("ip")

    if not domain or not ip:
        return jsonify({"status": "error", "message": "Domain and IP required"}), 400

    DOMAIN_IPS[domain] = ip
    save_domains()
    return jsonify({"status": "success", "domain": domain, "ip": ip})

# Route to list all domains
@app.route('/domains', methods=['GET'])
def list_domains():
    return jsonify(DOMAIN_IPS)

# Custom DNS resolver class
class DynamicResolver:
    def resolve(self, request, handler):
        qname = str(request.q.qname).strip(".")
        qtype = QTYPE[request.q.qtype]

        # Read domain mappings from memory
        if qtype == "A" and qname in DOMAIN_IPS:
            ip = DOMAIN_IPS[qname]
            reply = request.reply()
            reply.add_answer(*DNSRecord.answer(qname, "A", ttl=300, rdata=ip))
            return reply

        # Return NXDOMAIN for unknown domains
        return request.reply()

# Function to start the DNS server
def start_dns_server():
    resolver = DynamicResolver()
    server = DNSServer(resolver, port=53, address="0.0.0.0")
    print("DNS server running on port 53...")
    server.start()

# Main entry point
if __name__ == "__main__":
    # Run the DNS server in a separate thread
    dns_thread = threading.Thread(target=start_dns_server)
    dns_thread.daemon = True
    dns_thread.start()

    # Start the Flask API server
    print("DDNS API running on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000)
