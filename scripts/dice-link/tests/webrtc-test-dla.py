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
        print("ORIGINAL ANSWER (before fixes)")
        print("="*60)
        print(f"Length: {len(answer_sdp)} chars, Line endings: {'CRLF' if '\\r\\n' in repr(answer_sdp) else 'LF'}")
        
        # ============================================
        # FIX 1: Normalize line endings to LF (Unix)
        # ============================================
        answer_sdp = answer_sdp.replace('\r\n', '\n')
        print("[FIX 1] Normalized line endings to LF")
        
        # ============================================
        # FIX 2: Change a=setup:active to a=setup:passive
        # (answerer should be passive, offerer was actpass)
        # ============================================
        if 'a=setup:active' in answer_sdp:
            answer_sdp = answer_sdp.replace('a=setup:active', 'a=setup:passive')
            print("[FIX 2] Changed 'a=setup:active' to 'a=setup:passive'")
        
        # ============================================
        # FIX 3: Move a=setup:passive to correct position
        # It should appear right after a=mid:0, before fingerprints
        # ============================================
        lines = answer_sdp.split('\n')
        setup_line = None
        setup_index = None
        mid_index = None
        
        # Find the setup line and mid line
        for i, line in enumerate(lines):
            if line.startswith('a=setup:'):
                setup_line = line
                setup_index = i
            if line.startswith('a=mid:'):
                mid_index = i
        
        # If setup line exists and is after mid, we need to move it
        if setup_line and setup_index and mid_index and setup_index > mid_index + 1:
            # Remove setup line from current position
            lines.pop(setup_index)
            # Insert it right after a=mid:0
            lines.insert(mid_index + 1, setup_line)
            answer_sdp = '\n'.join(lines)
            print(f"[FIX 3] Moved 'a=setup:passive' from line {setup_index+1} to line {mid_index+2}")
        
        # ============================================
        # FIX 4: Keep only sha-256 fingerprint (remove sha-384, sha-512)
        # ============================================
        lines = answer_sdp.split('\n')
        new_lines = []
        fingerprint_kept = False
        for line in lines:
            if line.startswith('a=fingerprint:sha-256'):
                new_lines.append(line)
                fingerprint_kept = True
            elif line.startswith('a=fingerprint:sha-384') or line.startswith('a=fingerprint:sha-512'):
                print(f"[FIX 4] Removed extra fingerprint: {line[:40]}...")
                continue  # Skip this line
            else:
                new_lines.append(line)
        answer_sdp = '\n'.join(new_lines)
        
        print("="*60)
        print("FIXED ANSWER SDP")
        print("="*60)
        for i, line in enumerate(answer_sdp.split('\n')):
            repr_line = repr(line)
            if 'setup:' in line:
                print(f"  {i+1:3}: {repr_line}  <-- SETUP LINE")
            else:
                print(f"  {i+1:3}: {repr_line}")
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
