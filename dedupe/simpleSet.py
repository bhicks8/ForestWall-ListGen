class SimpleSetDedupe:
    """
    A simple deduplication class using a set to track seen items.
    Text is noramalized to lowercase before adding/checking.
    """
    def __init__(self):
        self.seen = set()

    def __len__(self):
        return len(self.seen)

    def addMany(self, items):
        for item in items:
            self.add(item)
    
    def add(self, item):
        item = item.lower()
        if item in self.seen:
            return False
        self.seen.add(item)
        return True
    
    def remove(self, item):
        item = item.lower()
        self.seen.discard(item)

    def contains(self, item):
        item = item.lower()
        return item in self.seen
    
    def all(self):
        return sorted(list(self.seen))
    
    def reset(self):
        self.seen.clear()