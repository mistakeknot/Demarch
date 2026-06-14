#!/usr/bin/env bash
# Join this (ephemeral) Claude Code cloud container to the user's tailnet and verify
# the path to the GPU desktop, ending with an nvidia-smi smoke over SSH.
#
# Prereqs (user side, one-time):
#   - Tailscale installed *inside WSL2* on the desktop, brought up with:
#       tailscale up --ssh
#     (Tailscale SSH: no sshd/authorized_keys management needed.)
#   - An EPHEMERAL, pre-authorized, tag-scoped auth key (e.g. tag:claude-session),
#     ACL-limited to SSH to the desktop node only, with a short expiry.
#     Generate: https://login.tailscale.com/admin/settings/keys
#
# Prereqs (session side):
#   - TS_AUTHKEY      : the auth key (set as a Claude Code environment secret)
#   - GPU_HOST        : tailnet hostname of the WSL2 node (e.g. "desktop-wsl")
#   - GPU_USER        : login user on that node (defaults to "root" under Tailscale SSH
#                       only if ACLs allow; usually your WSL username)
#
# Feasibility already verified from a session container: root + CAP_NET_ADMIN,
# /dev/net/tun present, egress to controlplane.tailscale.com / DERP / pkgs OK.
# DERP fallback means this works even if UDP is blocked (slower, fine for SSH).

set -euo pipefail

GPU_HOST="${GPU_HOST:-}"
GPU_USER="${GPU_USER:-}"

stage() { printf '\n==> %s\n' "$*"; }

if [ -z "${TS_AUTHKEY:-}" ]; then
  echo "ERROR: TS_AUTHKEY is not set. Add it as an environment secret (ephemeral," >&2
  echo "tag-scoped, short-expiry key from the Tailscale admin console)." >&2
  exit 1
fi
if [ -z "$GPU_HOST" ]; then
  echo "ERROR: GPU_HOST is not set (tailnet hostname of the WSL2 node)." >&2
  exit 1
fi

stage "1/5 Install tailscale (if missing)"
if ! command -v tailscale >/dev/null 2>&1; then
  curl -fsSL https://tailscale.com/install.sh | sh
fi
tailscale version

stage "2/5 Start tailscaled"
if ! pgrep -x tailscaled >/dev/null 2>&1; then
  if [ -c /dev/net/tun ]; then
    tailscaled >/tmp/tailscaled.log 2>&1 &
  else
    # userspace fallback: no TUN device needed; SOCKS5 proxy for outbound dials
    tailscaled --tun=userspace-networking \
      --socks5-server=localhost:1055 >/tmp/tailscaled.log 2>&1 &
  fi
  sleep 3
fi

stage "3/5 Join tailnet (ephemeral node)"
tailscale up --authkey="${TS_AUTHKEY}" --hostname="claude-session" --accept-routes
tailscale status

stage "4/5 SSH reachability to ${GPU_HOST}"
SSH_TARGET="${GPU_HOST}"
[ -n "$GPU_USER" ] && SSH_TARGET="${GPU_USER}@${GPU_HOST}"
# Tailscale SSH: authn/authz handled by tailnet ACLs, no key files.
tailscale ssh "$SSH_TARGET" -- echo "ssh-ok from claude-session"

stage "5/5 GPU smoke (nvidia-smi over SSH)"
tailscale ssh "$SSH_TARGET" -- nvidia-smi

stage "DONE — tailnet path verified end-to-end (container -> tailnet -> WSL2 -> 4090)"
echo "Note: this node is ephemeral; it auto-removes from the tailnet when the"
echo "container is reclaimed. Re-run this script in new sessions."
