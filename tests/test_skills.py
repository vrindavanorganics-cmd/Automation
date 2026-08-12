import pytest

from orbit.memory.store import MemoryStore
from orbit.permissions.engine import PermissionEngine
from orbit.skills.engine import SkillEngine
from orbit.skills.schema import Skill, SkillStep
from orbit.tools.files_tool import FilesTool
from orbit.tools.registry import ToolRegistry


@pytest.fixture
def engine(tmp_path):
    memory = MemoryStore(tmp_path / "orbit.db")
    registry = ToolRegistry()
    registry.register(FilesTool(base_dir=str(tmp_path)))
    permissions = PermissionEngine(confirm_callback=lambda r: True)
    e = SkillEngine(memory, registry, permissions)
    yield e, tmp_path
    memory.close()


def test_teach_mode_records_and_saves_skill(engine):
    skill_engine, tmp_path = engine
    skill_engine.start_teaching("buyer_outreach")
    assert skill_engine.is_teaching
    skill_engine.record_step("files", "create_folder", {"name": "Leads"}, description="Create leads folder")
    skill = skill_engine.finish_teaching(description="Prepares buyer leads folder")
    assert not skill_engine.is_teaching
    assert skill.name == "buyer_outreach"
    assert len(skill.steps) == 1

    loaded = skill_engine.get_skill("buyer_outreach")
    assert loaded is not None
    assert loaded.steps[0].tool == "files"


def test_find_skill_by_fuzzy_query(engine):
    skill_engine, _ = engine
    skill_engine.save_skill(Skill(name="Buyer Outreach", steps=[]))
    found = skill_engine.find_skill_by_query("run buyer outreach for these companies")
    assert found is not None
    assert found.name == "Buyer Outreach"


def test_run_skill_executes_steps_in_order(engine):
    skill_engine, tmp_path = engine
    skill = Skill(
        name="make_folder",
        steps=[SkillStep(tool="files", action="create_folder", params={"name": "Output"}, verification={"type": "file_exists"})],
    )
    result = skill_engine.run_skill(skill, {})
    assert result.success is True
    assert result.step_results[0].verified is True
    assert (tmp_path / "Output").is_dir()


def test_run_skill_with_loop_creates_multiple_folders(engine):
    skill_engine, tmp_path = engine
    skill = Skill(
        name="make_folders",
        variables=["names"],
        steps=[SkillStep(tool="files", action="create_folder", params={"name": "{item}"}, loop_over="names", loop_as="item")],
    )
    result = skill_engine.run_skill(skill, {"names": ["A", "B", "C"]})
    assert result.success is True
    assert len(result.step_results) == 3
    for name in ("A", "B", "C"):
        assert (tmp_path / name).is_dir()


def test_run_skill_condition_skips_step(engine):
    skill_engine, tmp_path = engine
    skill = Skill(
        name="conditional",
        steps=[SkillStep(tool="files", action="create_folder", params={"name": "ShouldSkip"}, condition="run_it")],
    )
    result = skill_engine.run_skill(skill, {"run_it": False})
    assert result.step_results[0].skipped is True
    assert not (tmp_path / "ShouldSkip").exists()


def test_run_skill_stops_on_permission_denied(engine):
    memory = MemoryStore(":memory:")
    registry = ToolRegistry()
    registry.register(FilesTool())
    denying_permissions = PermissionEngine(confirm_callback=lambda r: False)
    skill_engine = SkillEngine(memory, registry, denying_permissions)
    skill = Skill(
        name="sensitive",
        steps=[SkillStep(tool="files", action="create_folder", params={"name": "x"}, requires_approval=True)],
    )
    result = skill_engine.run_skill(skill, {})
    assert result.success is False
    memory.close()
