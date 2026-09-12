from __future__ import annotations

from dataclasses import dataclass
import os
import re

from .provider import ReasoningRequest, ReasoningResponse


@dataclass(frozen=True)
class LocalPlanRule:
    name: str
    keywords: tuple[str, ...]
    command: tuple[str, ...]
    verification: tuple[str, ...]
    criterion: str


class LocalReasoner:
    """Deterministic reasoning core implemented entirely with the Python standard library.

    It deliberately makes no network/API calls and never pretends to know facts it
    cannot derive from the mission and local workspace. More capable intelligence
    can be layered above this boundary without making it a dependency.
    """

    _RULES = (
        LocalPlanRule("python_tests", ("test", "tests", "pytest", "unittest"), ("python", "-m", "unittest", "discover", "-s", "tests", "-v"), ("python", "-m", "unittest", "discover", "-s", "tests"), "tests_pass"),
        LocalPlanRule("python_compile", ("compile", "syntax", "build"), ("python", "-m", "compileall", "-q", "src"), ("python", "-m", "compileall", "-q", "src"), "source_compiles"),
        LocalPlanRule(
            "inspect_workspace",
            ("inspect", "workspace", "repository", "repo", "files"),
            ("python", "-c", "import os; from pathlib import Path; root=os.path.abspath(os.getcwd()); files=[os.path.relpath(os.fspath(p), root) for p in Path(root).rglob('*') if p.is_file()]; print('\\n'.join(sorted(files)))"),
            ("python", "-c", "from pathlib import Path; print(Path('.').is_dir())"),
            "workspace_inspected",
        ),
    )

    def reason(self, request: ReasoningRequest) -> ReasoningResponse:
        objective = str(request.objective).strip()
        if not objective:
            return ReasoningResponse("Empty objective.", [], 0.0, ["objective"])

        text = objective.lower()
        actions: list[dict] = []
        matched: set[str] = set()
        for rule in self._RULES:
            if any(re.search(rf"\b{re.escape(keyword)}\b", text) for keyword in rule.keywords):
                matched.add(rule.name)
                actions.append({
                    "description": f"{rule.name}: execute the local deterministic step",
                    "criterion_ids": [rule.criterion],
                    "command": list(rule.command),
                    "verification_command": list(rule.verification),
                    "expected_progress": 0.35,
                    "success_probability": 0.95,
                    "cost": 0.1,
                    "risk": 0.05,
                    "reversible": True,
                })

        unknowns: list[str] = []
        if not matched:
            unknowns.append("specific executable strategy for this objective")
        if "workspace" not in request.context:
            unknowns.append("workspace context")

        confidence = 0.85 if actions and not unknowns else (0.55 if actions else 0.0)
        analysis = "Derived a bounded local plan from explicit mission keywords; no external intelligence was consulted."
        return ReasoningResponse(analysis, actions, confidence, unknowns)
