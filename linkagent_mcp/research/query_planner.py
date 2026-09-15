import itertools
TYPES=["DISCOVERY","PRIMARY_SOURCE","TECHNICAL","DOCUMENTATION","ALTERNATIVE_SOURCE","CONTRADICTION","HISTORICAL","COMMUNITY","LOCAL","VERIFICATION"]
class QueryPlanner:
    def __init__(self): self.counter=0
    def plan(self, gap, budget_remaining):
        # adaptive allocation §41
        qtype=TYPES[self.counter%len(TYPES)]
        self.counter+=1
        return {"query":f"{gap} {qtype.lower()}", "type":qtype, "targets":["R1"], "reason":f"gap: {gap}"}
