# UE5 双通道骨骼动画对比回放 — 操作指南

## 概述

本文档指导在 UE5 中实现**标准动作 vs 学生动作的双通道骨骼动画对比播放**，配合 AI 评分模块的关节级评分结果，以颜色编码（绿/黄/红）高亮偏差关节。

**最终效果：** 左侧播放标准动作（蓝色骨骼），右侧播放学生动作（偏差关节着色），底部显示评分面板。

**推荐方案：** OptiTrack LiveLink 实时流（方案 C）— 无需 FBX，Motive 直连 UE5。

**前置条件：**
- Unreal Engine 5.7（已安装）
- OptiTrack Motive（实验室已安装）
- Motive 导出的 CSV 数据文件（如 `basketball_001.csv`）
- Python 3.11+（motion-eval 模块）

> **已知问题：** Motive 导出的 FBX 仅含骨骼数据（无网格体），UE5 5.7 无法直接导入。请使用方案 C（LiveLink）或方案 D（Mixamo 角色 + 重定向）。

---

## 步骤 1：UE5 项目配置

### 1.1 打开项目

打开已有的空项目：
```
c:\Users\m1889\Documents\Unreal Projects\动捕案例\动捕案例.uproject
```

### 1.2 启用插件

菜单 → Edit → Plugins，搜索并启用以下插件：

| 插件 | 用途 |
|------|------|
| **Python Editor Script Plugin** | 在编辑器内运行 Python 脚本 |
| **Editor Scripting Utilities** | 蓝图中操作资产 |
| **JSONBlueprintUtilities** | 蓝图解析 JSON |
| **LiveLink**（可选） | 实时动捕数据流，demo 用 FBX 模式不需要 |

启用后重启编辑器。

### 1.3 项目设置

菜单 → Edit → Project Settings：

- **Engine → Skeletal Mesh**：
  - 默认骨架缩放保持 1.0（FZMotion FBX 通常已经是合理比例）
- **Engine → Animation Settings**：
  - 勾选 "Allow Anim Rotation Extraction"（如果动画方向不对）
- **Plugins → Python**：
  - 确认 "Developer Mode" 已开启
  - 确认 Python 路径包含项目的 `Content/Python` 目录

### 1.4 创建内容目录

在 Content Browser 中右键创建以下文件夹：

```
Content/
  Animations/        ← 动画序列
  Characters/        ← 骨架网格体
  Materials/         ← 材质
  Blueprints/        ← 蓝图
  Widgets/           ← UI 控件
  Data/              ← JSON 数据
  Python/            ← Python 脚本
```

---

## 步骤 2：FBX 动画拆分与导入

### 方案 A：用 Python 脚本拆分 FBX（推荐）

**安装依赖：**
```bash
pip install fbx
```
> 如果 `pip install fbx` 找不到包，从 https://pypi.org/project/fbx/ 下载对应 Python 版本的 wheel。

**运行拆分：**
```bash
cd motion-eval/
python split_fbx.py basketball_001.fbx --split 0.5
```

生成两个文件：
- `basketball_001_std.fbx` — 标准动作（前半段）
- `basketball_001_stu.fbx` — 学生动作（后半段）

### 方案 B：在 UE5 内截取动画序列

如果 FBX 拆分不方便，可以导入完整 FBX 后在 UE5 内裁剪：

1. 导入完整 FBX（见下方导入步骤）
2. 双击打开 Animation Sequence
3. 在底部时间轴选中前半段范围
4. 右键 → "Crop Animation" → "Crop Beginning" / "Crop End"
5. 复制一份原始动画再裁剪另一段

### 导入 FBX 到 UE5

1. 将 FBX 文件复制到 `Content/Animations/` 文件夹
2. 在 Content Browser 中右键 → Import to /Game/Animations/
3. 选择 FBX 文件，在导入对话框中设置：

| 设置项 | 值 | 说明 |
|--------|-----|------|
| Skeleton | Create New | 第一次导入创建新骨架 |
| Import As | Skeletal Mesh + Animation | 同时导入网格体和动画 |
| Animation Length | Exported Range | 使用 FBX 中的完整范围 |
| Default Animation Type | Animation Asset | 导出为 AnimSequence |
| Convert Scene | ✅ 勾选 | Y-up → Z-up 自动转换 |
| Forward Axis | Y | FZMotion 默认 Y 轴朝前 |
| Up Axis | Z | 转换后 Z 朝上 |
| Scale | 1.0 | 如果太大/太小改为 0.1 或 10 |
| Frame Rate | 120 | 匹配 FZMotion 采集帧率 |

4. 点击 Import
5. 第二个 FBX 导入时选择**使用已有骨架**（选择第一次导入生成的 Skeleton）

### 验证导入

1. 双击 Skeleton → 在 Skeleton Editor 中确认所有骨骼可见
2. 双击 Animation Sequence → 播放预览，确认动作正确
3. 检查角色朝向和大小是否合理

**常见问题：**
- 角色朝下/躺倒 → 调整导入时的 Forward Axis 和 Up Axis
- 角色太大/太小 → 重新导入调整 Scale（FZMotion 单位 mm，UE5 单位 cm，可能需要 0.1 缩放）
- 动画抖动 → 检查帧率是否匹配（120fps）

---

## 方案 C：OptiTrack LiveLink 实时流（推荐，实验室最快落地）

> 无需 FBX 导入，Motive 直连 UE5 实时传输骨骼数据。

### 前置条件

- 实验室电脑同时运行 Motive 和 UE5
- OptiTrack LiveLink 插件（UE5 内置或从 OptiTrack 官网下载）

### C.1 UE5 启用插件

1. 菜单 → Edit → Plugins
2. 搜索并启用：
   - **LiveLink**（内置插件）
   - **LiveLink OptiTrack**（如未内置，从 https://docs.optitrack.com/plugins/ 下载安装）
3. 重启 UE5

### C.2 Motive 端配置

1. 打开 Motive，加载标定好的项目
2. 菜单 → View → Settings → **Streaming**
3. 勾选 **Broadcast Bone Data**
4. 设置：
   - Interface: **Local** (127.0.0.1) 或实验室局域网 IP
   - Port: **1511**（默认）
   - Rigid Bodies: ✅
   - Skeletons: ✅
5. 点击 **Start Streaming**

### C.3 UE5 端连接 LiveLink

1. 菜单 → Window → **Live Link**
2. 点击 **+ Source** → 选择 **OptiTrack Stream**
3. 确认 Connection Settings：
   - Server IP: 127.0.0.1（本机）或 Motive 的 IP
   - Port: 1511
4. 如果连接正常，Live Link 面板中会出现 Motive 发送的骨骼 Subject

### C.4 使用 UE5 内置角色接收动捕

1. 在场景中放置 UE5 第三人称模板角色 **Manny**（或 Quinn）：
   - Add → Skeletal Mesh → 选择 `SKM_Manny`
2. 选中 Manny 的 SkeletalMeshComponent
3. 在 Details 面板搜索 **Live Link**
4. 启用 **Live Link**：
   - Subject Name: 选择 Motive 发送的骨骼名
   - Role: **Animation**
5. 此时角色会实时跟随 Motive 中的动捕数据

### C.5 录制动画序列（离线回放用）

1. 菜单 → Window → **Take Recorder**
2. 点击 **+ Source** → **Live Link Subject** → 选择骨骼
3. 点击红色录制按钮开始录制
4. 在 Motive 中回放动画（或让演员重新表演）
5. 停止录制 → 自动生成 Level Sequence + AnimSequence

### C.6 双通道对比

1. 录制两段动画（标准 + 学生）
2. 场景中放置两个 Manny 角色，左右并排
3. 分别指定不同的 AnimSequence
4. 用 Sequencer 同步播放

### 参考资源

- [OptiTrack LiveLink 官方文档](https://docs.optitrack.com/plugins/optitrack-unreal-engine-plugin/unreal-engine-optitrack-live-link-plugin)
- [UE 5.6 Performance Capture 新功能](https://www.youtube.com/watch?v=nuoYdcF3hSQ)

---

## 方案 D：Mixamo 角色 + CSV 重定向（离线备选）

> 适用于无法使用 LiveLink 的情况。用免费 Mixamo 角色替代 Motive FBX。

### D.1 下载 Mixamo 角色

1. 访问 [Mixamo.com](https://www.mixamo.com)（Adobe 免费账号）
2. 选择一个角色（如 "Warrior" 或 "X Bot"）
3. 下载格式：**FBX for Unity (.fbx)**，选择 **With Skin**

### D.2 导入 UE5

1. 将 FBX 拖入 Content Browser
2. 导入设置选择：
   - Skeleton: **Create New**
   - Import As: **Skeletal Mesh**
3. 导入成功后会自动生成 Skeleton + Skeletal Mesh

### D.3 用 Python 脚本生成动画

在 UE5 编辑器的 Python 控制台中运行脚本，从 CSV 读取坐标，生成 AnimSequence：

```python
import unreal
import json, csv, os

def csv_to_anim_sequence(csv_path, skeleton_asset, anim_name, fps=30):
    """从 Motive CSV 创建 UE5 AnimSequence"""
    # 读取 CSV 坐标数据
    # 创建 AnimSequence
    # 逐帧设置骨骼 Transform
    # 保存资产
    pass
```

> 注意：此脚本需要根据实际骨骼层级和命名映射编写，复杂度较高。建议优先使用 LiveLink 方案。

### D.4 IK Retargeting（如果 Mixamo 骨骼和 Manny 不兼容）

1. 菜单 → Window → **IK Retargeter**
2. Source: Mixamo Skeleton
3. Target: Manny Skeleton
4. 手动映射骨骼链
5. 导出 Retargeted AnimSequence

---

## 步骤 3：场景搭建

### 3.1 创建新关卡

菜单 → File → New Level → Empty Level，保存为 `DM_DualPlayback`。

### 3.2 放置角色

1. 从 Content Browser 拖入标准动作的 Skeletal Mesh → 放置在 **X=-300, Y=0, Z=0**
2. 拖入学生动作的 Skeletal Mesh → 放置在 **X=300, Y=0, Z=0**
3. 给两个 Actor 命名为 `BP_Standard` 和 `BP_Student`

### 3.3 添加标签

给每个角色上方添加 Text Render：
- 菜单 → Add → Text Render
- 标准角色上方：文本 "标准动作"，颜色蓝色
- 学生角色上方：文本 "学生动作"，颜色白色
- 位置在角色头部上方约 100 单位

### 3.4 摄像机

1. 添加 Camera Actor，位置 **X=0, Y=-800, Z=100**
2. 朝向 (0, 0, 50)（正对两个角色中间）
3. 在 Details 面板设置 FOV=60

### 3.5 灯光

1. **Directional Light**：位置随意，旋转使光线从前方偏上照射，Intensity=3.0
2. **Sky Light**：Intensity=1.0，提供环境光
3. 可选：两个角色各加一个 **Rect Light**（Intensity=2.0），增强关节可见度

### 3.6 地板

1. 添加 Floor（Basic Shapes → Plane），缩放 5x5
2. 材质设为深灰色网格（M_Grid 或自定义简单材质）

---

## 步骤 4：骨骼关节可视化

### 4.1 创建关节球体材质

在 Content/Materials/ 中创建 3 个 Material：

**M_JointGreen（关节正常）**
- Shading Model: Unlit
- Emissive Color: (0.0, 0.8, 0.2) — 绿色
- 适当调高 Emissive Intensity = 2.0

**M_JointYellow（关节注意）**
- Emissive Color: (1.0, 0.7, 0.0) — 黄色
- Emissive Intensity = 2.0

**M_JointRed（关节偏差大）**
- Emissive Color: (1.0, 0.1, 0.0) — 红色
- Emissive Intensity = 2.0

**M_JointDefault（标准动作用）**
- Emissive Color: (0.3, 0.5, 1.0) — 蓝色
- Emissive Intensity = 2.0

各创建对应的 Material Instance（MI_Green, MI_Yellow, MI_Red, MI_Default），方便动态切换。

### 4.2 创建 BP_SkeletonViz 蓝图

在 Content/Blueprints/ 中新建 Blueprint Class → Actor，命名为 `BP_SkeletonViz`。

**组件结构：**
```
BP_SkeletonViz (Actor)
  ├── SkeletalMesh (Skeletal Mesh Component)  ← 播放动画
  │     └── 17x StaticMesh (Sphere)           ← 关节球体
  └── 16x SplineMesh                          ← 骨骼连接线
```

**关节球体设置（17 个）：**

为每个评分关节创建一个 Sphere Static Mesh Component，设置：

| 球体名称 | 附加骨骼 (Attach to Socket) | 球体半径 |
|---------|--------------------------|---------|
| Sphere_Ab | Ab | 5 |
| Sphere_Chest | Chest | 5 |
| Sphere_Neck | Neck | 4 |
| Sphere_Head | Head | 6 |
| Sphere_LShoulder | LShoulder | 5 |
| Sphere_LUArm | LUArm | 4 |
| Sphere_LFArm | LFArm | 4 |
| Sphere_LHand | LHand | 3 |
| Sphere_RShoulder | RShoulder | 5 |
| Sphere_RUArm | RUArm | 4 |
| Sphere_RFArm | RFArm | 4 |
| Sphere_RHand | RHand | 3 |
| Sphere_LThigh | LThigh | 5 |
| Sphere_LShin | LShin | 4 |
| Sphere_LFoot | LFoot | 4 |
| Sphere_RThigh | RThigh | 5 |
| Sphere_RShin | RShin | 4 |
| Sphere_RFoot | RFoot | 4 |

每个球体附加到对应的骨骼 Socket 上（在 Details → Socket 中选择骨骼名）。

**骨骼连接线（可选但推荐）：**

用 Spline Mesh 或 Cable Component 连接相邻关节，形成火柴人效果：
- Head → Neck → Chest → Ab
- Chest → LShoulder → LUArm → LFArm → LHand
- Chest → RShoulder → RUArm → RFArm → RHand
- Ab → LThigh → LShin → LFoot
- Ab → RThigh → RShin → RFoot

**蓝图函数：UpdateJointColor**

```
函数: UpdateJointColor(JointName: String, Color: String)
  → 根据 JointName 找到对应球体组件
  → 根据 Color 设置材质:
    "green"  → MI_Green
    "yellow" → MI_Yellow
    "red"    → MI_Red
    "default"→ MI_Default
```

**蓝图函数：UpdateAllJoints**

```
函数: UpdateAllJoints(ScoreData: JsonObject)
  → 遍历 ScoreData["joint_colors"] 数组
  → 对每个关节调用 UpdateJointColor(bone, color)
```

### 4.3 关节名映射

FZMotion 骨骼名在 FBX 中可能带前缀（如 `Skeleton_002:RUArm`）。导入后检查实际的骨骼名，创建映射：

| 评分角度名 | FZMotion 骨骼（顶点） | UE5 骨骼名（需确认） |
|-----------|---------------------|-------------------|
| right_elbow | RUArm | RUArm 或 Skeleton_002:RUArm |
| left_elbow | LUArm | LUArm 或 Skeleton_002:LUArm |
| right_shoulder | RShoulder | RShoulder |
| left_shoulder | LShoulder | LShoulder |
| right_hip | RThigh | RThigh |
| left_hip | LThigh | LThigh |
| right_knee | RShin | RShin |
| left_knee | LShin | LShin |

> **注意：** 导入 FBX 后在 Skeleton Editor 中查看实际骨骼名，更新此表。

---

## 步骤 5：评分数据对接

### 5.1 运行评分导出

```bash
cd motion-eval/

# 方式1：同一 CSV 拆分（前半段=标准，后半段=学生）
python export_score_json.py basketball_001.csv --output ue5_score.json

# 方式2：两个独立 CSV
python export_score_json.py student.csv --std-csv standard.csv --output ue5_score.json

# 导出到 UE5 Content 目录
python export_score_json.py basketball_001.csv --output "C:/Users/m1889/Documents/Unreal Projects/动捕案例/Content/Data/ue5_score.json"
```

### 5.2 JSON 格式说明

导出的 `ue5_score.json` 结构：

```json
{
  "final_score": 72.5,
  "max_score": 100,
  "teacher_score": 29,
  "compare_score": 43.5,
  "student_info": {
    "name": "basketball_001_学生",
    "fps": 120,
    "frame_count": 2017,
    "duration": 16.8
  },
  "dimensions": [
    {
      "name": "准备姿势与重心",
      "score": 8,
      "max_score": 16,
      "group": "absolute",
      "pct": 50.0,
      "color": "yellow",
      "joints": [...]
    },
    {
      "name": "ROM（活动幅度对比）",
      "score": 93.5,
      "max_score": 100,
      "group": "compare",
      "pct": 93.5,
      "color": "green",
      "joints": [
        {"joint": "right_elbow", "score": 95.2, "detail": {"std_rom": 85, "stu_rom": 80}},
        {"joint": "left_knee", "score": 58.4, "detail": {"rmse": 20.8}}
      ]
    }
  ],
  "joint_colors": [
    {"bone": "RUArm", "label": "右肘", "score": 95.2, "color": "green", "detail": {...}},
    {"bone": "LShin", "label": "左膝", "score": 58.4, "color": "yellow", "detail": {...}}
  ],
  "suggestions": [
    "准备姿势不够标准：降低重心，屈膝至约120°，身体稍前倾"
  ]
}
```

**关键字段：**
- `joint_colors`：UE5 蓝图直接使用的关节着色数据
- 每个 `joint_colors` 条目的 `color` 值为 `"green"` / `"yellow"` / `"red"`
- `bone` 字段对应 FZMotion 骨骼名，需映射到 UE5 骨骼名

### 5.3 UE5 中读取 JSON

**蓝图方案：**

1. 将 `ue5_score.json` 放入 `Content/Data/`
2. 在 Blueprint 中使用 JSON Blueprint Utilities 插件：
   ```
   Event BeginPlay
     → Load Json from File ("/Game/Data/ue5_score.json")
     → Get Object Field ("joint_colors")
     → Get Array Field
     → For Each Loop:
         → Get String Field ("bone") → 关节名
         → Get String Field ("color") → 颜色
         → BP_Student→UpdateJointColor(bone, color)
   ```

**Python 脚本方案（更灵活）：**

在 `Content/Python/` 创建 `load_score.py`：

```python
import unreal
import json

def load_and_apply():
    json_path = unreal.Paths.project_content_dir() + "Data/ue5_score.json"
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 设置蓝图变量
    editor_sys = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = editor_sys.get_all_level_actors()

    score_widget = None
    student_bp = None
    for a in actors:
        if "Student" in a.get_name():
            student_bp = a
        if "ScoreWidget" in a.get_name():
            score_widget = a

    # 应用关节颜色
    if student_bp:
        for jc in data.get("joint_colors", []):
            student_bp.update_joint_color(jc["bone"], jc["color"])

    unreal.log(f"评分加载完成: {data['final_score']}/{data['max_score']}")

# 在 UE5 Python 控制台运行: load_and_apply()
```

---

## 步骤 6：同步播放逻辑

### 6.1 创建 BP_DualPlayback 蓝图

在 Content/Blueprints/ 创建 Actor Blueprint `BP_DualPlayback`。

**变量：**
```
StandardMesh: SkeletalMeshComponent Reference
StudentMesh: SkeletalMeshComponent Reference
StandardAnim: AnimSequence Reference
StudentAnim: AnimSequence Reference
IsPlaying: Boolean = false
PlayRate: Float = 1.0
CurrentTime: Float = 0.0
AnimationDuration: Float = 0.0
TimelineRef: Timeline Reference
```

**Event Graph：**

```
Event BeginPlay
  → 获取 Standard 和 Student 的 SkeletalMeshComponent
  → 设置 AnimationDuration = StandardAnim->GetTotalDuration()
  → 调用 StartPlayback()

自定义事件: StartPlayback
  → Set IsPlaying = true
  → StandardMesh->PlayAnimation(StandardAnim, false)
  → StudentMesh->PlayAnimation(StudentAnim, false)
  → 两者都从 time=0 开始

Event Tick
  → Branch: IsPlaying?
    → True:
      → CurrentTime += DeltaSeconds * PlayRate
      → Branch: CurrentTime > AnimationDuration?
        → True: StopPlayback()
        → False: 继续

自定义事件: StopPlayback
  → Set IsPlaying = false

自定义事件: SetPlayRate(Rate: Float)
  → PlayRate = Rate
  → StandardMesh->SetPlayRate(Rate)
  → StudentMesh->SetPlayRate(Rate)

自定义事件: ScrubToTime(Time: Float)
  → StandardMesh->SetPosition(Time)
  → StudentMesh->SetPosition(Time)
  → CurrentTime = Time
```

### 6.2 同步保证

关键点：**两个动画必须从同一帧开始、以相同速率播放**。

- 使用同一个 Timeline 驱动两边的 `SetPosition`
- 或者在 Tick 中同步更新两边的时间位置
- 确保 PlayRate 始终一致

---

## 步骤 7：UI 面板

### 7.1 创建 WBP_ScorePanel

在 Content/Widgets/ 创建 Widget Blueprint `WBP_ScorePanel`。

**布局（Canvas Panel）：**

```
┌─────────────────────────────────────────────┐
│  [总分]     标准动作 vs 学生动作             │
│            72.5 / 100                        │
├─────────────────────────────────────────────┤
│  A. 老师规则评分  29/40  ██████░░░░ 72%     │
│    准备姿势  8/16                            │
│    视线方向  5/5                             │
│    ...                                      │
│  B. 四维对比评分  43.5/60                    │
│    ROM   93.5/100                           │
│    DTW   99.0/100                           │
│    ...                                      │
├─────────────────────────────────────────────┤
│  建议:                                       │
│  1. 准备姿势不够标准...                      │
│  2. ...                                     │
├─────────────────────────────────────────────┤
│  [◀◀] [▶ 播放] [▶▶]  速度 [1.0x ▼]        │
│  进度 ████████░░░░░░░░  12.5s / 16.8s      │
└─────────────────────────────────────────────┘
```

**UMG 组件：**
- `Text_FinalScore`：总分显示
- `ProgressBar_Teacher`：老师规则评分进度条
- `ProgressBar_Compare`：四维对比评分进度条
- `VerticalBox_Dimensions`：维度分数列表
- `VerticalBox_Suggestions`：建议列表
- `Button_PlayPause`：播放/暂停按钮
- `Slider_Speed`：速度滑块（0.1-2.0）
- `Slider_Progress`：帧进度滑块

### 7.2 在关卡中添加 Widget

1. 在 Player Controller 蓝图中：
   ```
   Event BeginPlay
     → Create Widget (WBP_ScorePanel)
     → Add to Viewport
   ```
2. 设置 Widget 的 ZOrder = 10，确保在 3D 场景之上

---

## 步骤 8：整合与测试

### 8.1 完整工作流程

```
1. FZMotion 采集 → 导出 CSV + FBX
2. Python 评分: python export_score_json.py basketball_001.csv
3. FBX 拆分: python split_fbx.py basketball_001.fbx
4. UE5 导入两个 FBX
5. UE5 放置双角色 + 配置蓝图
6. 复制 ue5_score.json 到 Content/Data/
7. 运行 UE5 → 加载评分 → 播放对比
```

### 8.2 验证清单

- [ ] FBX 导入后骨骼网格体在预览场景中动作正确
- [ ] 两个角色左右对称放置，标签清晰
- [ ] 点击播放后两段动画同步播放，无偏移
- [ ] 暂停/恢复/变速功能正常
- [ ] 关节球体颜色与 JSON 中的评分一致（绿=好，黄=注意，红=差）
- [ ] UI 面板显示的分数与 Web Dashboard 一致
- [ ] 摄像机视角能同时看到两个角色的完整动作

---

## 附录 A：辅助脚本说明

### split_fbx.py

拆分 FBX 动画文件为标准/学生两段。

```bash
# 用法
python split_fbx.py <input.fbx> [--split RATIO] [--output-dir DIR]

# 示例：按 50% 拆分
python split_fbx.py basketball_001.fbx

# 示例：按 60% 拆分（前 60% 为标准）
python split_fbx.py basketball_001.fbx --split 0.6
```

依赖：`pip install fbx`

### export_score_json.py

运行评分并导出 UE5 可读的 JSON。

```bash
# 用法
python export_score_json.py <student.csv> [--std-csv STANDARD.csv] [--output OUTPUT.json] [--split RATIO]

# 示例：同一 CSV 拆分
python export_score_json.py basketball_001.csv

# 示例：两个独立 CSV
python export_score_json.py student.csv --std-csv standard.csv

# 导出到 UE5 项目
python export_score_json.py basketball_001.csv --output "C:/.../Content/Data/ue5_score.json"
```

依赖：`pip install scipy fastdtw numpy`

## 附录 B：FZMotion 关节与 UE5 骨骼映射

**17 个评分关节（csv_loader.py SCORING_JOINTS）：**

```
Ab       → pelvis/hips
Chest    → spine_02
Neck     → neck_01
Head     → head
LShoulder → shoulder_l
LUArm    → upperarm_l
LFArm    → lowerarm_l
LHand    → hand_l
RShoulder → shoulder_r
RUArm    → upperarm_r
RFArm    → lowerarm_r
RHand    → hand_r
LThigh   → thigh_l
LShin    → calf_l
LFoot    → foot_l
RThigh   → thigh_r
RShin    → calf_r
RFoot    → foot_r
```

> **注意：** 实际映射取决于 FZMotion 导出 FBX 时的骨骼命名。导入后在 Skeleton Editor 中确认。

## 附录 C：颜色编码标准

| 颜色 | 条件 | 含义 |
|------|------|------|
| 🟢 绿色 | 得分率 ≥ 80% | 动作规范 |
| 🟡 黄色 | 50% ≤ 得分率 < 80% | 需要注意 |
| 🔴 红色 | 得分率 < 50% | 偏差较大 |
| 🔵 蓝色 | 标准动作默认色 | 参考动作 |
