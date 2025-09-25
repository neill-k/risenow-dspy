import dspy

from agents import vendor_agent


def _make_tool(name: str) -> dspy.Tool:
    def _runner(**_: object) -> None:
        return None

    return dspy.Tool(_runner, name=name, desc=f"{name} tool")


def test_create_vendor_agent_includes_contact_tool(monkeypatch):
    base_tools = (_make_tool("search"), _make_tool("extract"))

    monkeypatch.setattr(vendor_agent, "create_dspy_tools", lambda: base_tools)

    contact_tool = _make_tool("lookup_vendor_contacts")
    monkeypatch.setattr(vendor_agent, "create_vendor_contact_tool", lambda: contact_tool)

    agent = vendor_agent.create_vendor_agent(max_iters=3)

    assert "lookup_vendor_contacts" in agent.tools
    assert agent.tools["lookup_vendor_contacts"] is contact_tool
