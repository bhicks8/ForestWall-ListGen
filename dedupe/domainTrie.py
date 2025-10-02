class DomainTrie:
    _TERM = "__terminal__"
    _WILDCARD = "__wildcard__"

    def __init__(self):
        self.root = {}

    def _normalize(self, domain):
        cleaned = (domain or "").strip().lower().strip('.')
        if not cleaned:
            raise ValueError("domain must be a non-empty string")
        return cleaned

    def add(self, domain):
        normalized = self._normalize(domain)
        original_labels = normalized.split('.')
        is_wildcard = original_labels[0] == '*'
        effective_labels = original_labels[1:] if is_wildcard else original_labels

        if not effective_labels:
            raise ValueError("wildcard must target at least one domain label")

        labels = list(reversed(effective_labels))

        node = self.root
        for label in labels:
            if self._WILDCARD in node:
                return False
            node = node.setdefault(label, {})

        if is_wildcard:
            node.clear()  # remove all more specific entries
            node[self._WILDCARD] = True
        else:
            node[self._TERM] = True
        return True

    def remove(self, domain):
        """Remove a domain or wildcard from the trie. Returns True if removed, False if not found."""
        normalized = self._normalize(domain)
        original_labels = normalized.split('.')
        is_wildcard = original_labels[0] == '*'
        effective_labels = original_labels[1:] if is_wildcard else original_labels

        if not effective_labels:
            raise ValueError("wildcard must target at least one domain label")

        labels = list(reversed(effective_labels))

        # Navigate to the target node, tracking the path
        path = [(self.root, None)]
        node = self.root
        for label in labels:
            if label not in node:
                return False  # Domain not in trie
            path.append((node, label))
            node = node[label]

        # Check if the target marker exists
        marker = self._WILDCARD if is_wildcard else self._TERM
        if marker not in node:
            return False  # Domain not in trie

        # Remove the marker
        del node[marker]

        # Clean up empty nodes from leaf to root
        for i in range(len(path) - 1, 0, -1):
            parent, label = path[i]
            child = parent[label]
            # Remove child if it's now empty (no markers, no children)
            if not child:
                del parent[label]
            else:
                break  # Stop if node still has content

        return True

    def contains(self, domain):
        normalized = self._normalize(domain)
        labels = list(reversed(normalized.split('.')))

        node = self.root
        for idx, label in enumerate(labels):
            if label not in node:
                return False
            node = node[label]
            # Check wildcard only when exactly one more label remains (immediate child only)
            remaining = len(labels) - idx - 1
            if self._WILDCARD in node and remaining == 1:
                return True

        return self._TERM in node

    def __len__(self):
        """Return the count of stored domains (both concrete and wildcards)."""
        return self._count_entries(self.root)

    def _count_entries(self, node):
        count = 0
        if self._TERM in node or self._WILDCARD in node:
            count = 1
        for key, child in node.items():
            if key not in (self._TERM, self._WILDCARD):
                count += self._count_entries(child)
        return count

    def iter_domains(self):
        """Yield all stored domains in lexicographic order."""
        yield from self._iter_recursive(self.root, [])

    def _iter_recursive(self, node, path):
        if self._WILDCARD in node:
            yield '*.' + '.'.join(reversed(path))
        if self._TERM in node:
            yield '.'.join(reversed(path))
        for label, child in sorted(node.items()):
            if label not in (self._TERM, self._WILDCARD):
                yield from self._iter_recursive(child, path + [label])