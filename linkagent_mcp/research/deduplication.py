import hashlib
class Deduplicator:
    def __init__(self): self.seen=set()
    def is_duplicate(self, url: str, content: str=""):
        h=hashlib.sha256((url+content).encode()).hexdigest()
        if h in self.seen: return True
        self.seen.add(h); return False
    def canonical(self, url: str): return url.split("?")[0].rstrip("/").lower()
