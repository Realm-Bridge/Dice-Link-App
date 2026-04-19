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
        # FIX 3: Extract attributes from offer that should be echoed in answer
        # ============================================
        offer_extmap_allow_mixed = None
        offer_ice_options = None
        
        for line in offer_sdp.split('\n'):
            if line.startswith('a=extmap-allow-mixed'):
                offer_extmap_allow_mixed = line
            if line.startswith('a=ice-options:'):
                offer_ice_options = line
        
        if offer_extmap_allow_mixed:
            print(f"[FIX 3] Found in offer: {offer_extmap_allow_mixed}")
        if offer_ice_options:
            print(f"[FIX 3] Found in offer: {offer_ice_options}")
        
        # ============================================
        # FIX 4: Match offer's connection line format (IPv4 vs IPv6)
        # ============================================
        offer_connection = None
        for line in offer_sdp.split('\n'):
            if line.startswith('c='):
                offer_connection = line
                break
        
        if offer_connection:
            print(f"[FIX 4] Using offer's connection line: {offer_connection}")
        
        # ============================================
        # FIX 5: Extract correct fingerprint algorithm from offer
        # ============================================
        offer_fingerprint = None
        for line in offer_sdp.split('\n'):
            if line.startswith('a=fingerprint:'):
                offer_fingerprint = line
                break
        
        # Get the fingerprint algorithm from the offer (sha-256, sha-384, or sha-512)
        offer_fingerprint_algo = None
        if offer_fingerprint:
            # Extract algorithm: "a=fingerprint:sha-256 ..." -> "sha-256"
            offer_fingerprint_algo = offer_fingerprint.split(':')[1].split(' ')[0]
            print(f"[FIX 5] Offer uses: {offer_fingerprint_algo}")
        
        # Remove fingerprints that don't match the offer
        lines = answer_sdp.split('\n')
        new_lines = []
        for line in lines:
            if line.startswith('a=fingerprint:'):
                # Extract this line's algorithm
                this_algo = line.split(':')[1].split(' ')[0]
                # Keep it only if it matches the offer's algorithm
                if offer_fingerprint_algo and this_algo == offer_fingerprint_algo:
                    new_lines.append(line)
                    print(f"[FIX 5] Keeping fingerprint with {this_algo}")
                else:
                    print(f"[FIX 5] Removing fingerprint with {this_algo} (offer uses {offer_fingerprint_algo})")
            else:
                new_lines.append(line)
        answer_sdp = '\n'.join(new_lines)
        
        # ============================================
        # FIX 6: Reorder SDP to match browser's expected order
        # Order should be: c=, ice-ufrag, ice-pwd, fingerprint, setup, mid, sctp-port, max-message-size
        # ============================================
        lines = answer_sdp.split('\n')
        
        # Separate session-level and media-level lines
        session_lines = []  # v=, o=, s=, t=, a=group, a=msid-semantic
        media_line = None   # m=
        connection_line = None  # c= from answer (will be replaced with offer's)
        ice_ufrag = None
        ice_pwd = None
        fingerprint = None
        setup_line = None
        mid_line = None
        sctp_port = None
        max_message_size = None
        candidates = []
        end_of_candidates = None
        extmap_allow_mixed = None
        ice_options = None
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
            elif line.startswith('a=extmap-allow-mixed'):
                extmap_allow_mixed = line
            elif line.startswith('a=ice-options:'):
                ice_options = line
            elif line.strip():  # Non-empty lines we haven't categorized
                other_lines.append(line)
                candidates.append(line)
            elif line.startswith('a=end-of-candidates'):
                end_of_candidates = line
            elif line.strip():  # Non-empty lines we haven't categorized
                other_lines.append(line)
        
        # ============================================
        # FIX 7: Use offer's connection line (override answer's)
        # ============================================
        if offer_connection:
            connection_line = offer_connection
        
        # ============================================
        # FIX 8: Use max-message-size from offer
        # ============================================
        offer_max_msg_size = None
        for line in offer_sdp.split('\n'):
            if line.startswith('a=max-message-size:'):
                offer_max_msg_size = line
                break
        
        if offer_max_msg_size:
            max_message_size = offer_max_msg_size
            print(f"[FIX 8] Using offer's max-message-size value: {offer_max_msg_size}")
        else:
            print(f"[FIX 8] No offer max-message-size found, using answer's value")
        
        # Rebuild SDP in correct order
        # Session-level order: v=, o=, s=, t=, a=group, a=extmap-allow-mixed (if present), a=msid-semantic
        # Media-level order: m=, c=, a=ice-ufrag, a=ice-pwd, a=ice-options (if present), a=fingerprint, a=setup, a=mid, a=sctp-port, a=max-message-size
        rebuilt_lines = []
        rebuilt_lines.extend(session_lines)
        
        # Add session-level attributes from offer
        if offer_extmap_allow_mixed:
            rebuilt_lines.append(offer_extmap_allow_mixed)
            print(f"[FIX 9] Added to answer: {offer_extmap_allow_mixed}")
        
        if media_line:
            rebuilt_lines.append(media_line)
        if connection_line:
            rebuilt_lines.append(connection_line)
        if ice_ufrag:
            rebuilt_lines.append(ice_ufrag)
        if ice_pwd:
            rebuilt_lines.append(ice_pwd)
        
        # Add ice-options from offer if present
        if offer_ice_options:
            rebuilt_lines.append(offer_ice_options)
            print(f"[FIX 10] Added to answer: {offer_ice_options}")
        
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
        print(f"[FIX 9] Removed {len(candidates)} candidates (trickle ICE - candidates exchanged separately)")
        rebuilt_lines.append('')  # Trailing newline
        
        answer_sdp = '\n'.join(rebuilt_lines)
        
        # ============================================
        # FIX 10: Remove trailing empty line (causes parsing issues)
        # ============================================
        answer_sdp = answer_sdp.rstrip('\n')
        print("[FIX 10] Removed trailing empty lines")
        
        print("\n" + "="*60)
        print("DEBUG: FINAL SDP BEING SENT TO BROWSER")
        print("="*60)
        print(f"Length: {len(answer_sdp)} bytes")
        print(f"Repr (with hidden chars): {repr(answer_sdp[:200])}")
        print("\nFinal answer lines:")
        for i, line in enumerate(answer_sdp.split('\n')):
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
