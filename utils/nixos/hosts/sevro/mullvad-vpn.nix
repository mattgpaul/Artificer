{ config, lib, pkgs, ... }:

# Mullvad WireGuard egress for the whole protected subnet.
#
# sevro is the gateway; every device behind it (cerebro today, more later) has
# its internet-bound traffic pushed INTO this tunnel and out a Mullvad exit, so
# the world sees Mullvad's IP, not the ISP's. A kill-switch drops anything that
# tries to leave the WAN outside the tunnel, so the ISP link can never leak.
#
# Only sevro's PRIVATE key is secret; it lives at /etc/wireguard/privatekey
# (root-only, 0600) and is referenced by PATH — it is never copied into this
# public repo or the world-readable nix store. Everything below (server keys,
# endpoints, the Mullvad-assigned in-tunnel address) is public / non-sensitive.
#
# TO SWITCH EXIT SERVERS: change `selected` to another key in `servers`. The
# tunnel peer AND the kill-switch whitelist both derive from that one entry, so
# there is nothing else to edit. Add servers (other cities, etc.) to the map.

let
  # --- Registry of known Mullvad exits (name -> endpoint ip + server pubkey) ---
  # Populated from Mullvad's WireGuard config bundle. Port is 51820 for all.
  servers = {
    "us-den-wg-101" = { ip = "37.19.210.1";    pubkey = "74U+9EQrMwVOafgXuSp8eaKG0+p4zjSsDe3J7+ojhx0="; };
    "us-den-wg-102" = { ip = "37.19.210.14";   pubkey = "T44stCRbQXFCBCcpdDbZPlNHp2eZEi91ooyk0JDC21E="; };
    "us-den-wg-103" = { ip = "37.19.210.27";   pubkey = "Az+PGHQ0xFElmRBv+PKZuRnEzKPrPtUpRD3vpxb4si4="; };
    "us-den-wg-201" = { ip = "23.234.68.2";    pubkey = "MsF1hhYtyCsvPt4B8f48biVcVYd692STflhcbKwTGAw="; };
    "us-den-wg-202" = { ip = "23.234.68.127";  pubkey = "YP20qT+/cY/sbBhlXo6fWZlfVhRU+emQlZ1am+vUNnw="; };
    "us-den-wg-203" = { ip = "23.234.69.2";    pubkey = "D8TSWEfmRIm1qMS0RgO8uireFMMZCMi+XxhIJ2jPBEU="; };
    "us-den-wg-204" = { ip = "23.234.69.127";  pubkey = "DZcEpwNSf+6BoDcHknHBVPwAA0ZJjz7DgQ+llATpAzg="; };
    "us-den-wg-205" = { ip = "23.234.70.2";    pubkey = "0LQQJLKBZD0Wf0s0nwFfyMW0MMEKoxNPZ14ZbxkogiY="; };
    "us-den-wg-206" = { ip = "23.234.70.127";  pubkey = "Y4waCBM7GE9iOT+xl9PcZ2mNKGiawEOBv8UkH84CaAo="; };
    "us-den-wg-207" = { ip = "23.234.71.2";    pubkey = "nUnmeY34CDLjW4Q3TAbJQ168jVXmkY4MVAp28rmpzEc="; };
    "us-den-wg-208" = { ip = "23.234.71.127";  pubkey = "Fo6J7nLUeSnNPenB1NiPoivVod3m4fN4OE5yjafxYXY="; };
  };

  # >>> The one line to change when switching exits <<<
  selected = "us-den-wg-101";

  server = servers.${selected};
  endpointPort = 51820;

  # Account-wide, identical across every Mullvad server (tied to sevro's key).
  wgAddrs = [ "10.72.34.18/32" "fc00:bbbb:bbbb:bb01::9:2211/128" ];
  mullvadDns = "10.64.0.1";

  wan = "enp42s0";   # ISP uplink — the ONLY interface the kill-switch guards
in
{
  # Fail the build early if `selected` isn't a real server, instead of producing
  # a broken tunnel at runtime.
  assertions = [{
    assertion = servers ? ${selected};
    message = "mullvad-vpn: selected exit '${selected}' is not in the servers registry.";
  }];

  # WireGuard tunnel. wg-quick's AllowedIPs=0.0.0.0/0,::/0 handling installs the
  # policy routing that sends internet traffic into wg0 while keeping LAN,
  # Tailscale, and the WAN /24 reachable directly (more-specific routes win).
  networking.wg-quick.interfaces.wg0 = {
    address = wgAddrs;
    dns = [ mullvadDns ];
    privateKeyFile = "/etc/wireguard/privatekey";
    peers = [{
      publicKey = server.pubkey;
      allowedIPs = [ "0.0.0.0/0" "::/0" ];
      endpoint = "${server.ip}:${toString endpointPort}";
      persistentKeepalive = 25;   # keep the tunnel alive through the router's NAT
    }];
  };

  environment.systemPackages = [ pkgs.wireguard-tools ];  # `wg show`, diagnostics

  # Policy routing + tunnel return traffic need loose reverse-path filtering,
  # otherwise the kernel can drop decrypted replies arriving on wg0.
  networking.firewall.checkReversePath = lib.mkForce "loose";

  # KILL-SWITCH. NixOS leaves OUTPUT/FORWARD at policy ACCEPT, so these appended
  # rules are authoritative: allow only the encrypted tunnel + DHCP out the WAN,
  # drop everything else. If wg0 is down, all egress is dropped — no ISP leak.
  networking.firewall.extraCommands = ''
    # The encrypted WireGuard handshake/data to Mullvad rides the WAN directly.
    iptables -A OUTPUT -o ${wan} -p udp -d ${server.ip} --dport ${toString endpointPort} -j ACCEPT
    # Keep the WAN's DHCP lease alive.
    iptables -A OUTPUT -o ${wan} -p udp --dport 67 -j ACCEPT
    # Everything else trying to exit the WAN is a leak: drop it.
    iptables -A OUTPUT  -o ${wan} -j DROP
    iptables -A FORWARD -o ${wan} -j DROP

    # IPv6: the tunnel underlay is IPv4, so no native v6 should exit the WAN.
    # Permit link-local/NDP so the interface stays healthy, drop the rest.
    ip6tables -A OUTPUT -o ${wan} -d fe80::/10 -j ACCEPT
    ip6tables -A OUTPUT -o ${wan} -d ff02::/16 -j ACCEPT
    ip6tables -A OUTPUT  -o ${wan} -j DROP
    ip6tables -A FORWARD -o ${wan} -j DROP
  '';
  networking.firewall.extraStopCommands = ''
    iptables -D OUTPUT -o ${wan} -p udp -d ${server.ip} --dport ${toString endpointPort} -j ACCEPT 2>/dev/null || true
    iptables -D OUTPUT -o ${wan} -p udp --dport 67 -j ACCEPT 2>/dev/null || true
    iptables -D OUTPUT  -o ${wan} -j DROP 2>/dev/null || true
    iptables -D FORWARD -o ${wan} -j DROP 2>/dev/null || true
    ip6tables -D OUTPUT -o ${wan} -d fe80::/10 -j ACCEPT 2>/dev/null || true
    ip6tables -D OUTPUT -o ${wan} -d ff02::/16 -j ACCEPT 2>/dev/null || true
    ip6tables -D OUTPUT  -o ${wan} -j DROP 2>/dev/null || true
    ip6tables -D FORWARD -o ${wan} -j DROP 2>/dev/null || true
  '';
}
