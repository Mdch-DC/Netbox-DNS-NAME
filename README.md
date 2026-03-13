# Netbox DNS Info Script

Dette script trækker IP-adresser fra Netbox for et angivet subnet/scope og foreslår automatisk DNS-navne, som er baseret på det interface og den enhed, IP-adressen er tilknyttet.

## Funktioner
* Henter alle IP-adresser for det angivne scope (håndterer automatisk Netbox's grænse på 50 resultater vha. paginering).
* Oversætter interfacenavne (som f.eks. "GigabitEthernet") til standardiserede forkortelser (som "ge").
* Bygger dynamisk et forslag til næste DNS-navn i formatet: `<interface>.<enhedsnvavn>.net.dccat.dk`.
* Sammenligner forslaget med det eksisterende DNS-navn i Netbox.
* **Sikkerhed/Read-Only:** Scriptet læser kun data og analyserer det. Det ændrer ikke noget i Netbox medmindre man udtrykkeligt godkender det til sidst med et "y". Alt andet (eller at trykke Enter, eller "n") afbryder og lader Netbox være urørt.

## Hvordan det køres

1. Åbn `netbox_dns_info.py` og tilpas `ip_scope` (f.eks. `10.50.0.0/16`).
2. Kør scriptet fra terminalen:
   ```bash
   python netbox_dns_info.py
   ```

## Eksempel på output

Når du kører scriptet, samler den en liste og præsenterer forslagene på skærmen:

```text
Fetching IP addresses within scope: '10.50.0.0/16'...

---------------------------------------------------------------------------
  [!]   IP 10.50.0.1      | Not assigned to an interface (skipping).
  [NEW] Vlan320        on tst-sw1      | 10.50.10.1     | New Proposal: vl320.tst-sw1.net.dccat.dk
  [OK]  GigabitEthernet1 on tst-r1       | 10.50.10.5     | DNS already correct
  [?!]  Loopback0      on tst-fw01     | 10.50.255.1    | EXISTS: 'tst-fw01-n1.net.dccat.dk' (Proposed: lo0.tst-fw01-n1.net.dccat.dk)
---------------------------------------------------------------------------

5 IP addresses ready for DNS update in Netbox.
Do you want to write these changes to Netbox now? (y/n): n
Changes cancelled. Nothing written to Netbox.
```

### Forklaring af statuser:
* `[NEW]` (Nyt): Netbox har intet DNS navn på denne IP. Scriptet viser her sit forslag.
* `[OK]` (Korrekt): Det eksisterende DNS navn i Netbox er allerede præcis det samme som scriptet ville foreslå. Der behøver ikke gøres noget.
* `[?!]` (Findes / Afviger): Der er allerede skrevet et DNS navn i Netbox, men scriptets logik ville foreslå noget andet.
* `[!]` (Fejl / Mangler): IP-adressen kan ikke behandles, typisk fordi den bare "ligger" i IPAM, men ikke er knyttet fysisk til en port på en switch eller en router.
