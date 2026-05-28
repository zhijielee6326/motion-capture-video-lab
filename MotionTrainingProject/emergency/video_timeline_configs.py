import os

_VIDEO_BASE = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "data", "数据", "案例4"
))

VIDEO_TIMELINES = {
    "earthquake": {
        "name": "山区地震通信抢修",
        "video_file": os.path.join(_VIDEO_BASE, "我的项目 - 虚幻编辑器 2026-05-26 19-33-38.mp4"),
        "motive_video_file": os.path.join(_VIDEO_BASE, "案例4数字人", "Motive_Body 3.2.0.2 Final 2026-05-26 19-33-49.mp4"),
        "description": "UE5地震场景 — 完整抢修演练过程",
        "timeline_nodes": [
            {"time": 5.0,  "action_id": 1, "name": "拿起通信设备箱",   "network_step": None},
            {"time": 15.0, "action_id": 2, "name": "行走到部署区域",   "network_step": None},
            {"time": 25.0, "action_id": 3, "name": "放置设备",         "network_step": "终端接入"},
            {"time": 35.0, "action_id": 4, "name": "连接线缆",         "network_step": "用户注册"},
            {"time": 45.0, "action_id": 5, "name": "调整天线方向",     "network_step": "会话建立"},
            {"time": 55.0, "action_id": 6, "name": "下蹲检查设备",     "network_step": None},
            {"time": 65.0, "action_id": 7, "name": "手持终端汇报",     "network_step": "视频回传"},
            {"time": 75.0, "action_id": 8, "name": "确认手势",         "network_step": None},
        ],
        "score_weights": {"action": 0.25, "process": 0.20, "network": 0.35, "synergy": 0.20},
    },
    "fire": {
        "name": "城市火灾应急通信保障",
        "video_file": os.path.join(_VIDEO_BASE, "我的项目 - 虚幻编辑器 2026-05-26 19-48-13.mp4"),
        "motive_video_file": os.path.join(_VIDEO_BASE, "案例4数字人", "Motive_Body 3.2.0.2 Final 2026-05-26 19-49-10.mp4"),
        "description": "UE5火灾场景 — 完整应急通信演练",
        "timeline_nodes": [
            {"time": 4.0,  "action_id": 1, "name": "搬运中继设备",     "network_step": "终端接入"},
            {"time": 12.0, "action_id": 2, "name": "行走到楼宇指定点", "network_step": None},
            {"time": 20.0, "action_id": 3, "name": "安装设备",         "network_step": "用户注册"},
            {"time": 28.0, "action_id": 4, "name": "线缆连接",         "network_step": "会话建立"},
            {"time": 36.0, "action_id": 5, "name": "查看设备屏幕",     "network_step": None},
            {"time": 44.0, "action_id": 6, "name": "对讲机汇报",       "network_step": None},
            {"time": 52.0, "action_id": 7, "name": "调整设备角度",     "network_step": None},
            {"time": 60.0, "action_id": 8, "name": "视频传输确认",     "network_step": "视频回传"},
        ],
        "score_weights": {"action": 0.20, "process": 0.15, "network": 0.25, "synergy": 0.40},
    },
}


def get_video_timeline(scenario_id: str) -> dict:
    if scenario_id not in VIDEO_TIMELINES:
        raise ValueError(f"Unknown scenario: {scenario_id}. Available: {list(VIDEO_TIMELINES.keys())}")
    config = VIDEO_TIMELINES[scenario_id]
    for key in ("video_file", "motive_video_file"):
        path = config.get(key)
        config[key + "_exists"] = bool(path and os.path.exists(path))
    return config
