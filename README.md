# ForestWall-ListGen

A list generation tool for the [ForestWall](https://github.com/bhicks8/ForestWall) project.

## Overview

ForestWall-ListGen downloads, parses, and combines IP/CIDR blocklists from multiple sources into unified lists. It automatically removes duplicates and supports various list formats, making it easy to maintain up-to-date threat intelligence feeds for ForestWall.

## Motivation

The internet is a dynamic, rapidly changing place. Threat actors constantly shift infrastructure, new malicious IPs emerge, and legitimate services change their networks. ForestWall addresses some of these challenges by embracing immutability principles that protect the router, however that creates its own issues that need to be overcome.

Re-deploying edge routers with new firewall images for every IP list change simply isn't viable in production environments. Instead, ForestWall needs to allow specific features—like IP blocklists—to be fetched and loaded into the packet filter (e.g., nftables) at runtime, keeping rules current without compromising the immutable filesystem.

### The ForestWall-ListGen Approach

This tool pre-generates consolidated, deduplicated blocklists from multiple threat intelligence sources and allows you to host them at stable URLs. ForestWall instances can then:

1. **Fetch lists on-demand**: Download current lists at boot or on a schedule
2. **Load into memory**: Apply rules directly to nftables/iptables without disk writes
3. **Stay current**: Automatically benefit from updated threat intelligence without redeployment
4. **Maintain immutability**: The filesystem remains read-only; no persistent changes are made

### Key Benefits

#### Centralized List Management

- Combine multiple threat feeds into curated, purpose-built lists
- One source of truth for all ForestWall instances that you manage.
- Version control and audit trails through Git history

#### Operational Efficiency

- Update blocklists independently from firewall deployments
- No need to rebuild and redeploy router images for list updates
- Reduce bandwidth: fetch one consolidated list instead of multiple upstream sources per router
- Less computational overhead: Routers dont need to scan and consolidate lists on their own. The hard work is already done.

#### Security & Transparency

- Pre-process and validate lists in CI/CD before making them available
- Review changes before they reach production routers
- Minimize attack surface on edge routers (they fetch simple text files, not complex parsers)

#### Flexibility

- Different ForestWall instances can subscribe to different list combinations
- Easy rollback by hosting multiple list versions
- Geographic filtering and custom exclusions tailored to your needs

## Features

- **Multiple source formats**: Currently supports hostlist, Spamhaus JSON, and geographic IP databases
- **Automatic deduplication**: Combines entries from multiple sources while removing duplicates
- **Exclusion lists**: Filter out specific IPs/CIDRs (e.g., private IP ranges)
- **Flexible compression**: Handles both plain text and gzip-compressed sources
- **Geographic filtering**: Generate lists by country using inet-ip-info data

## Usage

### Generating Lists

#### GitHub / DevOps

This repo includes workflow that runs `generate.py` and stores resulting lists in `lists/*.txt`. Each line in each file holds a valid CIDR.

You may:

1. Link to the provided lists, if they suite your needs.
2. Fork the repository to modify `lists.yaml` and either:
    1. Leverage the workflow capability to generate and add your lists.
    2. Remove the workflow, and publish to a web host of your choice using CI/CD.

#### Command Line

```bash
python generate.py <config_file> <output_dir>
```

Example:

```bash
python generate.py lists.yaml .
```

This reads the configuration from `lists.yaml` and outputs generated list files to the current directory.

### Using the lists

#### ForestWall

> **TODO:** Validate this section once ForestWall is further along.

1. Update `/etc/conf.d/forestwall/nft-lists.conf` with a mapping of nftables set => list URL.
2. Ensure you have a `/etc/periodic/daily.d/load-nftlists.sh` script (included by default).

## Configuration

Lists are defined in `lists.yaml`. Each list can have:

- **name**: Output filename (without .txt extension)
- **description**: Human-readable description of the list
- **sources**: Array of URLs to fetch and combine
  - **url**: The source URL
  - **format**: Parsing strategy (`hostlist`, `spamhaus-json`, or `inet-ip-info-geo`)
  - **format_options**: Format-specific options (e.g., country code for geo lists)
  - **compression**: Optional, `gzip` or `none` (default: `none`)
- **exclude**: Optional array of IPs/CIDRs to exclude from the final list. You should use this to ensure known safe IP's are not blocked.

### Example Configuration

```yaml
lists:
  - name: "blackhole"
    description: "Known malicious IPs"
    exclude: [10.0.0.0/8, 192.168.0.0/16]
    sources:
      - url: https://rules.emergingthreats.net/fwrules/emerging-Block-IPs.txt
        format: "hostlist"
      - url: https://www.spamhaus.org/drop/drop_v4.json
        format: "spamhaus-json"
  
  - name: "geo-china"
    description: "All IP ranges allocated to China"
    sources:
      - url: https://github.com/inet-ip-info/WorldIPv4Map/releases/latest/download/all-ipv4cidr.tsv.gz
        format: "inet-ip-info-geo"
        format_options:
          country: "CN"
        compression: "gzip"
```

## Requirements

- Python 3.x
  - `requests`
  - `PyYAML`

## Part of ForestWall

ForestWall is a small-scale, open-source, immutable firewall project focused on security and reliability. ForestWall-ListGen provides the threat intelligence feeds that power ForestWall's blocking capabilities.

## License

See [LICENSE](LICENSE) file for details.