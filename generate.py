#!/usr/bin/env python3
"""
List Generation Tool

Fetches, parses, deduplicates, and saves IP/domain blocklists from YAML configuration.
Supports multiple input formats, compression types, and output formats.

Usage:
    python generate.py <config_file> <output_dir>

Example:
    python generate.py lists.yaml ./lists
"""

import gzip
import os
import sys

import requests
import yaml

import dedupe
import input as input_parsers
import output as output_writers


CLI_HELP = """
Usage: python generate.py <config_file> <output_dir>
  config_file: Path to the YAML configuration file (e.g., 'lists.yaml')
  output_dir: Directory to save the generated list files (e.g., 'lists')
"""


# ============================================================================
# Logging Utilities
# ============================================================================

class Logger:
    """Simple structured logger for CI/CD-friendly output."""
    
    # ANSI color codes
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    RESET = '\033[0m'
    
    @staticmethod
    def _format(message, prefix='', color=''):
        """Format message with optional prefix and color."""
        if prefix:
            return f"{color}{prefix}{Logger.RESET} {message}"
        return f"{color}{message}{Logger.RESET}"
    
    @staticmethod
    def header(message):
        """Print a major section header."""
        bar = '═' * 60
        print(f"\n{Logger.BOLD}{Logger.BLUE}{bar}{Logger.RESET}")
        print(f"{Logger.BOLD}{Logger.BLUE}▶ {message}{Logger.RESET}")
        print(f"{Logger.BOLD}{Logger.BLUE}{bar}{Logger.RESET}")
    
    @staticmethod
    def section(message):
        """Print a subsection header."""
        print(f"\n{Logger.BOLD}{Logger.CYAN}┌─ {message}{Logger.RESET}")
    
    @staticmethod
    def info(message, indent=False):
        """Print an info message."""
        prefix = '  │' if indent else '│'
        print(Logger._format(message, prefix, Logger.CYAN))
    
    @staticmethod
    def success(message, indent=False):
        """Print a success message."""
        prefix = '  ✓' if indent else '✓'
        print(Logger._format(message, prefix, Logger.GREEN))
    
    @staticmethod
    def detail(key, value, indent=False):
        """Print a key-value detail."""
        prefix = '  │' if indent else '│'
        print(f"{Logger.CYAN}{prefix} {Logger.BOLD}{key}:{Logger.RESET} {value}")
    
    @staticmethod
    def summary(items_dict):
        """Print a summary box with key metrics."""
        print(f"{Logger.BOLD}{Logger.CYAN}└─ Summary{Logger.RESET}")
        for key, value in items_dict.items():
            print(f"  {Logger.BOLD}{key}:{Logger.RESET} {Logger.GREEN}{value}{Logger.RESET}")


# ============================================================================
# Configuration Loading
# ============================================================================

def load_config(config_path):
    """Load and parse YAML configuration file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


# ============================================================================
# Source Fetching and Parsing
# ============================================================================

def fetch_content(url, binary=False):
    """
    Fetch content from URL or local file.
    
    Args:
        url: HTTP(S) URL or file:// path
        binary: Whether to return binary content
        
    Returns:
        Content as bytes (binary=True) or string (binary=False)
    """
    if url.startswith('http://') or url.startswith('https://'):
        response = requests.get(url)
        response.raise_for_status()
        return response.content if binary else response.text
    
    # Handle local files
    file_path = url[7:] if url.startswith('file://') else url
    mode = 'rb' if binary else 'r'
    with open(file_path, mode) as f:
        return f.read()


def decompress_content(content, compression):
    """
    Decompress content based on compression type.
    
    Args:
        content: Raw content (string or bytes)
        compression: Compression type ('gzip', 'none')
        
    Returns:
        Decompressed string content
    """
    if compression == 'gzip':
        return gzip.decompress(content).decode('utf-8')
    elif compression == 'none':
        return content
    else:
        raise ValueError(f"Unknown compression type: {compression}")


def fetch_and_parse_source(url, compression, format_type, format_options):
    """
    Fetch and parse a single source list.
    
    Args:
        url: Source URL or file path
        compression: Compression type ('gzip', 'none')
        format_type: Parser strategy name
        format_options: Additional options for parser
        
    Returns:
        List of parsed entries
    """
    if not isinstance(url, str) or not url:
        raise ValueError(f"URL must be a non-empty string. Received: '{url}'")
    
    # Fetch content
    binary = (compression == 'gzip')
    content = fetch_content(url, binary)
    
    # Decompress if needed
    content = decompress_content(content, compression)
    
    # Parse content
    parser = input_parsers.get_parse(format_type)
    return parser(content.splitlines(), format_options)


# ============================================================================
# List Processing
# ============================================================================

def build_list(name, dedupe_strategy, sources):
    """
    Build a deduplicated list from multiple sources.
    
    Args:
        name: List name (for logging)
        dedupe_strategy: Deduplication strategy ('simple', 'radix', 'domain')
        sources: List of source configurations
        
    Returns:
        Deduplicator instance containing all entries
    """
    if not name:
        raise ValueError("List must have a 'name' field.")
    
    deduplicator = dedupe.get(dedupe_strategy)
    Logger.section(f"Fetching {len(sources)} source(s) for '{name}'")
    
    for idx, source in enumerate(sources, 1):
        url = source.get('url')
        compression = source.get('compression', 'none')
        format_type = source.get('format', 'hostlist')
        format_options = source.get('format_options', {})
        
        entries = fetch_and_parse_source(url, compression, format_type, format_options)
        deduplicator.addMany(entries)
        
        # Truncate long URLs for display
        display_url = url if len(url) < 70 else url[:67] + '...'
        Logger.info(f"[{idx}/{len(sources)}] {display_url}", indent=True)
        Logger.detail('Added', f"{len(entries):,} entries → Total: {len(deduplicator):,}", indent=True)
    
    return deduplicator


def apply_exclusions(list_items, exclusion_entries):
    """
    Remove exclusion entries from list.
    
    Args:
        list_items: Deduplicator instance to modify
        exclusion_entries: Set of entries to exclude
    """
    for item in exclusion_entries:
        if list_items.contains(item):
            list_items.remove(item)


def validate_exclusion_list(list_name, exclude_name, lists_with_exclusions):
    """
    Validate that exclusion list doesn't itself have exclusions.
    
    Raises:
        ValueError if exclusion list has exclusions
    """
    if exclude_name in lists_with_exclusions:
        raise ValueError(
            f"List '{list_name}' references exclusion list '{exclude_name}', "
            f"but exclusion lists cannot themselves have exclusions."
        )


def find_list_config(lists, list_name):
    """Find list configuration by name."""
    config = next((lst for lst in lists if lst.get('name') == list_name), None)
    if not config:
        raise ValueError(f"List '{list_name}' not found in configuration.")
    return config


# ============================================================================
# Main Processing
# ============================================================================

def process_single_list(list_config, all_lists, exclusion_cache):
    """
    Process a single list configuration.
    
    Args:
        list_config: Configuration for this list
        all_lists: All list configurations (for exclusion lookup)
        exclusion_cache: Dict caching loaded exclusion lists
        
    Returns:
        Deduplicator instance with final entries
    """
    name = list_config.get('name')
    Logger.header(f"Processing '{name}'")
    
    # Build main list
    list_items = build_list(
        name,
        list_config.get('dedupe', 'simple'),
        list_config.get('sources', [])
    )
    
    initial_size = len(list_items)
    
    # Apply exclusions if specified
    exclude_value = list_config.get('exclude', '')
    exclude_name = exclude_value if isinstance(exclude_value, str) else ''
    exclude_name = exclude_name.strip()
    
    if exclude_name:
        # Get list of all lists that have exclusions
        lists_with_exclusions = {
            lst.get('name') for lst in all_lists if lst.get('exclude')
        }
        
        validate_exclusion_list(name, exclude_name, lists_with_exclusions)
        
        # Load exclusion list (cached)
        if exclude_name not in exclusion_cache:
            Logger.section(f"Loading exclusion list '{exclude_name}'")
            exclude_config = find_list_config(all_lists, exclude_name)
            exclusion_deduper = build_list(
                exclude_name,
                exclude_config.get('dedupe', 'simple'),
                exclude_config.get('sources', [])
            )
            exclusion_cache[exclude_name] = exclusion_deduper.all()
        
        # Apply exclusions
        exclusion_entries = exclusion_cache[exclude_name]
        Logger.section(f"Applying exclusions from '{exclude_name}'")
        Logger.info(f"Removing {len(exclusion_entries):,} entries", indent=True)
        apply_exclusions(list_items, exclusion_entries)
    
    final_size = len(list_items)
    excluded = initial_size - final_size
    
    Logger.summary({
        'Initial': f"{initial_size:,} entries",
        'Excluded': f"{excluded:,} entries" if excluded > 0 else "0 entries",
        'Final': f"{final_size:,} entries"
    })
    
    return list_items


def save_list(list_items, output_dir, name, output_format, output_options):
    """Save list to output files."""
    writer = output_writers.get(output_format)
    writer(output_dir, name, list_items.all(), output_options)
    Logger.success(f"Saved to {output_dir} ({len(list_items):,} entries)")


def main(config_file, output_dir):
    """
    Main entry point for list generation.
    
    Args:
        config_file: Path to YAML configuration file
        output_dir: Directory to save generated lists
    """
    if not config_file or not output_dir:
        raise ValueError("Both config_file and output_dir must be provided.")
    
    # Print startup banner
    print(f"\n{Logger.BOLD}{Logger.BLUE}╔══════════════════════════════════════════════════════════╗{Logger.RESET}")
    print(f"{Logger.BOLD}{Logger.BLUE}║{Logger.RESET}          {Logger.BOLD}ForestWall List Generator{Logger.RESET}                       {Logger.BOLD}{Logger.BLUE}║{Logger.RESET}")
    print(f"{Logger.BOLD}{Logger.BLUE}╚══════════════════════════════════════════════════════════╝{Logger.RESET}")
    Logger.detail('Config', config_file)
    Logger.detail('Output', output_dir)
    
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    output_dir = os.path.abspath(output_dir)
    
    # Load configuration
    config = load_config(config_file)
    lists = config.get('lists', [])
    Logger.info(f"Loaded {len(lists)} list(s) from configuration\n")
    
    # Cache for exclusion lists
    exclusion_cache = {}
    
    # Process each list
    total_entries = 0
    for list_config in lists:
        name = list_config.get('name')
        
        # Build and filter list
        list_items = process_single_list(list_config, lists, exclusion_cache)
        
        # Save output
        output_format = list_config.get('output_format', 'hostlist_per_family')
        output_options = list_config.get('output_options', {})
        save_list(list_items, output_dir, name, output_format, output_options)
        
        total_entries += len(list_items)
    
    # Print completion summary
    print(f"\n{Logger.BOLD}{Logger.GREEN}{'═' * 60}{Logger.RESET}")
    print(f"{Logger.BOLD}{Logger.GREEN}✓ Generation Complete{Logger.RESET}")
    Logger.detail('Lists Generated', len(lists))
    Logger.detail('Total Entries', f"{total_entries:,}")
    Logger.detail('Output Directory', output_dir)
    print(f"{Logger.BOLD}{Logger.GREEN}{'═' * 60}{Logger.RESET}\n")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(CLI_HELP)
        sys.exit(1)
    
    config_file = sys.argv[1]
    output_dir = sys.argv[2]
    main(config_file, output_dir)