"""
app.py - Gradio GUI for the Shuttle Stop Crowd Ranking (Merge Sort).
Run with:  python app.py
"""

import html
import itertools

# Hugging Face free tier runs Gradio Spaces on ZeroGPU.
# ZeroGPU needs at least one @spaces.GPU function to start.
# This one does nothing and is never called. The app itself runs on CPU.
try:
    import spaces

    @spaces.GPU
    def gpu_placeholder():
        return None
except ImportError:
    pass  # running locally: the "spaces" package is not needed

import gradio as gr
from sorting import (parse_input, parse_threshold, merge_sort_with_steps,
                     stops_needing_shuttle, DEFAULT_THRESHOLD)

EXAMPLE = """Main Gate, 42
Library, 15
Engineering Building, 63
Residence Hall A, 27
Student Centre, 63
Sports Complex, 8
Hospital, 31"""

# Colour for each role in the sorting animation
COLORS = {
    "idle": "#9ca3af",    # grey
    "left": "#3b82f6",    # blue
    "right": "#f59e0b",   # orange
    "sorted": "#22c55e",  # green
    "done": "#22c55e",    # green
}

LEGEND = (
    '<div style="margin:8px 0;font-size:14px">'
    '<span style="color:#3b82f6">&#9632;</span> left half &nbsp; '
    '<span style="color:#f59e0b">&#9632;</span> right half &nbsp; '
    '<span style="color:#22c55e">&#9632;</span> already merged / final &nbsp; '
    '<span style="color:#9ca3af">&#9632;</span> not involved'
    '</div>'
)

# Every bus animation gets a new name, so the browser restarts it on each run
animation_counter = itertools.count(1)


def draw_step(steps, index):
    """Make the HTML picture of one sorting step (bars = crowd size)."""
    if not steps:
        return ""
    index = max(0, min(index, len(steps) - 1))  # keep index inside the list
    step = steps[index]

    biggest = max(count for _, count in step["items"])
    rows = ""
    for position, (item, role) in enumerate(zip(step["items"], step["roles"]), start=1):
        name, count = item
        width = 100 * count / biggest if biggest > 0 else 0
        width = max(width, 1)  # tiny bar for 0 so the row is still visible
        rows += (
            '<div style="display:flex;align-items:center;gap:8px;margin:4px 0">'
            f'<div style="width:28px;text-align:right">{position}.</div>'
            f'<div style="width:170px;overflow:hidden;white-space:nowrap;text-overflow:ellipsis">'
            f'{html.escape(name)}</div>'
            '<div style="flex:1">'
            f'<div style="width:{width}%;height:22px;border-radius:4px;'
            f'background:{COLORS[role]}"></div></div>'
            f'<div style="width:70px;text-align:right">{count}</div>'
            '</div>'
        )

    header = (f'<div style="font-weight:bold;margin-bottom:4px">'
              f'Step {index + 1} of {len(steps)}</div>'
              f'<div style="margin-bottom:8px">{html.escape(step["text"])}</div>')
    return header + LEGEND + rows


def draw_bus(sorted_stops, threshold):
    """
    Make the HTML for the bus animation.
    The stops stand in a row (busiest first). The bus drives along the road
    and stops at every stop whose crowd is at least the threshold.
    """
    if not sorted_stops:
        return ""

    count = len(sorted_stops)
    centers = [100 * (i + 0.5) / count for i in range(count)]  # x position of each stop in %
    targets = [i for i, stop in enumerate(sorted_stops) if stop[1] >= threshold]

    # 1) The row of stops under the road
    stop_html = ""
    for i, (name, crowd) in enumerate(sorted_stops):
        needs_bus = crowd >= threshold
        if needs_bus:
            box = "border:2px solid #f59e0b;background:rgba(245,158,11,0.18);"
            note = "needs bus"
        else:
            box = "border:2px solid transparent;"
            note = "ok"
        safe_name = html.escape(name)
        stop_html += (
            f'<div title="{safe_name}: {crowd} people" style="flex:1;min-width:0;'
            f'text-align:center;font-size:12px;border-radius:8px;padding:4px 2px;{box}">'
            '<div style="font-size:22px">&#128655;</div>'
            f'<div style="overflow:hidden;white-space:nowrap;text-overflow:ellipsis">{safe_name}</div>'
            f'<div>&#128101; {crowd}</div>'
            f'<div style="opacity:0.7">#{i + 1} &middot; {note}</div>'
            '</div>'
        )

    # 2) The bus. Nobody needs it -> it stays in the depot. Otherwise it drives.
    bus_style = ("position:absolute;bottom:0;font-size:34px;line-height:1;"
                 "transform:translateX(-50%) scaleX(-1);")  # scaleX(-1): bus looks to the right
    style_tag = ""
    if len(targets) == 0:
        bus_style += "left:3%;"
        message = (f"No stop reaches {threshold} people, so the extra bus stays in the depot.")
    else:
        name = f"drive{next(animation_counter)}"
        travel = 1.2   # seconds to drive to the next stop
        wait = 1.2     # seconds the bus waits at a stop
        total = travel * len(targets) + wait * len(targets) + travel  # last part: drive away

        # Keyframes: start at the left -> stop 1 -> wait -> stop 2 -> wait ... -> drive away
        frames = "0% { left: -4%; }\n"
        time = 0.0
        for i in targets:
            time += travel
            frames += f"{100 * time / total:.2f}% {{ left: {centers[i]:.2f}%; }}\n"   # arrive
            time += wait
            frames += f"{100 * time / total:.2f}% {{ left: {centers[i]:.2f}%; }}\n"   # leave
        frames += "100% { left: 104%; }\n"

        style_tag = f"<style>@keyframes {name} {{\n{frames}}}</style>"
        bus_style += (f"left:3%;animation:{name} {total:.1f}s ease-in-out infinite;")
        message = (f"The extra bus visits {len(targets)} stop(s), busiest first "
                   f"(threshold: {threshold} people).")

    return (
        style_tag +
        f'<div style="margin-bottom:8px">{html.escape(message)}</div>'
        '<div style="position:relative;overflow:hidden">'
        '<div style="position:relative;height:44px">'
        f'<span style="{bus_style}">&#128652;</span></div>'
        '<div style="border-top:4px dashed #6b7280;margin-bottom:6px"></div>'
        f'<div style="display:flex;gap:2px">{stop_html}</div>'
        '</div>'
    )


def run_sort(text, threshold_value):
    """Called by the 'Sort' button. Checks input, runs merge sort, shows step 0."""
    stops, error = parse_input(text)
    threshold = None
    if error == "":
        threshold, error = parse_threshold(threshold_value)

    if error != "":
        # Bad input: show the error and clear everything else
        return (f"**Error:** {error}", [], "", [],
                gr.update(maximum=1, value=0, interactive=False), "")

    sorted_stops, steps, comparisons = merge_sort_with_steps(stops)
    needed = stops_needing_shuttle(sorted_stops, threshold)
    needed_names = [name for name, _ in needed]

    # Final ranking table with a "Shuttle" column
    table = []
    for rank, (name, count) in enumerate(sorted_stops, start=1):
        table.append([rank, name, count, "Needs bus" if name in needed_names else "OK"])

    word = "stop" if len(stops) == 1 else "stops"
    message = f"Sorted {len(stops)} {word} with {comparisons} comparisons. "
    if len(needed) == 0:
        top_name, top_count = sorted_stops[0]
        message += (f"**No extra shuttle needed:** the busiest stop ({top_name}, {top_count} people) "
                    f"is below the threshold of {threshold}.")
    else:
        listing = ", ".join(f"{name} ({count})" for name, count in needed)
        message += f"**Extra shuttle needed at {len(needed)} stop(s):** {listing}."
    if len(sorted_stops) > 1 and sorted_stops[0][1] == sorted_stops[1][1]:
        message += " Equal crowds keep the order of your input."

    slider = gr.update(minimum=0, maximum=len(steps) - 1, value=0,
                       step=1, interactive=True)
    return (message, steps, draw_step(steps, 0), table, slider,
            draw_bus(sorted_stops, threshold))


def show_step(steps, index):
    """Called when the slider moves."""
    return draw_step(steps, int(index))


def go_back(index):
    return max(0, int(index) - 1)


def go_forward(index, steps):
    last = max(0, len(steps) - 1)
    return min(last, int(index) + 1)


with gr.Blocks(title="Shuttle Stop Crowd Ranking - Merge Sort") as demo:
    gr.Markdown("# Shuttle Stop Crowd Ranking\n"
                "Sorts campus shuttle stops by crowd size (busiest first) "
                "using **Merge Sort**, and shows every step. "
                "Stops with a crowd at or above the threshold get an extra bus.")

    steps_state = gr.State([])  # all recorded steps live here

    with gr.Row():
        with gr.Column():
            input_box = gr.Textbox(label="Stops (one per line: name, crowd_count)",
                                   value=EXAMPLE, lines=9)
            threshold_box = gr.Number(label="Threshold: crowd size that needs an extra bus",
                                      value=DEFAULT_THRESHOLD, precision=0)
            with gr.Row():
                sort_button = gr.Button("Sort", variant="primary")
                example_button = gr.Button("Load example")
            message_box = gr.Markdown()
            result_table = gr.Dataframe(headers=["Rank", "Stop", "Crowd", "Shuttle"],
                                        datatype=["number", "str", "number", "str"],
                                        interactive=False, label="Final ranking")
        with gr.Column():
            with gr.Tabs():
                with gr.Tab("Sorting steps"):
                    slider = gr.Slider(0, 1, value=0, step=1, label="Step",
                                       interactive=False)
                    with gr.Row():
                        back_button = gr.Button("< Back")
                        forward_button = gr.Button("Next >")
                    picture = gr.HTML()
                with gr.Tab("Shuttle map"):
                    bus_picture = gr.HTML()

    # Events
    sort_button.click(run_sort, inputs=[input_box, threshold_box],
                      outputs=[message_box, steps_state, picture, result_table,
                               slider, bus_picture])
    example_button.click(lambda: EXAMPLE, outputs=input_box)
    slider.change(show_step, inputs=[steps_state, slider], outputs=picture)
    back_button.click(go_back, inputs=slider, outputs=slider)
    forward_button.click(go_forward, inputs=[slider, steps_state], outputs=slider)

if __name__ == "__main__":
    demo.launch()
