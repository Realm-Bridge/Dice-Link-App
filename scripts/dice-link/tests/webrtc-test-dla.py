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
        # ============================================
        if 'a=setup:active' in answer_sdp:
            answer_sdp = answer_sdp.replace('a=setup:active', 'a=setup:passive')
            print("[FIX 2] Changed 'a=setup:active' to 'a=setup:passive'")
        
        # ============================================
        # FIX 3: Keep only sha-256 fingerprint
        # ============================================
        lines = answer_sdp.split('\n')
        new_lines = []
        for line in lines:
            if line.startswith('a=fingerprint:sha-384') or line.startswith('a=fingerprint:sha-512'):
                print(f"[FIX 3] Removed extra fingerprint: {line[:40]}...")
                continue
            new_lines.append(line)
        answer_sdp = '\n'.join(new_lines)
        
        # ============================================
        # FIX 4: Reorder SDP to match browser's expected order
        # Order should be: c=, ice-ufrag, ice-pwd, fingerprint, setup, mid, sctp-port, max-message-size, candidates, end-of-candidates
        # ============================================
        lines = answer_sdp.split('\n')
        
        # Separate session-level and media-level lines
        session_lines = []  # v=, o=, s=, t=, a=group, a=msid-semantic
        media_line = None   # m=
        connection_line = None  # c=
        ice_ufrag = None
        ice_pwd = None
        fingerprint = None
        setup_line = None
        mid_line = None
        sctp_port = None
        max_message_size = None
        candidates = []
        end_of_candidates = None
        other_lines = []
        
        for line in lines:
            if line.startswith('v=') or line.startswith('o=') or line.startswith('s=') or line.startswith('t='):
                session_lines.append(line)
            elif line.startswith('a=group:') or line.startswith('a=msid-semantic'):
                session_lines.append(line)
            elif line.startswith('m='):
                media_line = line
            elif line.startswith('c='):
                connection_line = line
            elif line.startswith('a=ice-ufrag:'):
                ice_ufrag = line
            elif line.startswith('a=ice-pwd:'):
                ice_pwd = line
            elif line.startswith('a=fingerprint:'):
                fingerprint = line
            elif line.startswith('a=setup:'):
                setup_line = line
            elif line.startswith('a=mid:'):
                mid_line = line
            elif line.startswith('a=sctp-port:'):
                sctp_port = line
            elif line.startswith('a=max-message-size:'):
                max_message_size = line
            elif line.startswith('a=candidate:'):
                candidates.append(line)
            elif line.startswith('a=end-of-candidates'):
                end_of_candidates = line
            elif line.strip():  # Non-empty lines we haven't categorized
                other_lines.append(line)
        
        # Rebuild SDP in correct order
        rebuilt_lines = []
        rebuilt_lines.extend(session_lines)
        if media_line:
            rebuilt_lines.append(media_line)
        if connection_line:
            rebuilt_lines.append(connection_line)
        if ice_ufrag:
            rebuilt_lines.append(ice_ufrag)
        if ice_pwd:
            rebuilt_lines.append(ice_pwd)
        if fingerprint:
            rebuilt_lines.append(fingerprint)
        if setup_line:
            rebuilt_lines.append(setup_line)
        if mid_line:
            rebuilt_lines.append(mid_line)
        if sctp_port:
            rebuilt_lines.append(sctp_port)
        if max_message_size:
            rebuilt_lines.append(max_message_size)
        # NOTE: Don't include candidates - browser uses trickle ICE (a=ice-options:trickle)
        # Candidates are exchanged separately, not in the SDP answer
        # rebuilt_lines.extend(candidates)
        # if end_of_candidates:
        #     rebuilt_lines.append(end_of_candidates)
        rebuilt_lines.extend(other_lines)
        print(f"[FIX 5] Removed {len(candidates)} candidates (trickle ICE - candidates exchanged separately)")
        rebuilt_lines.append('')  # Trailing newline
        
        answer_sdp = '\n'.join(rebuilt_lines)
        print("[FIX 4] Reordered SDP attributes to match expected order")
        
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
