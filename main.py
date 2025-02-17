import threading
import sqlite3
import logging
import time
from datetime import datetime
import requests
import feedparser
from bs4 import BeautifulSoup
from queue import Queue

class FeedChecker:
    def __init__(self, update_ui_callback=None):
        self.feeds = {}
        self.update_ui_callback = update_ui_callback
        self.lock = threading.Lock()  # Lock für Thread-Sicherheit
        self.setup_logging()
        self.ui_update_queue = Queue()
        self.load_feeds()

    def setup_logging(self):
        logging.basicConfig(
            filename='feed_checker.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def create_feed(self, game_id, webhook_url):
        stop_event = threading.Event()
        pause_event = threading.Event()
        feed_thread = threading.Thread(
            target=self._check_feed,
            args=(game_id, webhook_url, stop_event, pause_event)
        )
        feed_thread.daemon = True

        # Speichern der Feed-Daten in der Datenbank
        conn = sqlite3.connect('feeds.db', check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS feeds (
            game_id TEXT PRIMARY KEY,
            webhook_url TEXT
        )''')
        cursor.execute('INSERT OR REPLACE INTO feeds (game_id, webhook_url) VALUES (?, ?)', (game_id, webhook_url))
        conn.commit()
        conn.close()

        with self.lock:
            self.feeds[game_id] = {
                "thread": feed_thread,
                "stop_event": stop_event,
                "pause_event": pause_event,
                "webhook_url": webhook_url,
                "paused": False
            }

        feed_thread.start()
        logging.info(f"Started feed checker for game {game_id}")

    def load_feeds(self):
        try:
            # Verbindung zur Datenbank herstellen
            conn = sqlite3.connect('feeds.db', check_same_thread=False)
            cursor = conn.cursor()

            try:
                # Abfrage ausführen
                cursor.execute('SELECT game_id, webhook_url FROM feeds')
                rows = cursor.fetchall()
            except sqlite3.DatabaseError as e:
                print(f"Fehler beim Ausführen der Abfrage: {e}")
                conn.close()
                return

            # Verbindung schließen
            conn.close()

            # Feeds erstellen
            for row in rows:
                try:
                    game_id, webhook_url = row
                    # Feed automatisch starten und in der UI anzeigen
                    self.create_feed(game_id, webhook_url)
                except Exception as e:
                    print(f"Fehler beim Erstellen des Feeds für {row}: {e}")

        except sqlite3.Error as e:
            print(f"Fehler bei der Verbindung zur Datenbank: {e}")

    def stop_feed(self, game_id):

        self.remove_feed(game_id)
    
        self.remove_feed_from_ui(game_id)
    
    def remove_feed(self, game_id):
        with self.lock:
            if game_id in self.feeds:
                # Stoppe den Feed und entferne ihn aus der Liste
                self.feeds[game_id]["stop_event"].set()  # Stoppe den Feed-Thread
                self.feeds[game_id]["thread"].join()  # Warten, bis der Thread abgeschlossen ist
                del self.feeds[game_id]  # Entferne den Feed aus der Liste
                logging.info(f"Feed für {game_id} wurde gestoppt und entfernt.")

    def remove_feed_from_ui(self, game_id):
        # Verbindung zur Datenbank herstellen
        conn = sqlite3.connect('feeds.db', check_same_thread=False)
        cursor = conn.cursor()
    
        # Tabelle erstellen, falls sie noch nicht existiert
        cursor.execute('''CREATE TABLE IF NOT EXISTS feeds (
            game_id TEXT PRIMARY KEY,
            webhook_url TEXT
        )''')
    
        # Feed mit der gegebenen game_id löschen
        cursor.execute('DELETE FROM feeds WHERE game_id = ?', (game_id,))
    
        # Änderungen speichern und Verbindung schließen
        conn.commit()
        conn.close()
   
    def pause_feed(self, game_id):
        with self.lock:
            if game_id in self.feeds and not self.feeds[game_id]["paused"]:
                self.feeds[game_id]["paused"] = True
                self.feeds[game_id]["pause_event"].set()
                logging.info(f"Paused feed checker for game {game_id}")
                
                if self.update_ui_callback:
                    self.update_ui_callback(game_id, 'paused')

    def resume_feed(self, game_id):
        with self.lock:
            if game_id in self.feeds and self.feeds[game_id]["paused"]:
                self.feeds[game_id]["paused"] = False
                self.feeds[game_id]["pause_event"].clear()
                logging.info(f"Resumed feed checker for game {game_id}")
                
                if self.update_ui_callback:
                    self.update_ui_callback(game_id, 'resumed')

    def _check_feed(self, game_id, webhook_url, stop_event, pause_event):
        retry_delay = 60
        max_retry_delay = 3600

        # Öffne eine SQLite-Verbindung nur innerhalb dieses Threads
        conn = sqlite3.connect('feed_history.db', check_same_thread=False)
        conn.execute('''CREATE TABLE IF NOT EXISTS sent_articles (
            article_id TEXT PRIMARY KEY,
            game_id TEXT,
            publication_date TEXT,
            sent_date TEXT
        )''')
        conn.commit()

        while not stop_event.is_set():
            if not self.feeds[game_id]["paused"]:
                try:
                    feed_url = f"https://store.steampowered.com/feeds/news/app/{game_id}/"
                    feed = feedparser.parse(feed_url)

                    if feed.bozo:
                        raise Exception(f"Feed parsing error: {feed.bozo_exception}")

                    new_entries = self._get_new_entries(conn, game_id, feed.entries)

                    for entry in new_entries:
                        self._send_to_discord(entry, webhook_url, game_id)

                    retry_delay = 60
                    time.sleep(60)

                except requests.exceptions.RequestException as e:
                    logging.error(f"Network error for game {game_id}: {str(e)}")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, max_retry_delay)

                except Exception as e:
                    logging.error(f"Error in feed checker for game {game_id}: {str(e)}")
                    time.sleep(retry_delay)
                    retry_delay = min(retry_delay * 2, max_retry_delay)
            else:
                pause_event.wait()  # Wait until resume is called

        # Schließe die Verbindung, wenn der Thread beendet wird
        conn.close()

    def _get_new_entries(self, conn, game_id, entries):
        cursor = conn.cursor()
        new_entries = []

        for entry in entries:
            entry_id = entry.get('id', entry.get('link'))
            cursor.execute(
                'SELECT 1 FROM sent_articles WHERE article_id = ? AND game_id = ?',
                (entry_id, game_id)
            )

            if not cursor.fetchone():
                new_entries.append(entry)

                cursor.execute(
                    'INSERT INTO sent_articles (article_id, game_id, publication_date, sent_date) VALUES (?, ?, ?, ?)',
                    (entry_id, game_id, entry.get('published', ''), datetime.utcnow().isoformat())
                )

        conn.commit()
        return new_entries

    def _send_to_discord(self, entry, webhook_url, game_id):
        MAX_RETRIES = 3
        RETRY_DELAY = 5

        title = entry.title
        link = entry.link
        pub_date = entry.get('published', 'Unknown date')

        soup = BeautifulSoup(entry.get('description', ''), "html.parser")
        img_tag = soup.find("img")
        image_url = img_tag["src"] if img_tag else None
        clean_description = soup.get_text(separator="\n", strip=True)

        discord_message = {
            "embeds": [{
                "title": title,
                "url": link,
                "description": clean_description[:2000],  # Discord's 2000 char limit
                "footer": {"text": f"Published: {pub_date}"}
            }]
        }

        if image_url:
            discord_message["embeds"][0]["image"] = {"url": image_url}

        for attempt in range(MAX_RETRIES):
            try:
                response = requests.post(webhook_url, json=discord_message)

                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', RETRY_DELAY))
                    time.sleep(retry_after)
                    continue

                response.raise_for_status()
                logging.info(f"Successfully sent article '{title}' for game {game_id}")
                return

            except requests.exceptions.HTTPError as e:
                if attempt == MAX_RETRIES - 1:
                    logging.error(f"Failed to send article '{title}' for game {game_id}: {str(e)}")
                time.sleep(RETRY_DELAY)

            except Exception as e:
                logging.error(f"Unexpected error sending article '{title}' for game {game_id}: {str(e)}")
                break


