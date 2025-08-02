# Create simple test server
# /baduanjin_analysis/simple_test.py << 'EOF'
#!/usr/bin/env python3
from flask import Flask, jsonify
import socket

app = Flask(__name__)

@app.route('/')
def hello():
    return jsonify({
        "message": "SUCCESS! Server is working!",
        "ip": socket.gethostbyname(socket.gethostname()),
        "status": "running"
    })

@app.route('/test')
def test():
    return "Connection successful from Windows!"

if __name__ == '__main__':
    print("🧪 Starting simple test server...")
    print(f"📍 Server IP: {socket.gethostbyname(socket.gethostname())}")
    print("🌐 Starting on port 5000...")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=True)
    except Exception as e:
        print(f"❌ Error starting server: {e}")

