class ContradictionDetector:
    def scan(self, state):
        # naive: if two claims have same text but different status -> contradicted
        seen={}
        for c in state.claims:
            if c.text in seen and seen[c.text]!=c.status:
                c.status="contradicted"
            seen[c.text]=c.status
