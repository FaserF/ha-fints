#!/usr/bin/env python3
"""OpenWrt API Client Connection Test Tool.

Validates connectivity and functionality of the Ubus, LuCI RPC, and SSH
clients against a live router, checking all read-only methods.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import sys
from unittest.mock import MagicMock

import aiohttp

# Add integration directory to python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from custom_components.openwrt.api import LuciRpcClient, SshClient, UbusClient
except ImportError:
    print(
        "Error: Could not import OpenWrt API clients. Ensure this script is run from the repository root."
    )
    sys.exit(1)

# List of read-only methods to test
READ_METHODS = [
    "get_device_info",
    "get_system_resources",
    "get_external_ip",
    "get_wireless_interfaces",
    "get_wireguard_interfaces",
    "get_network_interfaces",
    "get_connected_devices",
    "get_dhcp_leases",
    "get_ip_neighbors",
    "get_lldp_neighbors",
    "get_mwan_status",
    "get_wps_status",
    "get_system_logs",
    "get_services",
    "get_installed_packages",
    "get_firewall_rules",
    "get_firewall_redirects",
    "get_access_control",
    "get_leds",
    "get_adblock_status",
    "get_simple_adblock_status",
    "get_banip_status",
    "get_sqm_status",
    "get_nlbwmon_data",
    "get_wifi_credentials",
]


async def test_client(name: str, client: any) -> None:
    print(f"\n==================== Testing {name} Client ====================")
    try:
        connected = await client.connect()
        print(f"Connection Status: {'SUCCESS' if connected else 'FAILED'}")
        if not connected:
            return
    except Exception as e:
        print(f"Connection Failed with error: {e}")
        return

    for method_name in READ_METHODS:
        if not hasattr(client, method_name):
            print(f"[{method_name}] - Unsupported (method not defined)")
            continue

        method = getattr(client, method_name)
        try:
            res = await method()
            await asyncio.sleep(0.2)
            if isinstance(res, list):
                summary = f"list with {len(res)} items"
            elif isinstance(res, dict):
                summary = f"dict with {len(res)} keys"
            elif hasattr(res, "__dict__"):
                # Clean up display of object dict
                d = {k: v for k, v in res.__dict__.items() if not k.startswith("_")}
                summary = f"object of type {res.__class__.__name__} ({str(d)[:120]}...)"
            else:
                summary = str(res)[:120]
            print(f"  [SUCCESS] {method_name:<30}: {summary}")
        except Exception as e:
            print(f"  [FAILED]  {method_name:<30}: {e}")


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Test OpenWrt API clients against a live router."
    )
    parser.add_argument(
        "--host",
        default="192.168.1.1",
        help="Router IP address or hostname (default: 192.168.1.1)",
    )
    parser.add_argument(
        "--username",
        default="homeassistant",
        help="Username for API communication (default: homeassistant)",
    )
    parser.add_argument(
        "--password",
        help="Password for the API user (will prompt interactively if not provided)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=80,
        help="HTTP/HTTPS port for Ubus and LuCI RPC (default: 80)",
    )
    parser.add_argument(
        "--ssh-port", type=int, default=22, help="SSH port (default: 22)"
    )
    parser.add_argument(
        "--use-ssl", action="store_true", help="Use HTTPS/SSL for Ubus and LuCI RPC"
    )
    parser.add_argument(
        "--verify-ssl", action="store_true", help="Verify SSL certificate"
    )

    args = parser.parse_args()

    password = args.password
    if not password:
        password = getpass.getpass(
            prompt=f"Enter password for {args.username}@{args.host}: "
        )

    async with aiohttp.ClientSession() as session:
        # 1. Ubus
        ubus = UbusClient(
            hass=MagicMock(),
            session=session,
            host=args.host,
            username=args.username,
            password=password,
            port=args.port,
            use_ssl=args.use_ssl,
            verify_ssl=args.verify_ssl,
        )
        await test_client("Ubus (HTTP/HTTPS JSON-RPC)", ubus)

        # 2. LuCI RPC
        luci = LuciRpcClient(
            hass=MagicMock(),
            session=session,
            host=args.host,
            username=args.username,
            password=password,
            port=args.port,
            use_ssl=args.use_ssl,
            verify_ssl=args.verify_ssl,
        )
        await test_client("LuCI RPC", luci)

        # 3. SSH
        ssh = SshClient(
            hass=MagicMock(),
            session=session,
            host=args.host,
            username=args.username,
            password=password,
            port=args.ssh_port,
        )
        await test_client("SSH", ssh)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
