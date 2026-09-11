"""Script to run the VoxLocal web server with rich active meeting state and capture screenshot."""

from pathlib import Path

from voxlocal.knowledge.database import KnowledgeDB
from voxlocal.web.server import SharedWebState, start_web_server


def populate_mock_state():
    SharedWebState.is_recording = True
    SharedWebState.meeting_name = "Architecture Sync: Distributed Audio Pipeline"
    SharedWebState.preset = "architecture_review"
    SharedWebState.elapsed_sec = 1124.0
    SharedWebState.mic_rms = 0.68
    SharedWebState.loopback_rms = 0.45
    SharedWebState.bookmarks_count = 3
    SharedWebState.segments = [
        {
            "timestamp": "10:14:02",
            "speaker": "You",
            "text": "Let's review the dual-stream capture architecture and verify WASAPI loopback latency.",
            "is_bookmarked": False,
        },
        {
            "timestamp": "10:14:18",
            "speaker": "Remote Speaker 1",
            "text": "The ring buffer handles 3-second sliding chunks with zero drops during heavy CPU load.",
            "is_bookmarked": True,
        },
        {
            "timestamp": "10:14:35",
            "speaker": "You",
            "text": "All PII, API tokens, and credentials are automatically redacted before disk writing.",
            "is_bookmarked": False,
        },
        {
            "timestamp": "10:14:52",
            "speaker": "Remote Speaker 2",
            "text": "The SQLite FTS5 search index enables instant full-text lookups and semantic Q&A.",
            "is_bookmarked": True,
        },
        {
            "timestamp": "10:15:10",
            "speaker": "Remote Speaker 1",
            "text": "Action item: benchmark the CTranslate2 model on CPU int8 and publish performance metrics.",
            "is_bookmarked": True,
        },
    ]

    # Populate local knowledge DB with sample meeting for the search tab
    try:
        db = KnowledgeDB()
        db.index_meeting(
            title="Core Audio Pipeline Review",
            date="2026-09-10",
            duration="23m 40s",
            preset="architecture_review",
            participants=["You", "Remote Speaker 1"],
            vault_file=Path("meetings/2026-09-10-core-audio.md"),
            summary="Discussion of WASAPI loopback capture, polyphase resampling, and Silero VAD.",
            segments=[
                (80.0, 95.0, "You", "Let's make sure the audio format is normalized float32 mono at 16kHz.", False),
                (135.0, 150.0, "Remote Speaker 1", "Silero VAD ONNX model runs with under 2ms inference latency.", True),
            ],
        )
    except Exception as exc:
        print("Note: KnowledgeDB populate:", exc)

def run_server():
    populate_mock_state()
    server = start_web_server(port=8543, host="127.0.0.1")
    port = server.server_address[1]
    print(f"Web dashboard running on http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()

if __name__ == "__main__":
    run_server()
