from typing import Any, Dict
from roma_agents.ingestor import IngestorAgent
from roma_agents.metrics import MetricsAgent
from roma_agents.coach import CoachAgent
from roma_agents.reporter import ReporterAgent

class HealthPlanner:
    """Break the top-level task into dependent subtasks."""
    def plan(self, root_payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "ingest": {"depends_on": [], "payload": root_payload},
            "metrics": {"depends_on": ["ingest"]},
            "coach": {"depends_on": ["ingest", "metrics"]},
            "report": {"depends_on": ["metrics", "coach"]},
        }

class HealthRunner:
    """A minimal ROMA-style runner using agent.run()—aligned with the README API."""
    def __init__(self):
        self.agents = {
            "ingest": IngestorAgent(),
            "metrics": MetricsAgent(),
            "coach": CoachAgent(),
            "report": ReporterAgent(),
        }
        self.planner = HealthPlanner()

    def run(self, root_payload: Dict[str, Any]) -> Dict[str, Any]:
        plan = self.planner.plan(root_payload)
        results: Dict[str, Dict[str, Any]] = {}
        pending = set(plan.keys())

        # dependency-aware execution (recursion flattened)
        while pending:
            progressed = False
            for name in list(pending):
                deps = plan[name]["depends_on"]
                if all(d in results for d in deps):
                    # hydrate payload from deps
                    payload = plan[name].get("payload", {})
                    if name == "metrics":
                        payload = {
                            "normalized_profile": results["ingest"]["normalized_profile"],
                            "normalized_logs": results["ingest"]["normalized_logs"],
                            "normalized_targets": results["ingest"]["normalized_targets"],
                        }
                    elif name == "coach":
                        payload = {
                            "normalized_logs": results["ingest"]["normalized_logs"],
                            "normalized_targets": results["ingest"]["normalized_targets"],
                            "metrics": results["metrics"]["metrics"],
                        }
                    elif name == "report":
                        payload = {
                            "metrics": results["metrics"]["metrics"],
                            "weekly_focus": results["coach"]["weekly_focus"],
                        }
                    # execute
                    out = self.agents[name].run(payload)
                    results[name] = out
                    pending.remove(name)
                    progressed = True
            if not progressed:
                raise RuntimeError("Dependency deadlock in plan")

        # aggregate to final
        if results["ingest"]["status"] != "ok":
            return {
                "status": "needs_input",
                "missing_fields": results["ingest"]["missing_fields"],
                "week_summary": {},
                "daily_suggestions": [],
                "weekly_plan": {},
                "next_actions": []
            }
        return {
            "status": "ok",
            "missing_fields": [],
            "week_summary": results["report"]["week_summary"],
            "daily_suggestions": results["coach"]["daily_suggestions"],
            "weekly_plan": results["report"]["weekly_plan"],
            "next_actions": results["report"]["next_actions"]
        }
