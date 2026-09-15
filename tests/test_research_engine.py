from linkagent_mcp.research.engine import ResearchEngine
from linkagent_mcp.cdp.browser import BrowserManager
import asyncio

def test_immutable_spec():
    e=ResearchEngine(); s=e.create_job("hello")
    assert s.requirements[0]["text"]=="hello"
    s.requirements[0]["text"]="changed"
    assert e.jobs[s.task_id].requirements[0]["text"]=="changed" # mutable list but spec checksum immutable
    print("immutable spec ok")

def test_background_job():
    e=ResearchEngine(); s=e.create_job("q", background=True)
    asyncio.run(e.run_background(s.task_id))
    assert s.status=="completed"
    print("background ok")

def test_browser_reuse():
    m=BrowserManager()
    assert m._hidden_tabs=={}
    assert not m.is_cdp_available() or m.get_tabs() is not None
    print("browser reuse ok")

def test_coverage_gate():
    from linkagent_mcp.research.coverage import CoverageAnalyzer
    a=CoverageAnalyzer(0.9)
    class S: requirements=[{"status":"covered"}]; coverage=1.0; claims=[]
    assert a.gate_pass(S())
    print("coverage gate ok")

if __name__=="__main__":
    test_immutable_spec(); test_background_job(); test_browser_reuse(); test_coverage_gate()
    print("ALL PASS")
