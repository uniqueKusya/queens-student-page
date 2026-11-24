"""
sorting.py - the algorithm part of the app (no GUI here).

Problem:   Shuttle Stop Crowd Ranking
Algorithm: Merge Sort (written by hand, no sorted() / list.sort())

Data type: a stop is a tuple (stop_name, crowd_count).
           The input is a list of such tuples.
Order:     biggest crowd first (descending).
"""

MAX_STOPS = 15          # keep the animation readable
MAX_COUNT = 1_000_000   # sanity limit for the crowd number
MAX_NAME_LEN = 40
DEFAULT_THRESHOLD = 30   # crowd size where an extra shuttle is needed


def parse_input(text):
    """
    Turn the text from the textbox into a list of (name, count).
    Each line must look like:  Stop name, 25
    Returns (stops, error). If the input is bad: stops is None and
    error is a message for the user. If it is good: error is "".
    """
    if text is None or text.strip() == "":
        return None, "The input is empty. Write one stop per line, e.g.  Main Gate, 42"

    stops = []
    seen_names = []

    for line_number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if line == "":
            continue  # ignore empty lines

        # Every line needs a comma between the name and the number
        if "," not in line:
            return None, f"Line {line_number}: missing a comma. Use  name, number"

        # Split at the LAST comma, so a name can contain commas
        name, count_text = line.rsplit(",", 1)
        name = name.strip()
        count_text = count_text.strip()

        if name == "":
            return None, f"Line {line_number}: the stop name is empty."
        if len(name) > MAX_NAME_LEN:
            return None, f"Line {line_number}: the name is longer than {MAX_NAME_LEN} characters."
        if name.lower() in seen_names:
            return None, f"Line {line_number}: the stop '{name}' appears twice."

        # The crowd must be a whole number >= 0 (digits only)
        if not (count_text.isascii() and count_text.isdigit()) or len(count_text) > 10:
            return None, (f"Line {line_number}: '{count_text}' is not a valid crowd number. "
                          "Use a whole number like 0, 15, 230.")
        count = int(count_text)
        if count > MAX_COUNT:
            return None, f"Line {line_number}: the crowd number is bigger than {MAX_COUNT}."

        seen_names.append(name.lower())
        stops.append((name, count))

    if len(stops) == 0:
        return None, "No stops found. Write one stop per line, e.g.  Main Gate, 42"
    if len(stops) > MAX_STOPS:
        return None, f"Too many stops ({len(stops)}). The maximum is {MAX_STOPS}."

    return stops, ""


def parse_threshold(value):
    """
    Check the threshold from the GUI (the crowd size where an extra shuttle is needed).
    Returns (threshold, error). If it is bad: threshold is None and error is a message.
    """
    # Empty box, text or True/False are not valid numbers
    if value is None or isinstance(value, bool) or not isinstance(value, (int, float)):
        return None, "Threshold: please enter a whole number."

    try:
        if value != int(value):  # 12.5 is not a whole number
            return None, "Threshold: please enter a whole number (no decimals)."
        threshold = int(value)
    except (ValueError, OverflowError):  # nan or infinity
        return None, "Threshold: please enter a normal whole number."

    if threshold < 1 or threshold > MAX_COUNT:
        return None, f"Threshold: the number must be between 1 and {MAX_COUNT}."
    return threshold, ""


def stops_needing_shuttle(sorted_stops, threshold):
    """
    Rule: a stop needs an extra shuttle when its crowd is at least the threshold.
    The input list is already sorted, so the result keeps the ranking order
    (busiest first). It can be empty: then no extra shuttle is needed.
    """
    needed = []
    for stop in sorted_stops:
        if stop[1] >= threshold:
            needed.append(stop)
    return needed


def merge_sort_with_steps(stops):
    """
    Sort the stops with Merge Sort (biggest crowd first).
    Also record every step so the GUI can replay it.

    Returns (sorted_list, steps, comparisons).
    Each step is a dict:
        "items": list of (name, count) in the order to show
        "roles": list of strings, one per item:
                 "idle"   = not involved right now
                 "left"   = waiting in the left half
                 "right"  = waiting in the right half
                 "sorted" = already placed in the merged result
                 "done"   = final answer
        "text":  sentence that explains the step
    """
    arr = list(stops)        # work on a copy, the input stays unchanged
    steps = []
    counter = {"comparisons": 0}

    def add_step(items, roles, text):
        steps.append({"items": list(items), "roles": list(roles), "text": text})

    def merge(lo, mid, hi):
        """Merge the sorted parts arr[lo:mid] and arr[mid:hi]."""
        left = arr[lo:mid]
        right = arr[mid:hi]
        merged = []
        i = 0  # next unused item in left
        j = 0  # next unused item in right

        # Take the bigger front item each time until one side is empty
        while i < len(left) and j < len(right):
            counter["comparisons"] += 1
            a = left[i]
            b = right[j]
            if a[1] >= b[1]:   # ">=" keeps equal items in original order (stable)
                merged.append(a)
                i += 1
                if a[1] == b[1]:
                    text = (f"Compare {a[0]} ({a[1]}) and {b[0]} ({b[1]}): equal, "
                            f"so the left one ({a[0]}) goes first.")
                else:
                    text = (f"Compare {a[0]} ({a[1]}) and {b[0]} ({b[1]}): "
                            f"{a[0]} is busier, so it goes first.")
            else:
                merged.append(b)
                j += 1
                text = (f"Compare {a[0]} ({a[1]}) and {b[0]} ({b[1]}): "
                        f"{b[0]} is busier, so it goes first.")

            # Show: untouched start + merged so far + what is left of each half + untouched end
            shown = arr[:lo] + merged + left[i:] + right[j:] + arr[hi:]
            roles = (["idle"] * lo + ["sorted"] * len(merged) +
                     ["left"] * (len(left) - i) + ["right"] * (len(right) - j) +
                     ["idle"] * (len(arr) - hi))
            add_step(shown, roles, text)

        # One side is empty: the rest of the other side is already in order
        merged = merged + left[i:] + right[j:]
        arr[lo:hi] = merged

        roles = ["idle"] * lo + ["sorted"] * (hi - lo) + ["idle"] * (len(arr) - hi)
        add_step(arr, roles,
                 f"Merged positions {lo + 1} to {hi}. The rest of the leftover half is copied as it is.")

    def sort_range(lo, hi):
        """Sort arr[lo:hi] (hi is NOT included)."""
        if hi - lo <= 1:      # base case: 0 or 1 item is already sorted
            return
        mid = (lo + hi) // 2

        roles = (["idle"] * lo + ["left"] * (mid - lo) +
                 ["right"] * (hi - mid) + ["idle"] * (len(arr) - hi))
        add_step(arr, roles, f"Split positions {lo + 1} to {hi} into two halves.")

        sort_range(lo, mid)   # sort left half
        sort_range(mid, hi)   # sort right half
        merge(lo, mid, hi)    # combine them

    add_step(arr, ["idle"] * len(arr), "Start: this is the original order.")
    sort_range(0, len(arr))
    add_step(arr, ["done"] * len(arr),
             f"Done! Sorted with {counter['comparisons']} comparisons.")

    return arr, steps, counter["comparisons"]
