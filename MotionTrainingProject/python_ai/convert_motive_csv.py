"""Convert Motive-exported CSV to FZMotion-compatible format."""
import csv
import sys
import os


MOTIVE_TO_FZMOTION = {
    "Skeleton 002:Skeleton 002": "Hips",
    "Skeleton 002:Ab": "Spine",
    "Skeleton 002:Chest": "Spine1",
    "Skeleton 002:Neck": "Neck",
    "Skeleton 002:Head": "Head",
    "Skeleton 002:LShoulder": "LeftShoulder",
    "Skeleton 002:LUArm": "LeftArm",
    "Skeleton 002:LFArm": "LeftForeArm",
    "Skeleton 002:LHand": "LeftHand",
    "Skeleton 002:LThumb1": "LeftHandThumb",
    "Skeleton 002:LIndex1": "LeftHandIndex",
    "Skeleton 002:LMiddle1": "LeftHandMiddle",
    "Skeleton 002:LRing1": "LeftHandRing",
    "Skeleton 002:LPinky1": "LeftHandPinky",
    "Skeleton 002:RShoulder": "RightShoulder",
    "Skeleton 002:RUArm": "RightArm",
    "Skeleton 002:RFArm": "RightForeArm",
    "Skeleton 002:RHand": "RightHand",
    "Skeleton 002:RThumb1": "RightHandThumb",
    "Skeleton 002:RIndex1": "RightHandIndex",
    "Skeleton 002:RMiddle1": "RightHandMiddle",
    "Skeleton 002:RRing1": "RightHandRing",
    "Skeleton 002:RPinky1": "RightHandPinky",
    "Skeleton 002:LThigh": "LeftUpLeg",
    "Skeleton 002:LShin": "LeftLeg",
    "Skeleton 002:LFoot": "LeftFoot",
    "Skeleton 002:LToe": "LeftToeBase",
    "Skeleton 002:RThigh": "RightUpLeg",
    "Skeleton 002:RShin": "RightLeg",
    "Skeleton 002:RFoot": "RightFoot",
    "Skeleton 002:RToe": "RightToeBase",
}

FZMOTION_JOINT_ORDER = [
    "Head", "Neck", "Spine", "Spine1", "Spine2", "Spine3", "Hips",
    "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
    "LeftHandThumb", "LeftHandIndex", "LeftHandMiddle", "LeftHandRing", "LeftHandPinky",
    "RightShoulder", "RightArm", "RightForeArm", "RightHand",
    "RightHandThumb", "RightHandIndex", "RightHandMiddle", "RightHandRing", "RightHandPinky",
    "LeftUpLeg", "LeftLeg", "LeftFoot", "LeftToeBase",
    "RightUpLeg", "RightLeg", "RightFoot", "RightToeBase",
]


def convert_motive_csv(input_path: str, output_path: str):
    with open(input_path, "r", encoding="utf-8") as f:
        reader = list(csv.reader(f))

    # Row indices (0-based): 3=name, 6=coord_type
    name_row = reader[3]
    coord_row = reader[6]

    # Build column mapping: {fzmotion_joint: [col_x_idx, col_y_idx, col_z_idx]}
    col_map = {}
    i = 2  # skip first two columns (Frame, Time)
    while i < len(name_row):
        motive_name = name_row[i].strip() if i < len(name_row) else ""
        if motive_name in MOTIVE_TO_FZMOTION:
            fz_name = MOTIVE_TO_FZMOTION[motive_name]
            # Find the 3 Position columns in this bone's group
            pos_cols = []
            for j in range(i, min(i + 6, len(coord_row))):
                if j < len(coord_row) and coord_row[j].strip() == "Position":
                    pos_cols.append(j)
            if len(pos_cols) == 3:
                col_map[fz_name] = pos_cols
            i += 6
        elif motive_name and "Bone Marker" not in str(name_row[2:min(len(name_row), i+10)]):
            i += 1
        else:
            i += 1

    # Spine2, Spine3: duplicate from Chest (Spine1)
    if "Spine1" in col_map:
        col_map["Spine2"] = col_map["Spine1"]
        col_map["Spine3"] = col_map["Spine1"]

    # Find frame and time columns
    frame_col = 0
    time_col = 1

    # Data starts at row 8 (0-based)
    data_start = 8
    header = ["frame", "time"]
    for joint in FZMOTION_JOINT_ORDER:
        header.extend([f"{joint}_x", f"{joint}_y", f"{joint}_z"])

    rows_out = []
    for row_idx in range(data_start, len(reader)):
        row = reader[row_idx]
        if len(row) < 2 or not row[0].strip():
            continue

        frame = row[frame_col].strip()
        time_val = row[time_col].strip()

        out_row = [frame, time_val]
        for joint in FZMOTION_JOINT_ORDER:
            if joint in col_map:
                cols = col_map[joint]
                x = row[cols[0]].strip() if cols[0] < len(row) else ""
                y = row[cols[1]].strip() if cols[1] < len(row) else ""
                z = row[cols[2]].strip() if cols[2] < len(row) else ""
                out_row.extend([x, y, z])
            else:
                out_row.extend(["", "", ""])
        rows_out.append(out_row)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows_out)

    print(f"Converted: {len(rows_out)} frames, {len(col_map)} joints mapped")
    print(f"Output: {output_path}")
    return output_path


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_motive_csv.py <input.csv> [output.csv]")
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else inp.replace(".csv", "_converted.csv")
    convert_motive_csv(inp, out)
