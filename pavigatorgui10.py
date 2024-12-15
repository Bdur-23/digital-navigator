import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import cv2
import numpy as np
import pyautogui
import time
import threading
from PIL import Image, ImageTk
import pyperclip

def find_and_perform_action(template_path, confidence, action, text_to_paste=None, hotkey=None, entry=None, retries=5, retry_delay=1):
    for _ in range(retries):
        try:
            coordinates = find_similar_image_on_screen(template_path, confidence)
            if coordinates:
                x, y = coordinates[0]
                template = cv2.imread(template_path)
                w, h = template.shape[:-1]

                drag_canvas = entry["drag_canvas"]
                start_point = entry.get("start_point")
                end_point = entry.get("end_point")

                original_width = entry["original_width"]
                original_height = entry["original_height"]

                displayed_width = drag_canvas.winfo_width()
                displayed_height = drag_canvas.winfo_height()

                if start_point and end_point:  # Perform drag
                    start_x = x + int(start_point[0] * (w / displayed_width) * (original_width/w))
                    start_y = y + int(start_point[1] * (h / displayed_height) * (original_height/h))
                    end_x = x + int(end_point[0] * (w / displayed_width) * (original_width/w))
                    end_y = y + int(end_point[1] * (h / displayed_height) * (original_height/h))

                    pyautogui.moveTo(start_x, start_y, duration=0.1)
                    pyautogui.mouseDown()
                    pyautogui.moveTo(end_x, end_y, duration=0.3)
                    pyautogui.mouseUp()
                elif start_point: #click if only start point defined
                    click_x = x + int(start_point[0] * (w / displayed_width) * (original_width/w))
                    click_y = y + int(start_point[1] * (h / displayed_height) * (original_height/h))
                    pyautogui.moveTo(click_x, click_y, duration=0.1)
                    if action == "Click":
                        pyautogui.click()
                    elif action == "Double Click":
                        pyautogui.doubleClick()
                elif action == "Click" or action == "Double Click": #click center if no points defined
                    click_x = x + w // 2
                    click_y = y + h // 2
                    pyautogui.moveTo(click_x, click_y, duration=0.1)
                    if action == "Click":
                        pyautogui.click()
                    elif action == "Double Click":
                        pyautogui.doubleClick()

                if text_to_paste:
                    time.sleep(0.5)
                    pyperclip.copy(text_to_paste)
                    pyautogui.hotkey('ctrl', 'v')

                if hotkey:
                    pyautogui.hotkey(*hotkey.split("+"))

                return True
        except Exception as e:
            print(f"Error during action: {e}")
        time.sleep(retry_delay)
    return False

def find_similar_image_on_screen(template_path, confidence):
    try:
        template = cv2.imread(template_path)
        screen = pyautogui.screenshot()
        screen = np.array(screen)
        screen = cv2.cvtColor(screen, cv2.COLOR_RGB2BGR)
        method = cv2.TM_CCOEFF_NORMED
        res = cv2.matchTemplate(screen, template, method)
        loc = np.where(res >= confidence)
        points = []
        for pt in zip(*loc[::-1]):
            points.append(pt)
        return points
    except Exception as e:
        print(f"Error during image search: {e}")
        return None

def browse_file(image_index):
    filename = filedialog.askopenfilename(initialdir=".", title=f"Select Image {image_index+1}",
                                           filetypes=(("Image files", "*.png;*.jpg;*.jpeg"), ("All files", "*.*")))
    if filename:
        image_entries[image_index]["path"].delete(0, tk.END)
        image_entries[image_index]["path"].insert(0, filename)
        try:
            image = Image.open(filename)
            original_width, original_height = image.size

            # Set maximum dimensions for display
            max_width = 300  # Adjust as needed
            max_height = 200 # Adjust as needed

            # Resize while maintaining aspect ratio
            if original_width > max_width or original_height > max_height:
                image.thumbnail((max_width, max_height))

            photo = ImageTk.PhotoImage(image)

            image_entries[image_index]["label"].config(image=photo)
            image_entries[image_index]["label"].image = photo

            # Resize canvases to match *scaled* image aspect ratio
            click_canvas = image_entries[image_index]["click_canvas"]
            drag_canvas = image_entries[image_index]["drag_canvas"]
            
            click_canvas.config(width=photo.width(), height=photo.height())
            drag_canvas.config(width=photo.width(), height=photo.height())

            #Store original image size
            image_entries[image_index]["original_width"] = original_width
            image_entries[image_index]["original_height"] = original_height

        except Exception as e:
            print(f"Error displaying image: {e}")

def perform_actions():
    def action_thread():
        status_label.config(text="Processing...")
        for i, entry in enumerate(image_entries):
            path = entry["path"].get()
            if not path:
                continue
            confidence = entry["confidence"].get() / 100.0
            action = entry["action"].get()
            paste_text = entry["paste_text"].get()
            hotkey = entry["hotkey"].get() #Get hotkey from entry
            status_label.config(text=f"Processing Image {i+1}...")

            start_time = time.time()
            while True:
                if find_and_perform_action(path, confidence, action, paste_text, hotkey, entry): #send hotkey to the function
                    end_time = time.time()
                    print(f"Image {i+1} found and action performed in {end_time - start_time:.4f} seconds")
                    break
                elif time.time() - start_time > 10:
                    status_label.config(text=f"Image {i+1} not found after 10 seconds.")
                    break
                else:
                    status_label.config(text = f"Retrying Image {i+1}")

        status_label.config(text="Finished processing all images.")
    threading.Thread(target=action_thread).start()

def add_image_entry():
    global image_count
    create_image_entry(image_count)
    image_count += 1

def delete_image_entry(index):
    global image_count
    frame_to_delete = image_entries[index]["frame"]  # Store the frame to delete
    frame_to_delete.destroy()  # Destroy the frame
    del image_entries[index]  # Remove the entry from the list

    # Renumber the image labels and update browse button commands
    for i, entry in enumerate(image_entries):
        entry["path_label"].config(text=f"Image {i+1}:")
        entry["browse_button"].config(command=lambda idx=i: browse_file(idx))
        entry["delete_button"].config(command=lambda idx=i: delete_image_entry(idx))
    image_count -= 1

def create_image_entry(index):
    image_entries.append({})
    frame = tk.Frame(image_frame)
    frame.pack(fill=tk.X, padx=5, pady=(2, 0))
    image_entries[index]["frame"] = frame

    path_label = tk.Label(frame, text=f"Image {index + 1}:")
    path_label.grid(row=0, column=0, padx=(5, 0))
    image_entries[index]["path_label"] = path_label

    path_entry = tk.Entry(frame, width=15)
    path_entry.grid(row=0, column=1, padx=2)
    image_entries[index]["path"] = path_entry

    browse_button = tk.Button(frame, text="Browse", command=lambda index=index: browse_file(index))
    browse_button.grid(row=0, column=2, padx=2)
    image_entries[index]["browse_button"] = browse_button

    delete_button = tk.Button(frame, text="Delete", command=lambda index=index: delete_image_entry(index))
    delete_button.grid(row=0, column=10, padx=2)
    image_entries[index]["delete_button"] = delete_button

    image_label = tk.Label(frame)
    image_label.grid(row=1, column=0, columnspan=3)
    image_entries[index]["label"] = image_label

    confidence_label = tk.Label(frame, text="Conf(%):")
    confidence_label.grid(row=0, column=3, padx=2)

    confidence_scale = tk.Scale(frame, from_=0, to=100, orient=tk.HORIZONTAL, length=75)
    confidence_scale.set(80)
    confidence_scale.grid(row=0, column=4, padx=2)
    image_entries[index]["confidence"] = confidence_scale

    action_combo = ttk.Combobox(frame, values=["Click", "Double Click"], width=15)
    action_combo.current(0)
    action_combo.grid(row=0, column=5, padx=2)
    image_entries[index]["action"] = action_combo

    paste_label = tk.Label(frame, text="Paste Text:")
    paste_label.grid(row=0, column=6, padx=2)

    paste_entry = tk.Entry(frame, width=10)
    paste_entry.grid(row=0, column=7, padx=2)
    image_entries[index]["paste_text"] = paste_entry

    hotkey_label = tk.Label(frame, text="Hotkey:")
    hotkey_label.grid(row=0, column=8, padx=2)

    hotkey_entry = tk.Entry(frame, width=10)
    hotkey_entry.grid(row=0, column=9, padx=(2, 5))
    image_entries[index]["hotkey"] = hotkey_entry

    click_canvas = tk.Canvas(frame, width=100, height=100, bg="white", highlightthickness=1, highlightbackground="black")
    click_canvas.grid(row=1, column=3, padx=5, pady=5)
    image_entries[index]["click_canvas"] = click_canvas
    image_entries[index]["click_point"] = None

    drag_canvas = tk.Canvas(frame, width=100, height=100, bg="white", highlightthickness=1, highlightbackground="black")
    drag_canvas.grid(row=1, column=4, padx=5, pady=5)
    image_entries[index]["drag_canvas"] = drag_canvas
    image_entries[index]["start_point"] = None
    image_entries[index]["end_point"] = None

    def draw_point(event):
        click_canvas.delete("point")
        click_canvas.create_oval(event.x - 2, event.y - 2, event.x + 2, event.y + 2, fill="red", tags="point")
        image_entries[index]["click_point"] = (event.x, event.y)

    click_canvas.bind("<Button-1>", draw_point)

    def start_drag(event):
        image_entries[index]["start_point"] = (event.x, event.y)
        drag_canvas.delete("line")

    def during_drag(event):
        if image_entries[index]["start_point"]:
            drag_canvas.delete("line")
            drag_canvas.create_line(image_entries[index]["start_point"], (event.x, event.y), fill="red", width=2, tags="line")

    def end_drag(event):
        if image_entries[index]["start_point"]:
            image_entries[index]["end_point"] = (event.x, event.y)

    drag_canvas.bind("<Button-1>", start_drag)
    drag_canvas.bind("<B1-Motion>", during_drag)
    drag_canvas.bind("<ButtonRelease-1>", end_drag)

    return frame # return frame to use in delete function

    

    def draw_point(event):
        click_canvas.delete("point")
        click_canvas.create_oval(event.x - 2, event.y - 2, event.x + 2, event.y + 2, fill="red", tags="point")
        image_entries[index]["click_point"] = (event.x, event.y)

    click_canvas.bind("<Button-1>", draw_point)

    def start_drag(event):
        image_entries[index]["start_point"] = (event.x, event.y)
        drag_canvas.delete("line")

    def during_drag(event):
        if image_entries[index]["start_point"]:
            drag_canvas.delete("line")
            drag_canvas.create_line(image_entries[index]["start_point"], (event.x, event.y), fill="red", width=2, tags="line")

    def end_drag(event):
        if image_entries[index]["start_point"]:
            image_entries[index]["end_point"] = (event.x, event.y)

    drag_canvas.bind("<Button-1>", start_drag)
    drag_canvas.bind("<B1-Motion>", during_drag)
    drag_canvas.bind("<ButtonRelease-1>", end_drag)

    return frame # return frame to use in delete function



def draw_point(event, canvas):
    canvas.delete("point")
    canvas.create_oval(event.x - 2, event.y - 2, event.x + 2, event.y + 2, fill="red", tags="point")

def get_click_point_from_canvas(canvas):
    items = canvas.find_withtag("point")
    if items:
        x1, y1, x2, y2 = canvas.coords(items[0])
        return ((x1 + x2) // 2, (y1 + y2) // 2)
    return None

def configure_canvas(event):
    canvas.configure(scrollregion=canvas.bbox("all"))

def show_hotkey_window():
    hotkey_window.deiconify()
    hotkey_window.attributes('-topmost', True)
    hotkey_window.focus_force()
    # Pencereyi ortala
    hotkey_window.update_idletasks()
    width = hotkey_window.winfo_width()
    height = hotkey_window.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    hotkey_window.geometry('{}x{}+{}+{}'.format(width, height, x, y))


root = tk.Tk()
root.title("Multi-Image Clicker")

canvas = tk.Canvas(root)
scrollbary = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
scrollbary.pack(side=tk.RIGHT, fill=tk.Y)
scrollbarx = tk.Scrollbar(root, orient="horizontal", command=canvas.xview)
scrollbarx.pack(side=tk.BOTTOM, fill=tk.X)
canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
canvas.configure(yscrollcommand=scrollbary.set)
canvas.configure(xscrollcommand=scrollbarx.set)

image_frame = tk.Frame(canvas)
canvas.create_window((0, 0), window=image_frame, anchor="nw")

image_entries = []
image_count = 0

add_image_button = tk.Button(root, text="Add Image", command=add_image_entry)
add_image_button.pack(pady=(10,5))

perform_button = tk.Button(root, text="Perform Actions", command=perform_actions)
perform_button.pack(pady=(5,10))

status_label = tk.Label(root, text="")
status_label.pack()

def configure_canvas(event):
    canvas.configure(scrollregion=canvas.bbox("all"))

image_frame.bind("<Configure>", configure_canvas)

create_image_entry(image_count)
image_count += 1

hotkey_window = tk.Toplevel(root)
hotkey_window.title("Enter Hotkey")
hotkey_window.withdraw()

hotkey_label = tk.Label(hotkey_window, text="Press Hotkey Combination (e.g., ctrl+shift+a):")
hotkey_label.pack()

hotkey_entry = tk.Entry(hotkey_window)
hotkey_entry.pack()

def show_hotkey_window():
    hotkey_window.deiconify()
    hotkey_window.attributes('-topmost', True)
    hotkey_window.focus_force()
    # Pencereyi ortala
    hotkey_window.update_idletasks()
    width = hotkey_window.winfo_width()
    height = hotkey_window.winfo_height()
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    hotkey_window.geometry('{}x{}+{}+{}'.format(width, height, x, y))

root.mainloop()
