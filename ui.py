import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from main import FeedChecker 

class RSSFeedUI:
    def __init__(self, root, feed_checker):
        self.root = root
        self.root.title("Steam News Feed Monitor")
        self.root.geometry("600x600")
        
        self.feed_checker = feed_checker
        
        # Erstelle die Hauptcontainer mit Padding
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        self._create_header()
        self._create_input_fields()
        self._create_feed_list()
        self._create_controls()
        self._create_status_bar()
        
        # Lade und zeige alle Feeds beim Start
        self.feed_checker.load_feeds()  # Lade die gespeicherten Feeds
        
        # Setze regelmäßige UI-Aktualisierungen
        self._update_feed_status()
        
        # Setze das Cleanup beim Schließen des Fensters
        root.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _create_controls(self):
        control_frame = ttk.Frame(self.main_frame)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stop_button = ttk.Button(
            control_frame,
            text="Stop Selected Feed",
            command=self._stop_selected_feed
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.pause_button = ttk.Button(
            control_frame,
            text="Pause Selected Feed",
            command=self._pause_selected_feed
        )
        self.pause_button.pack(side=tk.LEFT, padx=5)

        self.resume_button = ttk.Button(
            control_frame,
            text="Resume Selected Feed",
            command=self._resume_selected_feed
        )
        self.resume_button.pack(side=tk.LEFT, padx=5)

        self.view_log_button = ttk.Button(
            control_frame,
            text="View Logs",
            command=self._show_logs
        )
        self.view_log_button.pack(side=tk.LEFT, padx=5)
        
    def _pause_selected_feed(self):
        selected_item = self.feed_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a feed to pause!")
            return
        
        game_id = self.feed_tree.item(selected_item[0])["values"][0]
        
        try:
            # Pause the feed in the feed_checker
            self.feed_checker.pause_feed(game_id)
            
            # Update status in the treeview
            self.feed_tree.item(selected_item[0], values=(game_id, "Paused", "Just paused", "0"))
            
            self.status_var.set(f"Paused monitoring feed for game {game_id}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to pause feed: {str(e)}")

    def _resume_selected_feed(self):
        selected_item = self.feed_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a feed to resume!")
            return

        game_id = self.feed_tree.item(selected_item[0])["values"][0]

        try:
            # Resume the feed in the feed_checker
            self.feed_checker.resume_feed(game_id)

            # Update status in the treeview
            self.feed_tree.item(selected_item[0], values=(game_id, "Active", "Resumed", "0"))

            self.status_var.set(f"Resumed monitoring feed for game {game_id}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to resume feed: {str(e)}")

    def _create_header(self):
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        header_label = ttk.Label(
            header_frame, 
            text="Steam News Feed Monitor",
            font=("Helvetica", 16, "bold")
        )
        header_label.pack()

    def _create_input_fields(self):
        input_frame = ttk.LabelFrame(self.main_frame, text="Feed Configuration", padding="5")
        input_frame.pack(fill=tk.X, pady=(0, 10))

        # Webhook URL field
        webhook_frame = ttk.Frame(input_frame)
        webhook_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(webhook_frame, text="Discord Webhook URL:").pack(side=tk.LEFT)
        self.webhook_entry = ttk.Entry(webhook_frame, width=50)
        self.webhook_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)

        # Game ID field
        game_frame = ttk.Frame(input_frame)
        game_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(game_frame, text="Steam Game ID:").pack(side=tk.LEFT)
        self.game_id_entry = ttk.Entry(game_frame, width=50)
        self.game_id_entry.pack(side=tk.LEFT, padx=(5, 0), fill=tk.X, expand=True)

        # Start button
        self.start_button = ttk.Button(
            input_frame,
            text="Start Feed Monitor",
            command=self._start_feed_check
        )
        self.start_button.pack(pady=(5, 0))

    def _create_feed_list(self):
        list_frame = ttk.LabelFrame(self.main_frame, text="Active Feeds", padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Create treeview for feeds
        columns = ("game_id", "status", "last_check", "articles_sent")
        self.feed_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # Set column headings
        self.feed_tree.heading("game_id", text="Game ID")
        self.feed_tree.heading("status", text="Status")
        self.feed_tree.heading("last_check", text="Last Check")
        self.feed_tree.heading("articles_sent", text="Articles Sent")
        
        # Set column widths
        self.feed_tree.column("game_id", width=100)
        self.feed_tree.column("status", width=100)
        self.feed_tree.column("last_check", width=150)
        self.feed_tree.column("articles_sent", width=100)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.feed_tree.yview)
        self.feed_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.feed_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)       

    def _create_status_bar(self):
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(
            self.main_frame,
            textvariable=self.status_var,
            relief=tk.SUNKEN,
            padding="2"
        )
        self.status_bar.pack(fill=tk.X)

    def _start_feed_check(self):
        webhook_url = self.webhook_entry.get().strip()
        game_id = self.game_id_entry.get().strip()
        
        if not webhook_url or not game_id:
            messagebox.showerror(
                "Error",
                "Please enter both webhook URL and game ID!"
            )
            return
            
        try:
            # Start the feed
            self.feed_checker.create_feed(game_id, webhook_url)
            
            # Add to tree view
            self.feed_tree.insert(
                "",
                tk.END,
                game_id,
                values=(game_id, "Active", "Just started", "0")
            )
            
            # Clear input fields
            self.webhook_entry.delete(0, tk.END)
            self.game_id_entry.delete(0, tk.END)
            
            self.status_var.set(f"Started monitoring feed for game {game_id}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start feed: {str(e)}")

    def _stop_selected_feed(self):
        selected_item = self.feed_tree.selection()
        if not selected_item:
            messagebox.showwarning("Warning", "Please select a feed to stop!")
            return
        
        game_id = self.feed_tree.item(selected_item[0])["values"][0]
        
        try:
            self.feed_checker.stop_feed(game_id)
            self.feed_tree.delete(selected_item)
            self.status_var.set(f"Stopped monitoring feed for game {game_id}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop feed: {str(e)}")

    def _show_logs(self):
        with open("feed_checker.log", "r") as log_file:
            logs = log_file.read()
        
        log_window = tk.Toplevel(self.root)
        log_window.title("Logs")
        log_text = tk.Text(log_window, wrap=tk.WORD, height=20, width=80)
        log_text.insert(tk.END, logs)
        log_text.config(state=tk.DISABLED)
        log_text.pack()
        
    def _on_closing(self):
        self.root.quit()
        self.root.destroy()

    def _update_feed_status(self):
            # Feeds aus self.feed_checker.feeds laden und im Treeview anzeigen
            for feed_game_id, feed in self.feed_checker.feeds.items():
               # Hier wird angenommen, dass du den Feed-Status aktualisieren kannst
                self.feed_tree.insert(
                    "", tk.END,
                    feed_game_id,
                    values=(feed_game_id, "Active", "Just started", "0")
                )

# Main entry point
if __name__ == "__main__":
    
    root = tk.Tk()
    feed_checker = FeedChecker()
    app = RSSFeedUI(root, feed_checker)
    root.mainloop()
