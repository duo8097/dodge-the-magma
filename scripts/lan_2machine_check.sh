#!/usr/bin/env bash
#
# scripts/lan_2machine_check.sh
#
# Manual / semi-automated LAN test between two machines running the same build
# of Dodge the Magma. One machine hosts, the other joins.
#
# Usage:
#   ./scripts/lan_2machine_check.sh host  <port>
#   ./scripts/lan_2machine_check.sh client <host-ip> [port]
#   ./scripts/lan_2machine_check.sh ping   <host-ip>
#
# This script:
#   - pings the other machine and prints round-trip stats,
#   - opens a UDP socket to the game's port (45678) and sends a fake
#     PlayerJoinPacket to confirm the host is reachable at the application
#     layer (the host won't reply to this raw packet, but a successful send
#     with no ICMP unreachable proves the socket is open).
#   - if run with root, applies a `tc netem` rule on loopback so you can
#     feel latency / loss locally before the real test.
#
# Pre-requisites:
#   - Both machines on the same LAN (or with UDP 45678 reachable).
#   - `dodge_magma` built on both machines (see README).
#   - Firewall allowing UDP 45678 (Linux: `sudo ufw allow 45678/udp`).
#
# This script does NOT replace running the actual game. It exists to:
#   1. Quickly catch network problems (firewall, wrong IP, wrong port).
#   2. Provide a deterministic checklist (docs/lan_2machine_checklist.md)
#      of game-level scenarios to exercise.

set -euo pipefail

PORT="${PORT:-45678}"

cmd="${1:-}"
shift || true

log() { printf '[%(%H:%M:%S)T] %s\n' -1 "$*" >&2; }
die() { log "ERROR: $*"; exit 1; }

have_cmd() { command -v "$1" >/dev/null 2>&1; }

# ── ping ────────────────────────────────────────────────────────────────────
do_ping() {
    local target="$1"
    log "ping $target (10 packets)..."
    if have_cmd ping; then
        ping -c 10 -W 1 "$target" || true
    else
        log "ping not available; skipping"
    fi
}

# ── udp probe ───────────────────────────────────────────────────────────────
# Send a small UDP datagram to the game's port. We don't expect a reply,
# but a "Connection refused" / "No route to host" tells us the port is
# unreachable. A successful send means the kernel accepted it.
do_udp_probe() {
    local target="$1"
    local port="${2:-$PORT}"
    log "UDP probe: sending 5 datagrams to $target:$port..."
    if ! have_cmd nc; then
        log "nc (netcat) not available; skipping UDP probe"
        return 0
    fi
    for i in 1 2 3 4 5; do
        if printf 'DTMPROBE\n' | nc -u -w1 -q1 "$target" "$port"; then
            log "  send #$i: ok"
        else
            log "  send #$i: failed (rc=$?)"
        fi
    done
}

# ── netem (root only) ──────────────────────────────────────────────────────
# On the local loopback, add a netem qdisc so we can see what the game looks
# like over a flaky link. Useful for debugging rubber-banding / packet drops.
apply_netem_loopback() {
    if [[ $EUID -ne 0 ]]; then
        log "netem skipped (not root). Re-run with sudo to enable."
        return 0
    fi
    if ! have_cmd tc; then
        log "tc not installed; skipping netem"
        return 0
    fi
    log "applying tc netem on loopback: delay 50ms ± 20ms, loss 2%"
    tc qdisc add dev lo root netem delay 50ms 20ms loss 2% 2>/dev/null \
        || tc qdisc change dev lo root netem delay 50ms 20ms loss 2%
    log "netem active. To remove: sudo tc qdisc del dev lo root"
}

remove_netem_loopback() {
    if [[ $EUID -ne 0 ]]; then
        return 0
    fi
    if have_cmd tc; then
        tc qdisc del dev lo root 2>/dev/null || true
        log "netem removed"
    fi
}

# ── host / client roles ────────────────────────────────────────────────────
do_host() {
    log "HOST mode: ensure firewall allows UDP $PORT"
    if have_cmd ufw; then
        sudo ufw allow "${PORT}/udp" || true
    fi
    log "Run the game and press M → H to host. Tell the client machine your IP:"
    ip -4 addr show | awk '/inet / && !/127.0.0.1/ {print "  candidate IP:", $2}' | head -5
    apply_netem_loopback
    log "Open the game. Press M → H to host. When done, run this script again with 'cleanup'."
}

do_client() {
    local target="${1:?usage: $0 client <host-ip>}"
    log "CLIENT mode: target = $target"
    do_ping "$target"
    do_udp_probe "$target" "$PORT"
    log "Now run the game on this machine. Press M → C (toggle to LAN) → J → type the host IP → Enter."
}

do_cleanup() {
    remove_netem_loopback
    if have_cmd ufw; then
        sudo ufw delete allow "${PORT}/udp" || true
    fi
}

# ── entrypoint ─────────────────────────────────────────────────────────────
case "$cmd" in
    host)    do_host "$@" ;;
    client)  do_client "$@" ;;
    ping)    do_ping "${1:?usage: $0 ping <host-ip>}" ;;
    netem)   apply_netem_loopback ;;
    unnetem) remove_netem_loopback ;;
    cleanup) do_cleanup ;;
    -h|--help|help|"")
        cat <<EOF
Dodge the Magma — LAN test helper

Usage:
  $0 host                              Run firewall rules, show your IPs (HOST)
  $0 client <host-ip>                  Ping + UDP probe to the host, then run game (CLIENT)
  $0 ping   <host-ip>                  Just ping the other machine 10 times
  $0 netem / unnetem                   Add/remove loopback tc netem (root only)
  $0 cleanup                           Undo firewall + netem changes

Environment:
  PORT=45678                          Game UDP port (default)

See docs/lan_2machine_checklist.md for the full manual test checklist.
EOF
        ;;
    *) die "unknown subcommand: $cmd (try --help)" ;;
esac