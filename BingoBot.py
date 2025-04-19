import random
import tkinter as tk
from tkinter import simpledialog, messagebox
from tkinter import filedialog
import os

# === Logic functions ===

def load_level_list(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]
    seen = set()
    unique_lines = []
    for line in lines:
        if line not in seen:
            seen.add(line)
            unique_lines.append(line)
    return unique_lines

def generate_bingo_grid(level_list, seed):
    random.seed(seed)
    grid = []
    seen_tiles = set()

    for _ in range(25):
        while True:
            entry = random.choice(level_list)
            if entry not in seen_tiles:
                seen_tiles.add(entry)
                grid.append(entry)
                break

    return [grid[i:i+5] for i in range(0, 25, 5)]

def load_word_list(file_path):
    word_list = []
    word_categories = {}
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if "," in line:
                parts = line.rsplit(",", 1)
                word = parts[0].strip()
                try:
                    category = int(parts[1])
                    word_categories[word] = category
                except ValueError:
                    word = line
                    category = None
            else:
                word = line
                category = None
            word_list.append(word)
    return sorted(set(word_list)), word_categories

def generate_word_grid(word_list, word_categories, seed):
    random.seed(seed)
    grid = []
    for _ in range(25):
        while True:
            num_words = random.choices([1, 2, 3], weights=[60, 35, 5])[0]
            selected = []
            used_categories = set()
            attempts = 0
            while len(selected) < num_words and attempts < 100:
                word = random.choice(word_list)
                cat = word_categories.get(word)
                if cat is None or cat not in used_categories:
                    if word not in selected:
                        selected.append(word)
                        if cat is not None:
                            used_categories.add(cat)
                attempts += 1
            if len(selected) == num_words:
                grid.append(selected)
                break
    return [grid[i:i+5] for i in range(0, 25, 5)]

def mark_grid(grid, found_words):
    marked = []
    for row in grid:
        marked_row = []
        for tile in row:
            if all(word in found_words for word in tile):
                marked_row.append(True)
            else:
                marked_row.append(False)
        marked.append(marked_row)
    return marked

def check_bingos(marked):
    bingos = []
    for i, row in enumerate(marked):
        if all(row):
            bingos.append(f"Row {chr(65 + i)}")
    for col in range(5):
        if all(marked[row][col] for row in range(5)):
            bingos.append(f"Column {col + 1}")
    if all(marked[i][i] for i in range(5)):
        bingos.append("Diagonal Top-Left to Bottom-Right")
    if all(marked[i][4 - i] for i in range(5)):
        bingos.append("Diagonal Top-Right to Bottom-Left")
    return bingos

def download_levels_to_file():
    import requests
    url = "https://www.bscotch.net/api/levelhead/levels?limit=128&tag=race&dailyBuild=true"
    headers = {"User-Agent": "PythonClient", "Accept": "application/json"}
    response = requests.get(url, headers=headers)
    if response.ok:
        data = response.json().get("data", [])
        with open("levels.txt", "w", encoding="utf-8") as f:
            for level in data:
                line = f"{level['levelId']}, {', '.join(level.get('tagNames', []))}\n"
                f.write(line)
        messagebox.showinfo("Download Complete", f"Downloaded {len(data)} levels to levels.txt")
    else:
        messagebox.showerror("Download Failed", "Could not retrieve level data from server.")

# === GUI ===

class BingoGUI:
    def __init__(self, master, grid, mode, word_list=None):
        self.master = master
        self.grid = grid
        self.mode = mode  # "speed" or "tags"
        self.word_list = word_list or []
        self.cells = [[None for _ in range(5)] for _ in range(5)]
        self.found_words = set()
        self.build_ui()

    def build_ui(self):
        self.master.title("Bingo Grid")
        rows = "ABCDE"

        for i in range(5):
            for j in range(5):
                frame = tk.Frame(self.master, relief="solid", borderwidth=1)
                frame.grid(row=i, column=j, padx=2, pady=2)

                coord = f"{rows[i]}{j + 1}"
                content = self.grid[i][j]

                if self.mode == "speed":
                    parts = [p.strip() for p in content.split(",")]
                    level_id = parts[0]
                    tags = ", ".join(parts[1:]) if len(parts) > 1 else ""

                    label_text = f"{coord}\n{level_id}"
                    label = tk.Label(frame, text=label_text, width=15, height=3,
                                     wraplength=100, justify="center", bg="white", font=("Arial", 10))
                    label.pack()

                    tag_label = tk.Label(frame, text=tags, font=("Arial", 8), fg="gray")
                    tag_label.pack()

                    entry = tk.Entry(frame, width=10, justify="center")
                    entry.insert(0, "0.0")
                    entry.pack(pady=2)

                    label.bind("<Button-1>", lambda e, lbl=label: self.cycle_color(lbl))
                    self.cells[i][j] = (label, tag_label, entry)

                elif self.mode == "tags":
                    words = content
                    label = tk.Label(frame, text=f"{coord}\n{', '.join(words)}", width=15, height=4,
                                     wraplength=100, justify="center", bg="white", font=("Arial", 10))
                    label.pack()
                    self.cells[i][j] = (label, None, words)

        if self.mode == "tags":
            self.search_var = tk.StringVar()
            self.search_var.trace("w", self.update_dropdown)

            self.entry = tk.Entry(self.master, textvariable=self.search_var, width=50)
            self.entry.grid(row=6, column=0, columnspan=3, padx=10, pady=10)

            self.listbox = tk.Listbox(self.master, height=5, width=47)
            self.listbox.grid(row=7, column=0, columnspan=3, padx=10)
            self.listbox.bind("<Double-Button-1>", self.select_from_listbox)

            self.submit_btn = tk.Button(self.master, text="Submit", command=self.process_input)
            self.submit_btn.grid(row=6, column=3, columnspan=2, padx=10, pady=10)
            self.message_label = tk.Label(self.master, text="", fg="green")
            self.message_label.grid(row=8, column=0, columnspan=5)
            self.update_dropdown()

    def update_dropdown(self, *args):
        query = self.search_var.get().strip().lower()
        if "," in query:
            query = query.split(",")[-1].strip()

        self.filtered_words = [word for word in self.word_list if query in word.lower()]
        self.listbox.delete(0, tk.END)
        for word in self.filtered_words:
            self.listbox.insert(tk.END, word)

    def select_from_listbox(self, event):
        selection = self.listbox.curselection()
        if selection:
            selected_word = self.listbox.get(selection[0])
            current_text = self.search_var.get()
            if "," in current_text:
                base = ",".join(current_text.split(",")[:-1]).strip()
                new_text = f"{base}, {selected_word}" if base else selected_word
            else:
                new_text = selected_word
            self.search_var.set(new_text + ", ")

    def process_input(self):
        user_input = self.search_var.get().lower()
        self.search_var.set("")
        new_words = [word.strip() for word in user_input.split(",") if word.strip()]
        self.found_words.update(new_words)
        marked = mark_grid(self.grid, self.found_words)

        rows = "ABCDE"
        for i in range(5):
            for j in range(5):
                label, _, words = self.cells[i][j]
                if marked[i][j]:
                    label.config(bg="lightgreen")
        bingos = check_bingos(marked)
        if bingos:
            self.message_label.config(text="Bingo! " + ", ".join(bingos))
        else:
            self.message_label.config(text="")

    def cycle_color(self, label):
        current_color = label.cget("bg")
        if current_color == "white":
            label.config(bg="#ffcccc")  # light red
        elif current_color == "#ffcccc":
            label.config(bg="#add8e6")  # light blue
        else:
            label.config(bg="white")

# === Mode selection and Run App ===

def select_mode():
    selector = tk.Tk()
    selector.title("Select Bingo Mode")

    choice = tk.StringVar(value="speed")

    def proceed():
        selector.destroy()

    tk.Label(selector, text="Choose Bingo Mode:").pack(padx=10, pady=10)
    tk.Button(selector, text="Download Levels", command=lambda: [download_levels_to_file()]).pack(pady=5)
    tk.Radiobutton(selector, text="Speed Bingo (levels)", variable=choice, value="speed").pack(anchor="w", padx=20)
    tk.Radiobutton(selector, text="Tags Bingo (words)", variable=choice, value="tags").pack(anchor="w", padx=20)
    tk.Button(selector, text="Continue", command=proceed).pack(pady=10)

    selector.mainloop()
    return choice.get()

if __name__ == "__main__":
    mode = select_mode()

    if mode == "speed":
        level_list = load_level_list("levels.txt")
        if len(level_list) == 0:
            print("Your levels.txt is empty!")
        else:
            root = tk.Tk()
            seed = simpledialog.askstring("Seed Input", "Enter a seed:", parent=root)
            if seed:
                grid = generate_bingo_grid(level_list, seed)
                app = BingoGUI(root, grid, mode="speed")
                root.mainloop()

    elif mode == "tags":
        word_list, word_categories = load_word_list("words.txt")
        if len(word_list) == 0:
            print("Your words.txt is empty!")
        else:
            root = tk.Tk()
            seed = simpledialog.askstring("Seed Input", "Enter a seed:", parent=root)
            if seed:
                grid = generate_word_grid(word_list, word_categories, seed)
                app = BingoGUI(root, grid, mode="tags", word_list=word_list)
                root.mainloop()
