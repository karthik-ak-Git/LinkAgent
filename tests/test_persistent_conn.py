import asyncio
import sys
import os
import time
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from linkagent_mcp.cdp.client import CDPClient
from linkagent_mcp.cdp.browser import BrowserManager
from linkagent_mcp.config import get_config

async def test_persistent():
    cfg = get_config()
    bm = BrowserManager(cdp_host=cfg.cdp_host, cdp_port=cfg.cdp_port)
    tab = bm.get_any_tab()
    if not tab:
        print("No tab"); return
    print(f"Tab: {tab.title[:50]}")
    
    client = CDPClient(tab.ws_url)
    await client.connect()
    
    # Call 1: Get title
    t0 = time.time()
    title1 = await client.get_title()
    dt1 = time.time() - t0
    print(f"Call 1 ({dt1*1000:.0f}ms): {title1}")
    
    # Call 2: Get URL
    t0 = time.time()
    url = await client.get_url()
    dt2 = time.time() - t0
    print(f"Call 2 ({dt2*1000:.0f}ms): {url[:60]}")
    
    # Call 3: Evaluate JS
    t0 = time.time()
    js = 'document.querySelectorAll("button").length'
    count = await client.evaluate(js)
    dt3 = time.time() - t0
    print(f"Call 3 ({dt3*1000:.0f}ms): {count} buttons")
    
    # Call 4: Navigate
    t0 = time.time()
    await client.navigate("https://www.linkedin.com/feed/")
    dt4 = time.time() - t0
    title4 = await client.get_title()
    print(f"Call 4 ({dt4*1000:.0f}ms): navigated -> {title4}")
    
    await client.disconnect()
    print("Persistent connection works!")

asyncio.run(test_persistent())
