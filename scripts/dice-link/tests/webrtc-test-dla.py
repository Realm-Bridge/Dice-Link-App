"""
WebRTC Test App - DLA Side (Python)
Tests if WebRTC Data Channels can bypass PNA restrictions
Runs on localhost:8080, generates WebRTC offer for browser to paste
"""

import asyncio
import json
from aiohttp import web
from aiortc import RTCPeerConnection, RTCSessionDescription
from aiortc.contrib.media import MediaStreamTrack

class TestDataChannel:
    def __init__(self):
        self.messages = []
    
    async def on_datachannel(self, channel):
        print(f"[WebRTC Test] Data channel opened: {channel.label}")
        
        @channel.on("message")
        def on_message(message):
            print(f"[WebRTC Test] Received from browser: {message}")
            self.messages.append({"from": "browser", "text": message})
        
        @channel.on("close")
        def on_close():
            print("[WebRTC Test] Data channel closed")
        
        # Send a test message back
        await asyncio.sleep(0.5)
        test_msg = "Hello from DLA test app!"
        channel.send(test_msg)
        print(f"[WebRTC Test] Sent to browser: {test_msg}")
        self.messages.append({"from": "dla", "text": test_msg})

async def handle_offer(request):
    """Receive offer from browser, create answer"""
    global pc, test_channel
    
    try:
        data = await request.json()
        offer_sdp = data.get("offer")
        
        if not offer_sdp:
            return web.json_response({"error": "No offer provided"}, status=400)
        
        print("\n" + "="*60)
        print("OFFER ANALYSIS")
        print("="*60)
        print(f"Offer length: {len(offer_sdp)} characters")
        print(f"Line ending type: {'CRLF (Windows)' if chr(13)+chr(10) in offer_sdp else 'LF (Unix)'}")
        print("\n--- FULL OFFER SDP ---")
        for i, line in enumerate(offer_sdp.split('\n')):
            # Show line number, content, and any trailing characters
            repr_line = repr(line)
            print(f"  {i+1:3}: {repr_line}")
        print("--- END OFFER SDP ---\n")
        
        # Create peer connection
        pc = RTCPeerConnection()
        test_channel = TestDataChannel()
        
        # Handle incoming data channels from browser
        @pc.on("datachannel")
        def on_datachannel(channel):
            asyncio.create_task(test_channel.on_datachannel(channel))
        
        # Set remote description
        offer = RTCSessionDescription(sdp=offer_sdp, type="offer")
        await pc.setRemoteDescription(offer)
        
        # Create answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        answer_sdp = pc.localDescription.sdp
        
        print("="*60)
        print("ANSWER ANALYSIS")
        print("="*60)
        print(f"Answer length: {len(answer_sdp)} characters")
        print(f"Line ending type: {'CRLF (Windows)' if chr(13)+chr(10) in answer_sdp else 'LF (Unix)'}")
        print("\n--- FULL ANSWER SDP ---")
        for i, line in enumerate(answer_sdp.split('\n')):
            repr_line = repr(line)
            # Highlight potentially problematic lines
            if 'setup:' in line:
                print(f"  {i+1:3}: {repr_line}  <-- SETUP LINE")
            else:
                print(f"  {i+1:3}: {repr_line}")
        print("--- END ANSWER SDP ---\n")
        
        # Check for specific issues
        print("="*60)
        print("ISSUE CHECKS")
        print("="*60)
        if 'a=setup:active' in answer_sdp:
            print("  [!] Found 'a=setup:active' - may be rejected by some browsers")
        if 'a=setup:actpass' in answer_sdp:
            print("  [OK] Found 'a=setup:actpass'")
        if 'a=setup:passive' in answer_sdp:
            print("  [OK] Found 'a=setup:passive'")
        
        # Check line ending consistency
        crlf_count = answer_sdp.count('\r\n')
        lf_only_count = answer_sdp.count('\n') - crlf_count
        print(f"  Line endings: {crlf_count} CRLF, {lf_only_count} LF-only")
        if crlf_count > 0 and lf_only_count > 0:
            print("  [!] MIXED LINE ENDINGS - this could cause parsing issues!")
        print("="*60 + "\n")
        
        return web.json_response({"answer": answer_sdp})
    
    except Exception as e:
        print(f"[WebRTC Test] Error: {e}")
        import traceback
        print(f"[WebRTC Test] Traceback: {traceback.format_exc()}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_send_message(request):
    """Send a test message through data channel"""
    global pc
    
    try:
        data = await request.json()
        message = data.get("message", "Test message")
        
        if pc and pc.dataChannels:
            for channel in pc.dataChannels:
                channel.send(message)
                print(f"[WebRTC Test] Sent via data channel: {message}")
            return web.json_response({"status": "sent"})
        else:
            return web.json_response({"error": "No data channel available"}, status=400)
    
    except Exception as e:
        print(f"[WebRTC Test] Error: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_status(request):
    """Get current connection status"""
    global pc, test_channel
    
    if not pc:
        return web.json_response({
            "status": "disconnected",
            "messages": []
        })
    
    return web.json_response({
        "status": pc.connectionState if pc else "disconnected",
        "messages": test_channel.messages if test_channel else []
    })

async def handle_options(request):
    """Handle CORS preflight requests"""
    return web.Response(
        status=200,
        headers={
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type',
        }
    )

async def create_app():
    """Create the test app"""
    app = web.Application()
    
    # Add CORS middleware to allow requests from file:// origins
    @web.middleware
    async def cors_middleware(request, handler):
        # Handle preflight OPTIONS requests
        if request.method == 'OPTIONS':
            return web.Response(
                status=200,
                headers={
                    'Access-Control-Allow-Origin': '*',
                    'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, OPTIONS',
                    'Access-Control-Allow-Headers': 'Content-Type',
                }
            )
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response
    
    app.middlewares.append(cors_middleware)
    
    # Routes
    app.router.add_route('OPTIONS', '/api/offer', handle_options)
    app.router.add_route('OPTIONS', '/api/send', handle_options)
    app.router.add_route('OPTIONS', '/api/status', handle_options)
    app.router.add_post('/api/offer', handle_offer)
    app.router.add_post('/api/send', handle_send_message)
    app.router.add_get('/api/status', handle_status)
    
    return app

# Global variables
pc = None
test_channel = None

if __name__ == '__main__':
    print("\n" + "="*50)
    print("WebRTC Test App - DLA Side")
    print("="*50)
    print("Starting on http://localhost:8080")
    print("This app receives WebRTC offers from the browser")
    print("="*50 + "\n")
    
    app = asyncio.run(create_app())
    web.run_app(app, host='localhost', port=8080)
