"""
dedupe package — small collection of deduplication helpers.

Public API:
- RadixDedupe
- SimpleSetDedupe
- get(factory_name) -> helper factory to create one of the implementations
"""

from .radix import RadixDedupe
from .simpleSet import SimpleSetDedupe
from .domain import DomainTrieDedupe

__all__ = [
    "RadixDedupe",
    "SimpleSetDedupe",
    "DomainTrieDedupe",
    "get",
]

def get(kind: str):
    """
    Factory helper to create a dedupe instance.

    kind:
      - 'radix' -> returns RadixDedupe()
      - 'set'   -> returns SimpleSetDedupe()
      - 'domain' -> returns DomainTrieDedupe()

    Raises ValueError on unknown kind.
    """

    kind = (kind or "").lower()
    if kind in ("radix", "pytricia"):
        return RadixDedupe()
    if kind in ("set", "simpleset", "simple"):
        return SimpleSetDedupe()
    if kind in ("domain", "domaintrie"):
        return DomainTrieDedupe()
    raise ValueError(f"Unknown dedupe kind: {kind}")