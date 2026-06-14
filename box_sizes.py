"""A list of nominal outer box sizes: (length_mm, width_mm, height_mm).

Feed into the generator, e.g.:

    from enclosure import Enclosure
    from box_sizes import SIZES
    L, W, H = SIZES[0]
    Enclosure(width=L, breadth=W, base_height=H - 10, lid_height=10).export_zip()
"""

SIZES = [
    (119.4, 65.0, 40.6),
    (119.4, 65.0, 60.0),
    (119.4, 89.0, 40.6),
    (119.4, 89.0, 60.0),
    (119.4, 89.0, 80.0),
    (119.4, 119.4, 40.6),
    (119.4, 119.4, 60.0),
    (180.3, 119.4, 45.7),
    (180.3, 119.4, 63.5),
    (180.3, 119.4, 90.5),
    (160.0, 160.0, 90.5),
    (180.3, 180.3, 60.0),
    (180.3, 180.3, 90.5),
    (240.0, 160.0, 90.5),
]


def sizes():
    """Return the list of (length, width, height) tuples."""
    return list(SIZES)


if __name__ == "__main__":
    print(f"{'length':>8} {'width':>8} {'height':>8}")
    for length, width, height in SIZES:
        print(f"{length:8.1f} {width:8.1f} {height:8.1f}")
