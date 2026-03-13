import os
import requests
import urllib3

# 1. Konfigurer dine NetBox oplysninger her
NETBOX_URL = os.getenv('NETBOX_URL', 'https://netbox.dccat.dk/')
NETBOX_TOKEN = os.getenv('NETBOX_TOKEN', 'XXXXXXXXXXX')

# Deaktiver SSL-advarsler (intern CA)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def main():
    # Definer IP scopet i stedet for enhedens navn
    ip_scope = '10.50.0.0/16'
    print(f"Fetching IP addresses within scope: '{ip_scope}'...\n")

    headers_nb = {
        "Authorization": f"Token {NETBOX_TOKEN}", 
        "Content-Type": "application/json", 
        "Accept": "application/json"
    }

    try:
        # Søg efter alle IP-adresser, der ligger inde i (eller er lig med) det angivne scope
        # I Netbox API'et bruges parameteren `parent` til at finde IP'er i et prefix/subnet
        # Brug paginering ("next") for at sikre at alle resultater bliver hentet, uanset Netbox max-limit
        ips_url = f"{NETBOX_URL}/api/ipam/ip-addresses/?parent={ip_scope}&limit=100"
        
        results = []
        while ips_url:
            ip_response = requests.get(ips_url, headers=headers_nb, verify=False)
            ip_response.raise_for_status()
            ips_data = ip_response.json()
            
            # Tilføj resultaterne fra den aktuelle side til vores samlede liste
            results.extend(ips_data.get('results', []))
            
            # Tjek om der er en næste side, ellers bliver ops_url til None og loopet stopper
            ips_url = ips_data.get('next')
            
        if not results:
            print(f"No IP addresses found in scope {ip_scope}.")
            return
            
        print("-" * 75)
        
        pending_updates = []
        for ip in results:
            ip_id = ip['id']
            ip_addr = ip['address'].split('/')[0]
            current_dns = ip.get('dns_name', '')
            
            # Tjek for interface tilknytning
            assigned_object = ip.get('assigned_object')
            if not assigned_object or 'name' not in assigned_object:
                print(f"  [!]  IP {ip_addr:<14} | Not assigned to an interface (skipping).")
                continue
                
            interface_name = assigned_object['name']
            
            # Grib device (enheds) navnet fra interface objektets 'device' or 'virtual_machine' reference
            device_info = assigned_object.get('device') or assigned_object.get('virtual_machine')
            
            if not device_info:
                print(f"  [!]  IP {ip_addr:<14} | Interface '{interface_name}' missing a device (skipping).")
                continue
                
            raw_device_name = device_info.get('name', 'unknown')
            
            # Formatter enhedsnavnet
            device_dns_base = raw_device_name.lower().split('_')[0] 
            
            # Formatter interfacenavnet (små bogstaver + forkortelser til DNS)
            iface_dns = interface_name.lower()
            iface_dns = iface_dns.replace('gigabitethernet', 'ge')
            iface_dns = iface_dns.replace('tengigabitethernet', 'te')
            iface_dns = iface_dns.replace('fortygigabitethernet', 'fo')
            iface_dns = iface_dns.replace('hundredgigabitethernet', 'hu')
            iface_dns = iface_dns.replace('port-channel', 'po')
            iface_dns = iface_dns.replace('fastethernet', 'fa')
            iface_dns = iface_dns.replace('ethernet', 'eth')
            iface_dns = iface_dns.replace('loopback', 'lo')
            iface_dns = iface_dns.replace('vlan', 'vl')
            iface_dns = iface_dns.replace('management', 'mgmt')
            iface_dns = iface_dns.replace('bdi3', 'bd3')
            
            # Ekstra DNS regler: udskift punktum og slash med bindestreg
            iface_dns = iface_dns.replace('.', '-')
            iface_dns = iface_dns.replace('/', '-')
            
            
            # Byg dynamisk DNS-navn: <interface>.<device>.net.dccat.dk
            dns_name = f"{iface_dns}.{device_dns_base}.net.dccat.dk"
            
            # Udskrift logik
            if current_dns == dns_name:
                print(f"  [OK]  {interface_name:<14} on {device_dns_base:<12} | {ip_addr:<14} | DNS already correct")
            elif current_dns:
                print(f"  [?!]  {interface_name:<14} on {device_dns_base:<12} | {ip_addr:<14} | EXISTS: '{current_dns}' (Proposed: {dns_name})")
                pending_updates.append({"id": ip_id, "ip_addr": ip_addr, "new_dns": dns_name})
            else:
                print(f"  [NEW] {interface_name:<14} on {device_dns_base:<12} | {ip_addr:<14} | New Proposal: {dns_name}")
                pending_updates.append({"id": ip_id, "ip_addr": ip_addr, "new_dns": dns_name})
                
        print("-" * 75)
        
        # Hvis der er nogen ændringer at udføre:
        if pending_updates:
            print(f"\n{len(pending_updates)} IP addresses ready for DNS update in Netbox.")
            svar = input("Do you want to write these changes to Netbox now? (y/n): ")
            if svar.lower() == 'y':
                print("\nStarting update...")
                for update in pending_updates:
                    patch_url = f"{NETBOX_URL}api/ipam/ip-addresses/{update['id']}/" 
                    patch_data = {"dns_name": update['new_dns']}
                    print(f" -> Updating {update['ip_addr']:<15} to {update['new_dns']} ... ", end="")
                    try:
                        patch_resp = requests.patch(patch_url, headers=headers_nb, json=patch_data, verify=False)
                        patch_resp.raise_for_status()
                        print("OK!")
                    except requests.exceptions.HTTPError as e:
                        print(f"ERROR: {e.response.text}")
                print("Update completed!\n")
            else:
                print("Changes cancelled. Nothing written to Netbox.\n")
        
    except requests.exceptions.HTTPError as e:
        print(f"Error making HTTP connection to NetBox: Status {e.response.status_code}")
        print(f"Netbox Response: {e.response.text}")
    except Exception as e:
        print(f"Another error occurred: {e}")

if __name__ == '__main__':
    main()
