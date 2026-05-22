import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
from emergency.scenario_configs import get_scenario


def evaluate_drill(actions: list, scenario_id: str) -> dict:
    config = get_scenario(scenario_id)

    completed = sum(1 for a in actions if a["status"] == "completed")
    detected = sum(1 for a in actions if a["status"] in ("completed", "detected"))
    total = len(actions)

    action_score = round(100 * completed / total, 2) if total > 0 else 0
    avg_confidence = round(np.mean([a["confidence"] for a in actions]), 2)

    sequence_correct = True
    for i in range(1, len(actions)):
        if actions[i]["frame_range"][0] < actions[i - 1]["frame_range"][0]:
            sequence_correct = False
            break
    process_score = 90.0 if sequence_correct else 60.0
    process_score = min(process_score + avg_confidence * 10, 100)

    core_steps = config["core_network_steps"]
    network_recovered = 0
    for cs in core_steps:
        tid = cs["trigger_action"]
        for a in actions:
            if a["id"] == tid and a["status"] == "completed":
                network_recovered += 1
    network_score = round(100 * network_recovered / len(core_steps), 2) if core_steps else 0

    synergy_score = round(min(100, avg_confidence * 100 + (20 if sequence_correct else 0)), 2)

    weights = {"earthquake": {"action": 0.25, "process": 0.20, "network": 0.35, "synergy": 0.20},
               "fire": {"action": 0.20, "process": 0.15, "network": 0.25, "synergy": 0.40}}
    w = weights.get(scenario_id, weights["earthquake"])

    total_score = round(
        w["action"] * action_score +
        w["process"] * process_score +
        w["network"] * network_score +
        w["synergy"] * synergy_score, 2
    )

    issues = []
    for a in actions:
        if a["status"] != "completed":
            issues.append(f"{a['name']}: 识别置信度 {a['confidence']:.0%}，需检查动作规范性")

    suggestions = []
    if action_score < 70:
        suggestions.append("建议重新训练动作规范，确保每个动作到位")
    if not sequence_correct:
        suggestions.append("动作执行顺序有误，建议按标准流程演练")
    if network_score < 50:
        suggestions.append("核心网业务未充分恢复，建议检查网络模块对接")

    core_network_status = []
    for cs in core_steps:
        tid = cs["trigger_action"]
        done = any(a["id"] == tid and a["status"] == "completed" for a in actions)
        core_network_status.append({"step": cs["step"], "status": "connected" if done else "disconnected"})

    return {
        "total_score": total_score,
        "action_score": action_score,
        "process_score": round(process_score, 2),
        "network_score": network_score,
        "synergy_score": synergy_score,
        "actions": actions,
        "core_network_status": core_network_status,
        "issues": issues,
        "suggestions": suggestions,
        "scenario_name": config["name"],
    }
