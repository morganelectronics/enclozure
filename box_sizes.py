"""A list of nominal outer box sizes: (length_mm, width_mm, height_mm).

Feed into the generator, e.g.:

    from enclosure import Enclosure
    from box_sizes import SIZES
    L, W, H = SIZES[0]
    Enclosure(width=L, breadth=W, base_height=H - 10, lid_height=10).export_zip()
"""

SIZES = [
    (65.0, 60.0, 40.0),
    (85.0, 80.0, 55.0),
    (105.0, 75.0, 40.0),
    (105.0, 75.0, 55.0),
    (125.0, 85.0, 55.0),
    (165.0, 85.0, 55.0),
    (165.0, 85.0, 85.0),
    (145.0, 105.0, 40.0),
    (145.0, 105.0, 60.0),
    (165.0, 125.0, 75.0),
    (186.0, 146.0, 75.0),
    (186.0, 146.0, 110.0),
    (220.0, 165.0, 60.0),
    (220.0, 165.0, 85.0),
]


def sizes():
    """Return the list of (length, width, height) tuples."""
    return list(SIZES)


if __name__ == "__main__":
    print(f"{'length':>8} {'width':>8} {'height':>8}")
    for length, width, height in SIZES:
        print(f"{length:8.1f} {width:8.1f} {height:8.1f}")
