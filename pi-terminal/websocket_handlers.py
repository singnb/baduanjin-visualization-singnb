"""
websocket_handlers.py - WebSocket Event Handlers
Note: These are disabled for ngrok compatibility, using HTTP polling instead
"""

from flask_socketio import emit

def register_websocket_handlers(socketio, web_analyzer):
    """Register WebSocket event handlers (mostly disabled for ngrok)"""
    
    # === MINIMAL WEBSOCKET HANDLERS ===
    # These are kept minimal since we're using HTTP polling for ngrok compatibility
    
    @socketio.on('connect')
    def handle_connect():
        """Handle client connection - minimal for ngrok compatibility"""
        try:
            print('✅ Client connected to Pi WebSocket (HTTP polling mode)')
            emit('status', {
                'connected': True,
                'mode': 'http_polling',
                'message': 'Connected to Pi (WebSocket disabled for ngrok compatibility)'
            })
            return True
        except Exception as e:
            print(f"❌ Error in connect handler: {e}")
            return False

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        print('🔌 Client disconnected from Pi WebSocket')

    @socketio.on_error_default
    def default_error_handler(e):
        """Handle Socket.IO errors"""
        print(f"❌ Socket.IO error: {e}")
        return False

    # === DISABLED WEBSOCKET EVENTS ===
    # These events are commented out because they cause issues with ngrok
    # The frontend should use HTTP polling endpoints instead
    
    # @socketio.on('connect_error')
    # def handle_connect_error():
    #     """Handle connection errors"""
    #     print('❌ Connection error occurred')

    # @socketio.on('start_stream')
    # def handle_start_stream():
    #     """Handle start stream request"""
    #     success = web_analyzer.start_stream()
    #     emit('stream_status', {'started': success})

    # @socketio.on('stop_stream')
    # def handle_stop_stream():
    #     """Handle stop stream request"""
    #     web_analyzer.stop_stream()
    #     emit('stream_status', {'started': False})

    # === FRAME EMISSION (DISABLED FOR NGROK) ===
    # Frame emission via WebSocket is disabled for ngrok compatibility
    # Frontend should use /api/current_frame endpoint instead
    
    def emit_frame_safely(frame_data):
        """Safely emit frame data - DISABLED for ngrok compatibility"""
        # This function is disabled because it causes "Invalid frame header" errors with ngrok
        # Frontend should use HTTP polling via /api/current_frame instead
        try:
            # Uncomment only if you want to try WebSocket (not recommended with ngrok)
            # socketio.emit('frame_update', frame_data)
            return True
        except Exception as e:
            print(f"❌ Error emitting frame (disabled for ngrok): {e}")
            return False
    
    # Make emit function available to other modules (though it's disabled)
    web_analyzer.emit_frame_safely = emit_frame_safely
    
    print("⚠️ WebSocket handlers registered but mostly disabled for ngrok compatibility")
    print("💡 Frontend should use HTTP polling endpoints:")
    print("   - GET /api/current_frame for live frames")
    print("   - GET /api/status for status updates")
    print("   - GET /api/stream-events for event polling")
    
    return socketio

def emit_frame_safely(frame_data):
    """Standalone frame emission function - DISABLED for ngrok"""
    # This is a standalone version that can be imported by other modules
    # It's disabled for ngrok compatibility
    return False  # Always return False to indicate emission is disabled