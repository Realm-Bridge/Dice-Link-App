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
        
        # Normalize offer line endings to LF
        offer_sdp = offer_sdp.replace('\r\n', '\n')
        
        print("\n" + "="*60)
        print("OFFER ANALYSIS")
        print("="*60)
        print(f"Offer length: {len(offer_sdp)} characters")
        print("\n--- FULL OFFER SDP ---")
        for i, line in enumerate(offer_sdp.split('\n')):
            print(f"  {i+1:3}: {repr(line)}")
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
        
        aiortc_sdp = pc.localDescription.sdp
        
        print("="*60)
        print("AIORTC ORIGINAL ANSWER")
        print("="*60)
        for i, line in enumerate(aiortc_sdp.split('\n')):
            print(f"  {i+1:3}: {repr(line)}")
        print("="*60 + "\n")
        
        # ============================================
        # NEW APPROACH: Build answer SDP manually
        # Extract only what we need from aiortc (ice credentials, fingerprint)
        # and construct SDP with exact same structure as offer
        # ============================================
        
        # Parse aiortc's answer to extract what we need
        aiortc_lines = aiortc_sdp.replace('\r\n', '\n').split('\n')
        
        aiortc_ice_ufrag = None
        aiortc_ice_pwd = None
        aiortc_fingerprint_sha256 = None
        aiortc_o_line = None
        
        for line in aiortc_lines:
            if line.startswith('o='):
                aiortc_o_line = line
            elif line.startswith('a=ice-ufrag:'):
                aiortc_ice_ufrag = line
            elif line.startswith('a=ice-pwd:'):
                aiortc_ice_pwd = line
            elif line.startswith('a=fingerprint:sha-256'):
                aiortc_fingerprint_sha256 = line
        
        print("Extracted from aiortc:")
        print(f"  o-line: {aiortc_o_line}")
        print(f"  ice-ufrag: {aiortc_ice_ufrag}")
        print(f"  ice-pwd: {aiortc_ice_pwd}")
        print(f"  fingerprint: {aiortc_fingerprint_sha256[:60]}..." if aiortc_fingerprint_sha256 else "  fingerprint: None")
        
        # Parse offer to get structure and values we need to echo
        offer_lines = offer_sdp.split('\n')
        
        offer_o_line = None
        offer_group = None
        offer_extmap_allow_mixed = None
        offer_msid_semantic = None
        offer_m_line = None
        offer_c_line = None
        offer_ice_options = None
        offer_fingerprint = None
        offer_mid = None
        offer_sctp_port = None
        offer_max_message_size = None
        
        for line in offer_lines:
            if line.startswith('o='):
                offer_o_line = line
            elif line.startswith('a=group:'):
                offer_group = line
            elif line.startswith('a=extmap-allow-mixed'):
                offer_extmap_allow_mixed = line
            elif line.startswith('a=msid-semantic:'):
                offer_msid_semantic = line
            elif line.startswith('m='):
                offer_m_line = line
            elif line.startswith('c='):
                offer_c_line = line
            elif line.startswith('a=ice-options:'):
                offer_ice_options = line
            elif line.startswith('a=fingerprint:'):
                offer_fingerprint = line
            elif line.startswith('a=mid:'):
                offer_mid = line
            elif line.startswith('a=sctp-port:'):
                offer_sctp_port = line
            elif line.startswith('a=max-message-size:'):
                offer_max_message_size = line
        
        # Build answer SDP line by line, matching offer structure exactly
        # MINIMAL required attributes only - remove anything that causes parsing errors
        # Order matters!
        
        answer_lines = []
        
        # Session level
        answer_lines.append('v=0')
        answer_lines.append(aiortc_o_line or 'o=- 0 0 IN IP4 0.0.0.0')
        answer_lines.append('s=-')
        answer_lines.append('t=0 0')
        
        # Session-level attributes (these go BEFORE media section)
        if offer_group:
            answer_lines.append(offer_group)
        
        if offer_extmap_allow_mixed:
            answer_lines.append(offer_extmap_allow_mixed)
        
        if offer_msid_semantic:
            answer_lines.append(offer_msid_semantic)
        
        # Media section
        answer_lines.append('m=application 9 UDP/DTLS/SCTP webrtc-datachannel')
        
        # Connection line (must come after m=)
        if offer_c_line:
            answer_lines.append(offer_c_line)
        
        # Media-level attributes in order
        if aiortc_ice_ufrag:
            answer_lines.append(aiortc_ice_ufrag)
        
        if aiortc_ice_pwd:
            answer_lines.append(aiortc_ice_pwd)
        
        # Ice options
        if offer_ice_options:
            answer_lines.append(offer_ice_options)
        
        # Fingerprint (must come before setup)
        if aiortc_fingerprint_sha256:
            answer_lines.append(aiortc_fingerprint_sha256)
        
        # Setup (answer sets this to passive since offer was actpass)
        answer_lines.append('a=setup:passive')
        
        # Media ID
        if offer_mid:
            answer_lines.append(offer_mid)
        
        # SCTP port
        if offer_sctp_port:
            answer_lines.append(offer_sctp_port)
        
        # Max message size (MUST use the value from the offer, not aiortc's)
        if offer_max_message_size:
            answer_lines.append(offer_max_message_size)
        
        # Join with LF and add trailing LF (match offer's line ending style)
        answer_sdp = '\n'.join(answer_lines) + '\n'
        
        print("\n" + "="*60)
        print("MANUALLY CONSTRUCTED ANSWER SDP")
        print("="*60)
        print(f"Length: {len(answer_sdp)} bytes")
        print(f"Hex dump (first 200 bytes): {answer_sdp[:200].encode().hex()}")
        print(f"Repr (first 150 chars): {repr(answer_sdp[:150])}")
        print("\nFinal answer lines:")
        for i, line in enumerate(answer_sdp.split('\n')):
            if line or i < len(answer_sdp.split('\n')) - 1:  # Skip the final empty line from split
                print(f"  {i+1}: {repr(line)}")
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
