class CoverageAnalyzer:
    def __init__(self, threshold=0.9): self.threshold=threshold
    def compute(self, state):
        if not state.requirements: return 1.0
        covered=sum(1 for r in state.requirements if r.get("status")=="covered")
        return covered/len(state.requirements)
    def gate_pass(self, state):
        # §23 coverage gate
        if any(r.get("status")=="missing" for r in state.requirements): return False
        if any(c.status=="contradicted" for c in state.claims): return False
        return state.coverage >= self.threshold
