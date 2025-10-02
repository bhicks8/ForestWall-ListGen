"""
Helper that fetches and parses input files and yields lines one by one.
"""

import json

def parse_hostlist(lines, opts):
    return [line.strip() for line in lines if line and not line.startswith('#')]

def parse_spamhaus_json(lines, opts):
    data = [json.loads(line) for line in lines if line]
    return [item['cidr'] for item in data if 'cidr' in item]

def parse_inet_ip_info_geo(lines, opts):
    if 'country' not in opts:
        raise ValueError("opts must include 'country' for inet-ip-info-geo strategy")
    
    country = opts['country'].upper()
    cells = [line.split('\t') for line in lines if line]
    return [cell[1].strip() for cell in cells if cell[1] and cell[0] and cell[0].upper() == country]

def get_parse(strategy):
    """
    Get a parsing function by strategy name.    
    
    """
    strategy = (strategy or "").lower()

    if strategy == 'hostlist':
        return parse_hostlist
    elif strategy == 'spamhaus-json':
        return parse_spamhaus_json
    elif strategy == 'inet-ip-info-geo':
        return parse_inet_ip_info_geo
    else:
        raise ValueError(f"Unknown parsing strategy: {strategy}")
