import ipaddress
import json
import socket

import pyroute2
import wireguard_py
from wireguard_py.wireguard_common import Endpoint

WG_IFACE = 'wg-srv'
SRV_ENDPOINT = 'vubnt-srv'

def del_peer(iface: str ,ip: str):
    peers = wireguard_py.list_peers(iface.encode())
    for peer in peers:
        print(f"{peer.endpoint.ip} - ref {ip}")
        if str(peer.endpoint.ip) == ip:
            wireguard_py.delete_peer(iface.encode(), peer.pubkey.encode())


def add_peer(iface: str ,ip: str, srv_pub_key = None):
    cl_priv_key = wireguard_py.gen_priv_key()
    cl_pub_key = wireguard_py.get_pub_key(cl_priv_key)
    # Create a peer
    wireguard_py.set_peer(
        device_name=iface.encode(),
        pub_key=cl_pub_key,
        #endpoint=Endpoint(ip=ipaddress.ip_address(ip), port=51820),
        endpoint=Endpoint(ip=ipaddress.ip_address('172.28.6.224'), port=51820),
        #endpoint=None,
        allowed_ips={
            ipaddress.ip_network(f"{ip}/32")
        },
        replace_allowed_ips=True,
    )
    js = {
        'ip': ip,
        'endpoint': SRV_ENDPOINT,
        'pub_key': cl_pub_key.decode(),
        'priv_key': cl_priv_key.decode(),
        'srv_pub_key': srv_pub_key.decode()
    }
    json.dump(js, open(f'{iface}__{ip}.json', 'w'), ensure_ascii=False, indent=2, default=str)
    return js


# Create the wireguard interface
ipr = pyroute2.IPRoute()
try:
    ipr.link("add", ifname=WG_IFACE, kind="wireguard")
except pyroute2.netlink.exceptions.NetlinkError as e:
    if e.code == 17:
        print(f"Interface {WG_IFACE} already exists")
        ipr.link("remove", ifname=WG_IFACE)
        ipr.link("add", ifname=WG_IFACE, kind="wireguard")
    else:
        print(e)
wg_ifc = ipr.link_lookup(ifname=WG_IFACE)[0]
try:
    ipr.addr("add", index=wg_ifc, address="172.16.0.1", prefixlen=24)
except pyroute2.netlink.exceptions.NetlinkError as e:
    if e.code == 17:
        print(f"IP address for {WG_IFACE} already added, resetting...")
        ipr.addr("set", index=wg_ifc, address="172.16.0.1", prefixlen=24)
    else:
        print(e.args)

ipr.link("set", index=wg_ifc, state="up")

# Configure wireguard interface
srv_priv_key = wireguard_py.gen_priv_key()
srv_pub_key = wireguard_py.get_pub_key(srv_priv_key)
info = {
    "server" : {
        'pubkey': srv_pub_key.decode(),
        'privkey': srv_priv_key.decode()
    }
}
wireguard_py.set_device(
    device_name=WG_IFACE.encode(),
    priv_key=srv_priv_key,
    port=51820,
)


peers = [{'ip': str(peer.endpoint.ip),'pub_key': peer.pubkey} for peer in wireguard_py.list_peers(WG_IFACE.encode())]
ip = "172.16.0.2"
if ip in [peer.get('ip', None) for peer in peers]:
    print(ip)
    del_peer(WG_IFACE, ip)
peers.append(add_peer(WG_IFACE, ip, srv_pub_key))
info.update({ "peers" : peers })


# List peers
peers = wireguard_py.list_peers(WG_IFACE.encode())
json.dump(info, open('settings.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2, default=str)
print("\n")
for peer in peers:
    try:
        s = f"IP: {peer.endpoint.ip}:{peer.endpoint.port}\n"
    except:
        s = ''
    s+= f"Public key: {peer.pubkey}\n"
    for ip in peer.allowed_ips:
        s+= f"Allowed: {ip}\n"

    print(s)