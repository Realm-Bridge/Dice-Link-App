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
        
        raw_offer_sdp = pc.localDescription.sdp
        
        print("\n" + "="*60)
        print("AIORTC RAW OFFER (before fixing)")
        print("="*60)
        for i, line in enumerate(raw_offer_sdp.split('\n')):
            print(f"  {i+1:3}: {repr(line)}")
        print("="*60 + "\n")
        
        # ============================================
        # FIX THE OFFER SDP
        # aiortc generates SDP that browsers reject
        # We need to reformat it to match browser expectations
        # ============================================
        
        # Normalize line endings to LF
        raw_offer_sdp = raw_offer_sdp.replace('\r\n', '\n').replace('\r', '\n')
        
        # Parse aiortc's offer
        lines = raw_offer_sdp.strip().split('\n')
        
        # Extract components
        v_line = None
        o_line = None
        s_line = None
        t_line = None
        group_line = None
        msid_semantic = None
        m_line = None
        c_line = None
        mid_line = None
        sctp_port = None
        max_message_size = None
        ice_ufrag = None
        ice_pwd = None
        fingerprint_sha256 = None
        setup_line = None
        candidates = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('v='):
                v_line = line
            elif line.startswith('o='):
                o_line = line
            elif line.startswith('s='):
                s_line = line
            elif line.startswith('t='):
                t_line = line
            elif line.startswith('a=group:'):
                group_line = line
            elif line.startswith('a=msid-semantic:'):
                msid_semantic = line
            elif line.startswith('m='):
                m_line = line
            elif line.startswith('c='):
                c_line = line
            elif line.startswith('a=mid:'):
                mid_line = line
            elif line.startswith('a=sctp-port:'):
                sctp_port = line
            elif line.startswith('a=max-message-size:'):
                max_message_size = line
            elif line.startswith('a=ice-ufrag:'):
                ice_ufrag = line
            elif line.startswith('a=ice-pwd:'):
                ice_pwd = line
            elif line.startswith('a=fingerprint:sha-256'):
                fingerprint_sha256 = line
            elif line.startswith('a=setup:'):
                setup_line = line
            elif line.startswith('a=candidate:'):
                candidates.append(line)
        
        # Build offer in correct order for browsers
        # Session level: v, o, s, t, a=group, a=extmap-allow-mixed (optional), a=msid-semantic
        # Media level: m, c, a=ice-ufrag, a=ice-pwd, a=ice-options, a=fingerprint, a=setup, a=mid, a=sctp-port, a=max-message-size, candidates
        
        fixed_lines = []
        
        # Session section
        fixed_lines.append(v_line or 'v=0')
        fixed_lines.append(o_line or 'o=- 0 0 IN IP4 0.0.0.0')
        fixed_lines.append(s_line or 's=-')
        fixed_lines.append(t_line or 't=0 0')
        if group_line:
            fixed_lines.append(group_line)
        fixed_lines.append('a=extmap-allow-mixed')
        # Use simple msid-semantic without the asterisk
        fixed_lines.append('a=msid-semantic: WMS')
        
        # Media section - use port 9 (standard for trickle ICE)
        fixed_lines.append('m=application 9 UDP/DTLS/SCTP webrtc-datachannel')
        
        # Use IPv4 0.0.0.0 (browsers prefer this)
        fixed_lines.append('c=IN IP4 0.0.0.0')
        
        # ICE credentials (required, come early)
        if ice_ufrag:
            fixed_lines.append(ice_ufrag)
        if ice_pwd:
            fixed_lines.append(ice_pwd)
        
        # ice-options for trickle ICE
        fixed_lines.append('a=ice-options:trickle')
        
        # Fingerprint (only sha-256)
        if fingerprint_sha256:
            fixed_lines.append(fingerprint_sha256)
        
        # Setup (offerer uses actpass)
        fixed_lines.append('a=setup:actpass')
        
        # Media ID
        if mid_line:
            fixed_lines.append(mid_line)
        
        # SCTP settings
        if sctp_port:
            fixed_lines.append(sctp_port)
        fixed_lines.append('a=max-message-size:262144')
        
        # Join with LF and add trailing LF
        offer_sdp = '\n'.join(fixed_lines) + '\n'
        
        print("\n" + "="*60)
        print("FIXED OFFER (to send to browser)")
        print("="*60)
        print(f"Offer length: {len(offer_sdp)} characters")
        print("\n--- FIXED OFFER SDP ---")
        for i, line in enumerate(offer_sdp.split('\n')):
            if line:
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
