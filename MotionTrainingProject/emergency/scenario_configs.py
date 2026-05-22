SCENARIOS = {
    "earthquake": {
        "name": "山区地震通信抢修",
        "terrain": "山地 + 道路阻断区",
        "network_status": "基站断电、用户注册失败、视频无法回传",
        "objective": "部署临时通信基站，恢复指挥中心视频通信",
        "priority": "通信恢复时间优先",
        "actions": [
            {"id": 1, "name": "拿起通信设备箱", "key_joints": ["RightForeArm", "LeftForeArm", "Hips"],
             "detect": "torso_forward>30 AND hands_y_rising"},
            {"id": 2, "name": "行走到部署区域", "key_joints": ["RightLeg", "LeftLeg"],
             "detect": "gait_cycle"},
            {"id": 3, "name": "放置设备", "key_joints": ["RightKnee", "LeftKnee", "RightForeArm"],
             "detect": "knee_bend>90 AND hands_y_dropping"},
            {"id": 4, "name": "连接线缆", "key_joints": ["RightHand", "LeftHand"],
             "detect": "hands_small_range<150mm"},
            {"id": 5, "name": "调整天线方向", "key_joints": ["RightShoulder", "LeftShoulder"],
             "detect": "arm_above_shoulder AND rotation"},
            {"id": 6, "name": "下蹲检查设备", "key_joints": ["RightKnee", "LeftKnee"],
             "detect": "knee_bend>120"},
            {"id": 7, "name": "手持终端汇报", "key_joints": ["RightHand", "Head"],
             "detect": "hand_at_head_level"},
            {"id": 8, "name": "确认手势", "key_joints": ["RightArm"],
             "detect": "arm_raised_above_head"},
        ],
        "core_network_steps": [
            {"step": "终端接入", "trigger_action": 1},
            {"step": "用户注册", "trigger_action": 3},
            {"step": "会话建立", "trigger_action": 4},
            {"step": "视频回传", "trigger_action": 7},
        ],
    },
    "fire": {
        "name": "城市火灾应急通信保障",
        "terrain": "楼宇密集区",
        "network_status": "网络拥塞、视频高时延",
        "objective": "建立消防临时通信链路",
        "priority": "协同效率优先",
        "actions": [
            {"id": 1, "name": "搬运中继设备", "key_joints": ["RightForeArm", "LeftForeArm", "Hips"],
             "detect": "torso_forward>30 AND hands_y_rising"},
            {"id": 2, "name": "行走到楼宇指定点", "key_joints": ["RightLeg", "LeftLeg"],
             "detect": "gait_cycle"},
            {"id": 3, "name": "安装设备", "key_joints": ["RightHand", "LeftHand"],
             "detect": "hands_at_waist AND small_movement"},
            {"id": 4, "name": "线缆连接", "key_joints": ["RightHand", "LeftHand"],
             "detect": "hands_small_range<150mm"},
            {"id": 5, "name": "查看设备屏幕", "key_joints": ["Head"],
             "detect": "head_tilt_down>15"},
            {"id": 6, "name": "对讲机汇报", "key_joints": ["RightHand"],
             "detect": "hand_at_mouth_level"},
            {"id": 7, "name": "调整设备角度", "key_joints": ["RightShoulder", "LeftShoulder"],
             "detect": "arm_rotation"},
            {"id": 8, "name": "视频传输确认", "key_joints": ["RightArm", "Head"],
             "detect": "arm_raised AND head_nod"},
        ],
        "core_network_steps": [
            {"step": "终端接入", "trigger_action": 1},
            {"step": "用户注册", "trigger_action": 3},
            {"step": "会话建立", "trigger_action": 4},
            {"step": "视频回传", "trigger_action": 8},
        ],
    },
}


def get_scenario(scenario_id: str) -> dict:
    if scenario_id not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_id}. Available: {list(SCENARIOS.keys())}")
    return SCENARIOS[scenario_id]
