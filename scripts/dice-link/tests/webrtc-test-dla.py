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

async def handle_generate_offer(request):
    """Generate offer and send to browser"""
    global pc, test_channel
    
    try:
        # Create peer connection
        pc = RTCPeerConnection()
        test_channel = TestDataChannel()
        
        # Create data channel
        dc = pc.createDataChannel('test-channel')
        
        @dc.on("open")
        async def on_open():
            print("[WebRTC Test] Data channel opened")
        
        @dc.on("message")
        def on_message(message):
            print(f"[WebRTC Test] Received from browser: {message}")
            test_channel.messages.append({"from": "browser", "text": message})
        
        # Create offer
        offer = await pc.createOffer()
        await pc.setLocalDescription(offer)
        
        offer_sdp = pc.localDescription.sdp
        
        print("\n" + "="*60)
        print("DLA-GENERATED OFFER (to send to browser)")
        print("="*60)
        print(f"Offer length: {len(offer_sdp)} characters")
        print("\n--- FULL OFFER SDP ---")
        for i, line in enumerate(offer_sdp.split('\n')):
            print(f"  {i+1:3}: {repr(line)}")
        print("--- END OFFER SDP ---\n")
        
        return web.json_response({"offer": offer_sdp})
    
    except Exception as e:
        print(f"[WebRTC Test] Error generating offer: {e}")
        import traceback
        print(f"[WebRTC Test] Traceback: {traceback.format_exc()}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_answer(request):
    """Receive answer from browser, set as remote description"""
    global pc
    
    try:
        data = await request.json()
        answer_sdp = data.get("answer")
        
        if not answer_sdp:
            return web.json_response({"error": "No answer provided"}, status=400)
        
        if not pc:
            return web.json_response({"error": "No peer connection created. Generate offer first."}, status=400)
        
        # Normalize answer line endings to LF
        answer_sdp = answer_sdp.replace('\r\n', '\n')
        
        print("\n" + "="*60)
        print("BROWSER-GENERATED ANSWER ANALYSIS (THIS IS WHAT WE NEED TO COPY!)")
        print("="*60)
        print(f"Answer length: {len(answer_sdp)} characters")
        print("\n--- FULL ANSWER SDP ---")
        for i, line in enumerate(answer_sdp.split('\n')):
            print(f"  {i+1:3}: {repr(line)}")
        print("--- END ANSWER SDP ---\n")
        print("\n--- BROWSER ANSWER DETAILS ---")
        print(f"Hex dump (first 200 bytes): {answer_sdp[:200].encode().hex()}")
        print(f"Repr (first 150 chars): {repr(answer_sdp[:150])}")
        print("="*60 + "\n")
        
        # Set remote description
        answer = RTCSessionDescription(sdp=answer_sdp, type="answer")
        await pc.setRemoteDescription(answer)
        
        print("[WebRTC Test] Answer accepted successfully!")
        
        return web.json_response({"status": "success"})
    
    except Exception as e:
        print(f"[WebRTC Test] Error accepting answer: {e}")
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
    app.router.add_route('OPTIONS', '/api/answer', handle_options)
    app.router.add_route('OPTIONS', '/api/send', handle_options)
    app.router.add_route('OPTIONS', '/api/status', handle_options)
    app.router.add_get('/api/offer', handle_generate_offer)
    app.router.add_post('/api/answer', handle_answer)
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
