# UPnP Investigation Document

## The Problem We're Trying to Solve

**Goal:** Allow DLC (Foundry VTT module running in player's browser) to connect to DLA (desktop app running on player's local machine) without requiring manual router configuration.

**Architecture:**
- GM hosts Foundry VTT on their machine (accessible via external IP, e.g., `http://83.105.151.227:30000`)
- Each player runs their own local instance of DLA
- Player accesses GM's Foundry via browser
- DLC (in player's browser) needs to connect to player's local DLA via WebSocket on port 8765
- DLC connects using `window.location.hostname` (the external IP) with port 8765
- Connection routes through player's router back to their local DLA (hairpin NAT)

## What Works

1. **Manual static port forwarding** - When a user manually creates a port forward rule in their router (TCP 8765 → local IP:8765), the connection succeeds. DLA receives the connection attempt and everything works.

2. **UPnP rule creation** - DLA successfully discovers the router's UPnP service (WANIPConnection), creates a dynamic port mapping, and the rule appears in the router's Dynamic Port Mapping table with correct parameters.

3. **Local connections** - When accessing Foundry via local IP (e.g., `192.168.1.55:30000`), connections to localhost work fine.

## What Does NOT Work

**UPnP-created port forwarding fails silently.** Despite the UPnP rule being created successfully and appearing correctly in the router's settings:
- Zero connection attempts reach DLA
- No error messages
- The traffic simply never arrives

## Technical Details

### Router Tested
- Vodafone PowerHub Router
- Firmware version: 22.1.0404-6421066
- UPnP enabled
- Hairpin NAT works for static port mappings

### UPnP Implementation
- Library: `upnpy` (pure Python, no compilation required)
- Service discovered: WANIPConnection (WANIPConn1)
- Action used: `AddPortMapping`

### UPnP Parameters Used
```python
wan_service.AddPortMapping(
    NewRemoteHost='',           # Empty = any remote host
    NewExternalPort=8765,
    NewProtocol='TCP',
    NewInternalPort=8765,
    NewInternalClient='192.168.1.55',  # Local IP
    NewEnabled=1,
    NewPortMappingDescription='Dice Link App',
    NewLeaseDuration=3600       # Also tried 0 (permanent)
)
```

### Router Display Comparison

**Static Port Mapping (WORKS):**
| Service | Local IPv4 Address | Protocol | Local Port | Public Port |
|---------|-------------------|----------|------------|-------------|
| DLA     | 192.168.1.55      | TCP      | 8765       | 8765        |

**Dynamic Port Mapping via UPnP (FAILS):**
| Service | Local IPv4 Address | Protocol | Local Port | Public Port |
|---------|-------------------|----------|------------|-------------|
| upnp    | 192.168.1.55      | TCP      | 8765       | 8765        |

The parameters are identical, yet only the static rule works.

## What We've Tried

1. **Lease duration 0 (permanent)** - Failed
2. **Lease duration 3600 (1 hour)** - Failed
3. **Verified TCP protocol explicitly specified** - Confirmed correct
4. **Verified local IP is correct** - Confirmed correct
5. **Checked router displays rule correctly** - Confirmed rule exists

## Root Cause Hypothesis

The Vodafone router appears to NOT support hairpin NAT for UPnP-created dynamic rules, only for manually-created static rules. This may be a router firmware limitation, not a DLA code issue.

**Evidence:**
- Rule creation succeeds (visible in router)
- Parameters are identical to working static rule
- Zero traffic reaches DLA (not even a failed connection attempt)
- Static rule with same parameters works immediately

## Why Other Solutions Don't Work

### Browser Security (PNA - Private Network Access)
When a page is loaded from an external origin (e.g., `http://83.105.151.227:30000`), browsers block:
- WebSocket connections to `localhost` or `127.0.0.1`
- Fetch requests to `localhost` or `127.0.0.1`

This is why DLC must use the external IP for connections, which requires port forwarding (manual or UPnP).

### localhost Architecture
Originally intended architecture was:
- DLC connects to `ws://localhost:8765` (player's own machine)
- Should work regardless of where Foundry page was loaded from
- **Blocked by PNA** - browsers now prevent this for security

## Questions for Investigation

1. **Is there a different UPnP action** that creates rules the router treats the same as static rules?

2. **Is there a way to detect** that UPnP rule creation succeeded but hairpin NAT won't work, so we can prompt the user for manual port forwarding?

3. **Are there alternative NAT traversal techniques** that don't require port forwarding at all? (STUN, TURN, ICE, WebRTC data channels?)

4. **Is there a relay server architecture** that could work? (DLA connects outbound to a relay, DLC connects to the same relay, no inbound ports needed)

5. **Can we bypass PNA restrictions** another way? (The `local.realmbridge.co.uk` DNS + SSL certificate approach was mentioned but not yet implemented)

## Files Involved

- `/scripts/dice-link/upnp.py` - UPnP implementation
- `/scripts/dice-link/config.py` - Configuration (WEBSOCKET_HOST, WEBSOCKET_PORT)
- `/scripts/dice-link/main.py` - Application entry point, UPnP setup/cleanup
- `/scripts/dice-link/server.py` - WebSocket server, `/ws/dlc` endpoint
- `/scripts/dice-link/debug.py` - Centralized debug logging

## Current State

- DLA binds to `0.0.0.0:8765` (all interfaces)
- UPnP attempts port forwarding on startup
- UPnP rule creation succeeds but traffic doesn't flow
- Manual port forwarding works as a fallback
- No graceful fallback messaging implemented yet
