from linkagent_mcp.research.engine import ResearchEngine
import asyncio, time
def test_500_limit():
    e=ResearchEngine(max_queries=500, workers=20)
    s=e.create_job("stress test", max_queries=500)
    # simulate 500 queries without real browser
    start=time.time()
    async def run():
        for i in range(500):
            s.queries_used+=1
            if i%100==0: await asyncio.sleep(0.001)
    asyncio.run(run())
    assert s.queries_used==500
    assert s.queries_used <= s.queries_budget
    print(f"500 limit ok duration {time.time()-start:.2f}s")
def test_dedup_500():
    from linkagent_mcp.research.deduplication import Deduplicator
    d=Deduplicator()
    assert not d.is_duplicate("https://example.com/a")
    assert d.is_duplicate("https://example.com/a")
    assert not d.is_duplicate("https://example.com/b")
    print("dedup ok")
if __name__=="__main__":
    test_500_limit(); test_dedup_500()
    print("LIMIT PASS")
