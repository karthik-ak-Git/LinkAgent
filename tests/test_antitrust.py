"""B01-B09 anti-trust"""
from linkagent_mcp.research.engine import ResearchEngine
import asyncio
def test_B01_keyword_retention():
    e=ResearchEngine(); s=e.create_job("compare frameworks with auth")
    assert "auth" in s.requirements[0]["text"]
def test_B04_correction():
    e=ResearchEngine(); s=e.create_job("old"); s.claims.append(type('C',(),{'text':'hyp','status':'supported'})())
    e.apply_correction(s.task_id,"new query")
    assert s.claims[0].status=="unverified"
def test_B09_coverage_illusion():
    from linkagent_mcp.research.coverage import CoverageAnalyzer
    a=CoverageAnalyzer(0.9)
    class S: requirements=[{"status":"missing"}]; coverage=0; claims=[]
    assert not a.gate_pass(S())
    print("B01-B09 PASS")
if __name__=="__main__":
    test_B01_keyword_retention(); test_B04_correction(); test_B09_coverage_illusion()
    print("ALL ANTITRUST PASS")
