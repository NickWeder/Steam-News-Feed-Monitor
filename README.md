# Steam News Feed Monitor

## Overview

The **Steam News Feed Monitor** is a Python application that monitors Steam game news feeds and sends updates to a Discord webhook.

## Features

- Fetches news feeds from Steam for specified game IDs.
- Sends news updates to a Discord webhook.
- Stores and retrieves feed configurations using SQLite.
- Provides a Tkinter-based GUI for easy management.
- Logs feed activity for debugging and monitoring.

## Requirements

### Python Version

- Python 3.7+

### Dependencies

Install the required dependencies using:

```sh
pip install -r requirements.txt
```

Create a `requirements.txt` file with:

```
feedparser
beautifulsoup4
requests
tkinter
```

## Installation & Setup

1. **Clone the repository**:
   ```sh
   git clone https://github.com/yourusername/steam-news-feed-monitor.git
   cd steam-news-feed-monitor
   ```
2. **Install dependencies**:
   ```sh
   pip install -r requirements.txt
   ```
3. **Run the application**:
   ```sh
   python ui.py
   ```

## Usage

1. Enter a **Steam Game ID** and a **Discord Webhook URL** in the application.
2. Click **Start Feed Monitor** to begin tracking news.
3. Use the interface to pause, resume, or stop individual feeds.
4. View logs to check the application's activity.

Example for Steam Game ID:
`https://store.steampowered.com/app/<ins>582010</ins>/Monster_Hunter_World/`

## Contributing

Feel free to submit issues or pull requests to enhance the project.

## License

This project is licensed under the Apache 2.0 License.

## Author

[Nick Weder](https://github.com/NickWeder)

