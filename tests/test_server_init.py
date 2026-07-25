import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_server_imports():
    from linkagent_mcp.server import _create_server, BROWSER_TOOLS
    assert _create_server is not None
    assert len(BROWSER_TOOLS) == 5


def test_config_defaults():
    from linkagent_mcp.config import Config, get_config
    cfg = get_config()
    assert cfg.cdp_host == "127.0.0.1"
    assert cfg.cdp_port == 9222
    assert cfg.log_level == "INFO"
    assert cfg.server_name == "linkagent"


def test_registry_starts_empty():
    from linkagent_mcp.core.registry import registry
    assert registry.list_tools() == []


def test_auto_discover_does_not_crash():
    from linkagent_mcp.sites import auto_discover
    from linkagent_mcp.core.registry import Registry
    reg = Registry()
    auto_discover(reg)


def test_browser_manager_starts_without_cdp():
    from linkagent_mcp.cdp.browser import BrowserManager
    mgr = BrowserManager()
    assert not mgr.is_cdp_available()


def test_server_creation():
    from linkagent_mcp.server import _create_server
    server = _create_server()
    assert server is not None


def test_all_site_modules_import():
    from linkagent_mcp.sites.linkedin import register
    from linkagent_mcp.core.registry import Registry
    reg = Registry()
    register(reg)
    tools = reg.list_tools()
    assert len(tools) == 5
