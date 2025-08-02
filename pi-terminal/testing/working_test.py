# Test with port 5001 instead
# /baduanjin_analysis/working_test.py << 'EOF'
#!/usr/bin/env python3
from flask import Flask, jsonify
import subprocess

app = Flask(__name__)

@app.route('/')
def hello():
    # Get the correct external IP
    try:
        result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
        external_ip = result.stdout.strip()
    except:
        external_ip = "172.20.10.5"
    
    return jsonify({
        "message": "SUCCESS! Server is working!",
        "external_ip": external_ip,
        "status": "running",
        "port": 5001
    })

@app.route('/test')
def test():
    return "🎉 Connection successful from Windows!"

if __name__ == '__main__':
    print("🧪 Starting test server on port 5001...")
    print("📍 External IP: 172.20.10.5")
    print("🌐 Test URL: http://172.20.10.5:5001")
    
    try:
        app.run(host='0.0.0.0', port=5001, debug=False)
    except Exception as e:
        print(f"❌ Error: {e}")
