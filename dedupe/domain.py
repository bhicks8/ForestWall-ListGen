from .domainTrie import DomainTrie

class DomainTrieDedupe:
    """
    Simple deduplicator for domains using a DomainTrie for storage.
    Text is normalized to lowercase before adding/checking.
    Supports wildcards at the leftmost label only (e.g. *.example.com).
    """
    def __init__(self):
        self.trie = DomainTrie()

    def __len__(self):
        return len(self.trie)

    def addMany(self, items):
        for item in items:
            self.add(item)
    
    def add(self, item):
        return self.trie.add(item)

    def remove(self, item):
        item = item.lower()
        self.trie.remove(item)

    def contains(self, item):
        item = item.lower()
        return self.trie.contains(item)

    def all(self):
        return sorted(list(self.trie.iter_domains()))

    def reset(self):
        self.trie = DomainTrie()