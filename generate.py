#!/usr/bin/env python3

# Simple script that:
#    1. Queries lists from lists.yaml
#    2. Downloads each list file
#    3. Generates a single combined list file, removing duplicates
# Usage: python generate.py <config_file> <output_dir>
# Intended for use as part of GitHub Actions workflow, but can be run manually as well.

import yaml
import json
import requests
import gzip
import os

def load_lists_config(config_path):
    with open(config_path, 'r') as file:
        return yaml.safe_load(file)
    
def parse_list(list_content, strategy, strategy_options):
    if strategy == 'hostlist':
        return [line.strip() for line in list_content.splitlines() if line and not line.startswith('#')]
    
    elif strategy == 'spamhaus-json':
        lines = list_content.splitlines()
        data = [json.loads(line) for line in lines if line and not line.startswith('#')]
        return [item['cidr'] for item in data if 'cidr' in item]
    
    elif strategy == 'inet-ip-info-geo':
        if 'country' not in strategy_options:
            raise ValueError("strategy_options must include 'country' for inet-ip-info-geo strategy")
        
        country = strategy_options['country'].upper()
        lines = list_content.splitlines()
        cells = [line.split('\t') for line in lines if line]
        return [cell[1].strip() for cell in cells if cell[1] and cell[0] and cell[0].upper() == country]
    
    else:
        raise ValueError(f"Unknown parsing strategy: {strategy}")

def get_list(url, compression, strategy, strategy_options):
    response = requests.get(url)
    response.raise_for_status()
    
    if compression == "gzip":
        content = gzip.decompress(response.content).decode('utf-8')
    elif compression == "none":
        content = response.text
    else:
        raise ValueError(f"Unknown compression type: {compression}")

    return parse_list(content, strategy, strategy_options)

def save_combined_list(combined_list, output_path):
    with open(output_path, 'w') as file:
        for item in sorted(combined_list):
            file.write(f"{item}\n")

def main(config_file, output_dir):
    if not config_file or not output_dir:
        raise ValueError("Both config_file and output_dir must be provided.")
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    config = load_lists_config(config_file)
    output_dir = os.path.abspath(output_dir)

    for list_info in config.get('lists', []):
        name = list_info.get('name')
        if (not name):
            raise ValueError("Each list must have a 'name' field.")
        
        combined_set = set() # Using a set to avoid duplicates
        exclude = set(list_info.get('exclude', [])) # Entries to exclude from the final list

        print(f"\nProcessing list: {name} with {len(exclude)} exclusions.")
        for url_info in list_info.get('sources', []):
            url = url_info.get('url')
            url_compression = url_info.get('compression', 'none') # Default to 'none' if not specified

            if not isinstance(url, str) or not url:
                raise ValueError(f"Each URL must be a non-empty string. Received: '{url}'")

            strategy = url_info.get('format', 'hostlist') # Default to 'hostlist' if not specified
            strategy_options = url_info.get('format_options', {}) # Additional options for parsing strategies
            print(f"Fetching list from {url} using format: '{strategy}'")

            try:
                entries = get_list(url, url_compression, strategy, strategy_options)
                combined_set.update([entry for entry in entries if entry not in exclude])
                print(f"Added {len(entries)} entries from {url}. Set size is now {len(combined_set)}.")
            except Exception as e:
                print(f"Error fetching or parsing list from {url}: {e}")

        output_path = os.path.join(output_dir, name + ".txt")
        save_combined_list(combined_set, output_path)
        print(f"Combined list {name} saved to {output_path} with {len(combined_set)} unique entries.")

if __name__ == "__main__":
    if len(os.sys.argv) != 3:
        print("Usage: python generate.py <config_file> <output_dir>")
        os.sys.exit(1)

    config_file = os.sys.argv[1]
    output_dir = os.sys.argv[2]
    main(config_file, output_dir)