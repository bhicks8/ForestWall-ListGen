"""
Helper to get an output function to write lists to a file format.
"""

import os

def write_lines(file, content):
    with open(file, 'w') as f:
        for line in content:
            f.write(f"{line}\n")


def hostlist_per_family(output_path, output_name, combined_list, opts):
    path = output_path + "/" + output_name

    combined_list = sorted(combined_list)
    ipv4_list = [item for item in combined_list if '.' in item]
    ipv6_list = [item for item in combined_list if ':' in item]

    if (len(combined_list) > 0):
        combined_file = path +  ".combined.txt"
        ipv4_list_file = path + ".ipv4.txt"
        ipv6_list_file = path + ".ipv6.txt"

        write_lines(combined_file, combined_list)
        if len(ipv4_list) > 0:
            write_lines(ipv4_list_file, ipv4_list)
        if len(ipv6_list) > 0:
            write_lines(ipv6_list_file, ipv6_list)

def rpz_file(output_path, output_name, combined_list, opts):
    path = output_path + "/" + output_name + ".rpz"

    combined_list = sorted(combined_list)
    rpz_lines = [f"{item} CNAME ." for item in combined_list]

    if (opts.get('block_subdomains', False)):
        rpz_lines += [f"*.{item} CNAME ." for item in combined_list]

    if (len(rpz_lines) > 0):
        write_lines(path, rpz_lines)

def get(output_type):
    """
    Get an output function by type.

    Supported types:
      - 'hostlist_per_family' -> writes combined, ipv4-only, and ipv6-only files
      - 'rpz' -> writes a RPZ file for DNS blocking in e.g. BIND or Knot.
      - 'none' -> no output (used for testing and/or exclusions)
    """

    output_type = (output_type or "").lower()
    if output_type in ("hostlist_per_family", "per_family", "family"):
        return hostlist_per_family
    elif output_type in ("rpz"):
        return rpz_file
    elif output_type in ("none"):
        return lambda output_path, output_name, combined_list, opts: None

    raise ValueError(f"Unknown output type: {output_type}")