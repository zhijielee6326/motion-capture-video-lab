import math


def get_2d_dist(p1, p2) -> float:
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


def get_abc_degree(a, b, c) -> float:
    ab = (b[0] - a[0], b[1] - a[1])
    cb = (b[0] - c[0], b[1] - c[1])
    dot = ab[0] * cb[0] + ab[1] * cb[1]
    mag_ab = math.sqrt(ab[0] ** 2 + ab[1] ** 2)
    mag_cb = math.sqrt(cb[0] ** 2 + cb[1] ** 2)
    if mag_ab == 0 or mag_cb == 0:
        return 0.0
    cos_angle = max(-1, min(1, dot / (mag_ab * mag_cb)))
    return math.degrees(math.acos(cos_angle))
