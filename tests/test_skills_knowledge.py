
from genesis.knowledge.graph import KnowledgeGraph
from genesis.skills.registry import Skill, SkillRegistry


async def test_skill_registry_register_and_run():
    reg = SkillRegistry()

    async def greet(name: str = "world") -> str:
        return f"hello {name}"

    reg.register(Skill(name="greet", description="greet someone", tags=["demo"], fn=greet))
    assert reg.get("greet") is not None
    assert await reg.get("greet").run(name="genesis") == "hello genesis"
    assert len(reg.list()) == 1
    assert reg.find("demo")[0].name == "greet"
    assert reg.find("missing") == []


def test_knowledge_graph_query_and_neighbors():
    kg = KnowledgeGraph()
    kg.add("Coder", "implements", "Feature")
    kg.add("Reviewer", "reviews", "Feature")
    assert kg.size == 2
    assert len(kg.query(obj="Feature")) == 2
    assert len(kg.query(subject="Coder")) == 1
    assert len(kg.query(predicate="reviews")) == 1
    # Feature is touched by both edges (incoming)
    assert len(kg.neighbors("Feature")) == 2
    assert len(kg.neighbors("Coder")) == 1
