import tkinter as tk
import pandas as pd
import datetime
import pixela
from datetime import datetime as dtt
from tkinter import simpledialog, messagebox
import webbrowser
import os

# ---------------------------- CONSTANTS ------------------------------- #
GREY = "#D3D3D3"
BLACK = "#000000"
FONT_NAME = "Arial"
FONT_SIZE = 16
FONT_SIZE_BUTTON = 16
current_topic: str | None = None   # <- only one timer allowed

def create_gui(learning_date: str):

    topics = []
    
    try:
        df = pd.read_csv("learning_topics.csv",sep=";")
    except FileNotFoundError:
        messagebox.showerror("Missing file", "learning_topics.csv not found.")
        df = pd.DataFrame(columns=["TOPIC","ACTIVE"])

    # Loop through rows where active == "Y"
    for index, row in df[df.ACTIVE == "Y"].iterrows():
        topics.append(row.TOPIC)

    # ---------------------------- UI SETUP ------------------------------- #
    # Today's date pre-filled
    today = datetime.date.today().strftime("%d.%m.%Y")

    window = tk.Tk()
    window.title("Learning Tracker")
    window.config(padx=80, pady=50, bg=GREY)

    window.closed_by_x = False # pyright: ignore[reportAttributeAccessIssue]

    date_var = tk.StringVar(value=learning_date)

    for graph in pixela.get_graph_list(dtt.strptime(learning_date, "%d.%m.%Y").strftime("%Y%m%d")):
        print(f"Existing pixel for the learning day for the graph: {graph["name"]}")
        if graph["name"] not in topics:
            topics.append(graph["name"])
   
    # state
    counters: dict[str, int] = {}
    running: dict[str, bool] = {}        
  

    # widget refs
    value_vars: dict[str, tk.StringVar] = {}
    entries: dict[str, tk.Entry] = {}
    btn_start: dict[str, tk.Button] = {}
    btn_stop: dict[str, tk.Button] = {}
    # (optional) btn_reset: dict[str, tk.Button] = {}

    def open_link(event):
        webpage = os.environ["PIXELA_PROFILE_PAGE"]
        if not webpage:
            messagebox.showerror("Missing config", "PIXELA_PROFILE_PAGE is not set.")
            return
        webbrowser.open_new(webpage)

    def fmt_time(total_seconds: int) -> str:
        h, r = divmod(total_seconds, 3600)
        m, s = divmod(r, 60)
        return f"{m:02d}:{s:02d}" if h == 0 else f"{h:d}:{m:02d}:{s:02d}"

    day_total_var = tk.StringVar(value=fmt_time(0))

    def parse_time(text: str) -> int | None:
        t = text.strip()
        try:
            parts = t.split(":")
            if len(parts) == 1:
                sec = int(parts[0]);  return sec if sec >= 0 else None
            if len(parts) == 2:
                m, s = map(int, parts);  return m*60 + s if (m >= 0 and 0 <= s < 60) else None
            if len(parts) == 3:
                h, m, s = map(int, parts);  return h*3600 + m*60 + s if (h >= 0 and 0 <= m < 60 and 0 <= s < 60) else None
        except ValueError:
            return None
        return None

    def refresh_label(topic: str):
        value_vars[topic].set(fmt_time(counters[topic]))
        refresh_day_total()

    def apply_user_input(topic: str):
        # Ignore edits while running this topic
        if running.get(topic, False):
            refresh_label(topic)
            return
        txt = value_vars[topic].get()
        seconds = parse_time(txt)
        if seconds is None:
            refresh_label(topic)  # revert to last valid
        else:
            counters[topic] = seconds
            refresh_label(topic)

    def set_running_state(topic: str, is_running: bool):
        running[topic] = is_running
        ent = entries[topic]
        if is_running:
            ent.config(state="disabled")
            btn_start[topic].config(state="disabled")
            btn_stop[topic].config(state="normal")
            # if using reset buttons per-topic, you could disable it here
            # btn_reset[topic].config(state="disabled")
        else:
            ent.config(state="normal")
            btn_start[topic].config(state="normal")
            btn_stop[topic].config(state="disabled")
            # btn_reset[topic].config(state="normal")

    def tick(topic: str):
        if running.get(topic, False):
            counters[topic] += 1
            refresh_label(topic)
            window.after(1000, tick, topic)

    def start(topic: str):
        global current_topic
        # Block if some other topic is already running
        if current_topic is not None and current_topic != topic:
            messagebox.showinfo("Timer running",
                                f"'{current_topic}' is already running.\nStop it before starting another.")
            return
        if not running.get(topic, False):
            set_running_state(topic, True)
            current_topic = topic
            # Disable all other Start buttons
            for t, b in btn_start.items():
                if t != topic:
                    b.config(state="disabled")
            tick(topic)

    def stop(topic: str):
        global current_topic
        set_running_state(topic, False)
        if current_topic == topic:
            current_topic = None
            # Re-enable all Start buttons when no timer is running
            for b in btn_start.values():
                b.config(state="normal")

    def reset(topic: str):
        counters[topic] = 0
        refresh_label(topic)

    def refresh_day_total():
        total = sum(counters.values())
        day_total_var.set(fmt_time(total))

    def comment():
        answer = simpledialog.askstring("Comment", "Please enter comment for today's learning:")
        if answer:
            return(answer)
        else:
            return ""
        
    def any_running() -> bool:
        return any(running.values())

    def upload():
        if any_running():
            messagebox.showinfo("Learning in progress", "Stop all timers before uploading.")
            return
        commentt = comment()
        for key, value in counters.items():
            if value == 0:
                try:
                    pixela.delete_pixel(dtt.strptime(date_var.get(), "%d.%m.%Y").strftime("%Y%m%d"),pixela.to_graph_id(key))                    
                except Exception as e:
                    messagebox.showerror("Upload failed", f"{e}")
                    return  
            else:
                try:
                    pixela.create_graph(key)
                    pixela.add_pixel(pixela.to_graph_id(key),dtt.strptime(date_var.get(), "%d.%m.%Y").strftime("%Y%m%d"),str(round(float(value/60))))
                except Exception as e:
                    messagebox.showerror("Upload failed", f"{e}")
                    return                

        pixela.update_total_tracker(dtt.strptime(date_var.get(), "%d.%m.%Y").strftime("%Y%m%d"),commentt)    
        messagebox.showinfo("Done", "Pixela upload executed.")

    # build UI

    # Input box
    entry_date = tk.Entry(window, textvariable=date_var, width=10,font=(FONT_NAME, FONT_SIZE),justify="center")
    entry_date.grid(column=1, row=0,padx=5, pady=5)

    #button upload
    b_upload = tk.Button(window, text="Upload to Pixela", font=(FONT_NAME, FONT_SIZE_BUTTON), command=upload)
    b_upload.grid(column=3, row=0, padx=5, pady=5,columnspan=3)

    #Input box label
    entry_label = tk.Label(text="Your learning day:",font=(FONT_NAME, FONT_SIZE),anchor="e", width=30,bg="#d3d3d3")
    entry_label.grid(column=0,row=0,padx=5, pady=5)

    label = tk.Label(text="Your total learning time for the day:",font=(FONT_NAME, FONT_SIZE),anchor="e", width=30,bg="#d3d3d3")
    label.grid(column=0,row=1,padx=5, pady=5)

    label_total = tk.Label(textvariable=day_total_var, font=(FONT_NAME, FONT_SIZE), anchor="center", width=10, bg="white")
    label_total.grid(column=1, row=1, padx=5, pady=5)

    separator = tk.Frame(window, height=2, bd=0, relief="solid", bg="black")
    separator.grid(row=2, column=0, columnspan=6, sticky="ew", pady=10)

    for i, topic in enumerate(topics, start=3):
        tk.Label(window, text=f"{topic}:", font=(FONT_NAME, FONT_SIZE),
                anchor="e", width=30, bg="#d3d3d3").grid(column=0, row=i, padx=5, pady=5)

        var = tk.StringVar(value=fmt_time(0))
        ent = tk.Entry(window, textvariable=var, font=(FONT_NAME, FONT_SIZE),
                    width=10, justify="center",
                    disabledbackground="white", disabledforeground="black")
        ent.grid(column=1, row=i, padx=5, pady=5)
        ent.bind("<Return>", lambda e, t=topic: apply_user_input(t))
        ent.bind("<FocusOut>", lambda e, t=topic: apply_user_input(t))

        value_vars[topic] = var
        entries[topic] = ent
        counters[topic] = 0
        running[topic] = False

        b_start = tk.Button(window, text="Start", font=(FONT_NAME, FONT_SIZE_BUTTON),
                            command=lambda t=topic: start(t))
        b_start.grid(column=3, row=i, padx=5, pady=5,sticky="e")
        btn_start[topic] = b_start

        b_stop = tk.Button(window, text="Stop", font=(FONT_NAME, FONT_SIZE_BUTTON),
                        command=lambda t=topic: stop(t), state="disabled")
        b_stop.grid(column=4, row=i, padx=5, pady=5)
        btn_stop[topic] = b_stop

        tk.Button(window, text="Reset", font=(FONT_NAME, FONT_SIZE_BUTTON),
                command=lambda t=topic: reset(t)).grid(column=5, row=i, padx=5, pady=5)
        
    link = tk.Label(window, text="Pixela profile page", fg="blue", cursor="hand2",font=(FONT_NAME, FONT_SIZE),bg=GREY)
    link.grid(column=3,row=1,columnspan=3)

    link.bind("<Button-1>", open_link)
        
    for graph in pixela.get_graph_list(dtt.strptime(date_var.get(), "%d.%m.%Y").strftime("%Y%m%d")):
        counters[graph["name"]] = int(graph["quantity"]) * 60

    
    def refresh_all_labels():
        for topic in counters:
            refresh_label(topic) 

    refresh_all_labels()
        
    def validate_date(date_text):
        try:
            # Try to parse the date in dd.mm.yyyy format
            datetime.datetime.strptime(date_text, "%d.%m.%Y")
            return True
        except ValueError:
            return False

    def on_enter(event):
        date_text = entry_date.get()       
        if validate_date(date_text):
            pass
            window.current_date = date_text # pyright: ignore[reportAttributeAccessIssue]
            window.destroy() 
        #    mesagebox.showinfo("Valid Date", f"Entered date: {date_text}")
        else:
            messagebox.showerror("Invalid Date", "Please enter date in format dd.mm.yyyy")
            entry_date.focus_set()     
            entry_date.icursor(tk.END)
            return
            window.focus_set()

    def on_close():        
        window.closed_by_x = True   # type: ignore # change variable when X is clicked#        
        window.destroy()             
    
    entry_date.bind("<Return>", on_enter)      # main Enter key
    entry_date.bind("<KP_Enter>", on_enter)    # numeric keypad Enter (optional)
    refresh_day_total()
    window.protocol("WM_DELETE_WINDOW", on_close)  # handle X button
    window.mainloop()
    if not window.closed_by_x: # type: ignore
        create_gui(window.current_date) # type: ignore

