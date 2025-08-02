# test_cors.py - Simple CORS test
# Save this as test_cors.py and run it to test CORS

from flask import Flask, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit

app = Flask(__name__)
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*")

@app.after_request
def after_request(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    return response

@app.route('/test')
def test():
    return jsonify({"message": "CORS test working", "status": "ok"})

@socketio.on('connect')
def handle_connect():
    print('✅ Test client connected')
    emit('response', {'data': 'CORS working!'})

if __name__ == '__main__':
    print("🧪 CORS Test Server on port 5002")
    socketio.run(app, host='0.0.0.0', port=5002, debug=True)