"""Lightweight local web companion dashboard for VoxLocal."""

import http.server
import json
import logging
from typing import ClassVar
from urllib.parse import parse_qs, urlparse

from voxlocal.knowledge.database import KnowledgeDB

logger = logging.getLogger(__name__)

# State container shared with active recording session
class SharedWebState:
    is_recording: bool = False
    meeting_name: str = "No Active Session"
    preset: str = "general"
    elapsed_sec: float = 0.0
    mic_rms: float = 0.0
    loopback_rms: float = 0.0
    segments: ClassVar[list[dict]] = []
    bookmarks_count: int = 0


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>VoxLocal: Ambient Audio Intelligence</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #090d16;
      --card-bg: #131b2e;
      --border: #1e293b;
      --accent: #38bdf8;
      --accent-hover: #0ea5e9;
      --text: #f1f5f9;
      --text-dim: #94a3b8;
      --green: #10b981;
      --yellow: #f59e0b;
      --purple: #c084fc;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: 'Inter', -apple-system, sans-serif;
      background: var(--bg);
      color: var(--text);
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }
    header {
      padding: 16px 24px;
      background: rgba(19, 27, 46, 0.8);
      backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }
    .logo {
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 700;
      font-size: 1.25rem;
      letter-spacing: -0.02em;
    }
    .badge {
      font-size: 0.75rem;
      padding: 3px 8px;
      border-radius: 9999px;
      background: rgba(56, 189, 248, 0.15);
      color: var(--accent);
      border: 1px solid rgba(56, 189, 248, 0.3);
      font-weight: 600;
    }
    .nav-tabs {
      display: flex;
      gap: 8px;
    }
    .tab-btn {
      background: transparent;
      border: 1px solid transparent;
      color: var(--text-dim);
      padding: 8px 16px;
      border-radius: 8px;
      cursor: pointer;
      font-weight: 500;
      transition: all 0.2s;
    }
    .tab-btn.active, .tab-btn:hover {
      color: var(--text);
      background: var(--card-bg);
      border-color: var(--border);
    }
    main {
      flex: 1;
      display: grid;
      grid-template-columns: 360px 1fr;
      overflow: hidden;
    }
    .sidebar {
      background: #0f1626;
      border-right: 1px solid var(--border);
      padding: 20px;
      display: flex;
      flex-direction: column;
      gap: 20px;
      overflow-y: auto;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 16px;
    }
    .card-title {
      font-size: 0.85rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: var(--text-dim);
      margin-bottom: 12px;
    }
    .meter-row {
      margin-bottom: 12px;
    }
    .meter-label {
      display: flex;
      justify-content: space-between;
      font-size: 0.85rem;
      margin-bottom: 6px;
    }
    .meter-bar-container {
      height: 10px;
      background: #1e293b;
      border-radius: 5px;
      overflow: hidden;
    }
    .meter-fill {
      height: 100%;
      width: 0%;
      background: linear-gradient(90deg, var(--green), var(--yellow), #ef4444);
      transition: width 0.1s ease;
      border-radius: 5px;
    }
    .btn {
      width: 100%;
      padding: 12px;
      border-radius: 8px;
      border: none;
      font-weight: 600;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 8px;
      transition: background 0.2s;
    }
    .btn-bookmark {
      background: #d97706;
      color: white;
    }
    .btn-bookmark:hover {
      background: #b45309;
    }
    .btn-copy {
      background: var(--border);
      color: var(--text);
      margin-top: 8px;
    }
    .btn-copy:hover {
      background: #334155;
    }
    .content-area {
      display: flex;
      flex-direction: column;
      background: var(--bg);
      overflow: hidden;
    }
    .panel-header {
      padding: 16px 24px;
      border-bottom: 1px solid var(--border);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }
    .transcript-stream {
      flex: 1;
      overflow-y: auto;
      padding: 24px;
      display: flex;
      flex-direction: column;
      gap: 16px;
    }
    .dialogue-card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 10px;
      padding: 14px 18px;
      line-height: 1.6;
    }
    .dialogue-card.bookmarked {
      border-left: 4px solid var(--yellow);
      background: rgba(245, 158, 11, 0.05);
    }
    .dialogue-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 6px;
      font-size: 0.85rem;
    }
    .speaker-tag {
      font-weight: 600;
    }
    .speaker-you { color: var(--accent); }
    .speaker-remote { color: var(--green); }
    .speaker-other { color: var(--purple); }
    .timestamp {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.75rem;
      color: var(--text-dim);
    }
    .search-input {
      width: 100%;
      padding: 12px 16px;
      background: #090d16;
      border: 1px solid var(--border);
      color: var(--text);
      border-radius: 8px;
      font-size: 0.95rem;
      margin-bottom: 16px;
    }
    .search-input:focus {
      outline: none;
      border-color: var(--accent);
    }
    .hidden { display: none !important; }
  </style>
</head>
<body>
  <header>
    <div class="logo">
      <span>VoxLocal</span>
      <span class="badge">100% OFFLINE</span>
    </div>
    <div class="nav-tabs">
      <button class="tab-btn active" id="tab-live-btn" onclick="showTab('live')">Live Session</button>
      <button class="tab-btn" id="tab-search-btn" onclick="showTab('search')">Meeting Vault</button>
    </div>
  </header>

  <main>
    <aside class="sidebar">
      <div class="card">
        <div class="card-title">Active Audio Levels</div>
        <div class="meter-row">
          <div class="meter-label">
            <span>Mic (You)</span>
            <span id="mic-val">0.000</span>
          </div>
          <div class="meter-bar-container">
            <div id="mic-bar" class="meter-fill"></div>
          </div>
        </div>
        <div class="meter-row">
          <div class="meter-label">
            <span>Loopback (Remote)</span>
            <span id="loopback-val">0.000</span>
          </div>
          <div class="meter-bar-container">
            <div id="loopback-bar" class="meter-fill"></div>
          </div>
        </div>
      </div>

      <div class="card">
        <div class="card-title">Live Controls</div>
        <button class="btn btn-bookmark" onclick="bookmarkMoment()">⭐ Bookmark Takeaway</button>
        <button class="btn btn-copy" onclick="copyTranscript()">📋 Copy Notes</button>
      </div>

      <div class="card">
        <div class="card-title">Session Details</div>
        <div style="font-size: 0.9rem; color: var(--text-dim); line-height: 1.8;">
          <div>Session: <b id="session-name" style="color: var(--text);">Standby</b></div>
          <div>Preset: <span id="session-preset" class="badge">general</span></div>
          <div>Turns: <span id="turns-count">0</span></div>
          <div>Bookmarks: <span id="bookmarks-count">0</span></div>
        </div>
      </div>
    </aside>

    <section class="content-area">
      <!-- Live Session View -->
      <div id="view-live" style="display: flex; flex-direction: column; height: 100%;">
        <div class="panel-header">
          <h2 id="live-header-title">Live Transcript Feed</h2>
          <span id="live-status-dot" style="display: flex; align-items: center; gap: 6px; font-size: 0.85rem; color: var(--green);">
            ● Ready
          </span>
        </div>
        <div class="transcript-stream" id="transcript-feed">
          <div style="color: var(--text-dim); font-style: italic; text-align: center; margin-top: 40px;">
            Waiting for speech activity... Speak into your microphone or play meeting audio.
          </div>
        </div>
      </div>

      <!-- Vault Search View -->
      <div id="view-search" class="hidden" style="display: flex; flex-direction: column; height: 100%; padding: 24px;">
        <h2>Knowledge Base & Meeting Search</h2>
        <p style="color: var(--text-dim); margin: 8px 0 20px 0;">Search all past recorded meetings indexed in SQLite FTS5.</p>
        <input type="text" id="search-box" class="search-input" placeholder="Type keywords (e.g. Flyway, migration, budget)..." onkeyup="if(event.key==='Enter') executeSearch()">
        <div class="transcript-stream" id="search-results" style="padding: 0;"></div>
      </div>
    </section>
  </main>

  <script>
    function showTab(name) {
      document.getElementById('tab-live-btn').classList.toggle('active', name === 'live');
      document.getElementById('tab-search-btn').classList.toggle('active', name === 'search');
      document.getElementById('view-live').classList.toggle('hidden', name !== 'live');
      document.getElementById('view-search').classList.toggle('hidden', name !== 'search');
      if (name === 'search') loadAllMeetings();
    }

    async function pollStatus() {
      try {
        const res = await fetch('/api/status');
        const data = await res.json();
        
        document.getElementById('session-name').innerText = data.meeting_name || "Standby";
        document.getElementById('session-preset').innerText = data.preset || "general";
        document.getElementById('turns-count').innerText = (data.segments || []).length;
        document.getElementById('bookmarks-count').innerText = data.bookmarks_count || 0;

        const micFill = Math.min(100, Math.round(data.mic_rms * 400));
        const lbFill = Math.min(100, Math.round(data.loopback_rms * 400));
        document.getElementById('mic-bar').style.width = micFill + '%';
        document.getElementById('loopback-bar').style.width = lbFill + '%';
        document.getElementById('mic-val').innerText = data.mic_rms.toFixed(3);
        document.getElementById('loopback-val').innerText = data.loopback_rms.toFixed(3);

        renderTranscript(data.segments || []);
      } catch (e) {}
    }

    function renderTranscript(segments) {
      if (!segments || segments.length === 0) return;
      const feed = document.getElementById('transcript-feed');
      feed.innerHTML = segments.map(s => {
        const isYou = s.speaker === 'You';
        const speakerClass = isYou ? 'speaker-you' : 'speaker-remote';
        return `
          <div class="dialogue-card ${s.is_bookmarked ? 'bookmarked' : ''}">
            <div class="dialogue-meta">
              <span class="speaker-tag ${speakerClass}">${s.is_bookmarked ? '⭐ ' : ''}${s.speaker}</span>
              <span class="timestamp">[${s.formatted_timestamp || '00:00'}]</span>
            </div>
            <div>${s.text}</div>
          </div>
        `;
      }).join('');
    }

    async function bookmarkMoment() {
      await fetch('/api/bookmark', { method: 'POST' });
      pollStatus();
    }

    async function copyTranscript() {
      const feed = document.getElementById('transcript-feed');
      await navigator.clipboard.writeText(feed.innerText);
      alert('Transcript copied to clipboard!');
    }

    async function executeSearch() {
      const q = document.getElementById('search-box').value;
      if (!q.trim()) return;
      const res = await fetch('/api/search?q=' + encodeURIComponent(q));
      const results = await res.json();
      const container = document.getElementById('search-results');
      if (results.length === 0) {
        container.innerHTML = '<p style="color: var(--text-dim); text-align: center;">No matching dialogue found.</p>';
        return;
      }
      container.innerHTML = results.map(r => `
        <div class="dialogue-card">
          <div class="dialogue-meta">
            <b>${r.title}</b> <span class="badge">${r.date}</span>
            <span class="speaker-tag speaker-you">${r.speaker}</span>
          </div>
          <div>${r.text}</div>
        </div>
      `).join('');
    }

    async function loadAllMeetings() {
      const res = await fetch('/api/meetings');
      const list = await res.json();
      const container = document.getElementById('search-results');
      if (!list || list.length === 0) {
        container.innerHTML = '<p style="color: var(--text-dim); text-align: center;">No meetings recorded yet.</p>';
        return;
      }
      container.innerHTML = list.map(m => `
        <div class="dialogue-card" style="margin-bottom: 12px;">
          <div class="dialogue-meta">
            <b style="font-size: 1.05rem;">${m.title}</b>
            <span class="badge">${m.preset}</span>
            <span class="timestamp">${m.date} | ${m.duration}</span>
          </div>
          <div style="font-size: 0.85rem; color: var(--text-dim); margin-top: 4px;">
            Participants: ${m.participants || 'N/A'}
          </div>
        </div>
      `).join('');
    }

    setInterval(pollStatus, 800);
  </script>
</body>
</html>
"""


class VoxLocalHTTPHandler(http.server.BaseHTTPRequestHandler):
    """Custom HTTP handler serving dashboard and REST APIs."""

    def log_message(self, format, *args):
        # Silence default terminal request logs
        pass

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))

        elif path == "/api/status":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            data = {
                "is_recording": SharedWebState.is_recording,
                "meeting_name": SharedWebState.meeting_name,
                "preset": SharedWebState.preset,
                "elapsed_sec": SharedWebState.elapsed_sec,
                "mic_rms": SharedWebState.mic_rms,
                "loopback_rms": SharedWebState.loopback_rms,
                "segments": SharedWebState.segments,
                "bookmarks_count": SharedWebState.bookmarks_count,
            }
            self.wfile.write(json.dumps(data).encode("utf-8"))

        elif path == "/api/meetings":
            db = KnowledgeDB()
            meetings = db.list_all_meetings()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(meetings).encode("utf-8"))

        elif path == "/api/search":
            query = parse_qs(parsed.query).get("q", [""])[0]
            db = KnowledgeDB()
            results = db.search(query, limit=10)
            serialized = [
                {
                    "title": r.title,
                    "date": r.date,
                    "speaker": r.speaker,
                    "text": r.text,
                    "is_bookmarked": r.is_bookmarked,
                }
                for r in results
            ]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(serialized).encode("utf-8"))

        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/bookmark":
            SharedWebState.bookmarks_count += 1
            if SharedWebState.segments:
                SharedWebState.segments[-1]["is_bookmarked"] = True
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "bookmarks": SharedWebState.bookmarks_count}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()


def start_web_server(host: str = "127.0.0.1", port: int = 5432) -> http.server.ThreadingHTTPServer:
    """Instantiate and start threading HTTP server."""
    server = http.server.ThreadingHTTPServer((host, port), VoxLocalHTTPHandler)
    logger.info("VoxLocal web server running on http://%s:%d", host, port)
    return server
