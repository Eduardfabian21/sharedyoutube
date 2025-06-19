from collections import deque
import json
from flask import Flask, request, jsonify, send_file, Response
import time
port = 80  # Change to 5000 or another port if you don't want to run as root

queue = deque()
now_playing = {
    "title": None,
    "url": None,
    "video_id": None,
    "start_time": None,
    "duration": None # Duration in seconds
}
HTML = """
<!doctype html>
<html>
<head>
  <meta property="og:title" content="YouTube Global Queue" />
  <meta property="og:description" content="See what people are watching at" />
  <meta property="og:image" content="https://yourserver.com/favicon.ico" />
  <meta property="og:url" content="https://sharedyoutube.outsideitrains.com/" />
  <meta property="og:type" content="website" />
  <meta property="og:color" content= "ff0000" />
  <link rel="icon" href="/favicon.ico">
  <title>YouTube Queue</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      background: #121212;
      color: #eee;
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 20px;
      min-height: 100vh;
      margin: 0;
    }
    h1, h2 {
      margin-bottom: 0.5em;
    }
    #player {
      margin-top: 20px;
      border-radius: 8px;
      overflow: hidden;
      box-shadow: 0 0 10px #000;
      width: 640px;
      height: 390px;
      background: black;
    }
    #overlay {
      position: fixed;
      top: 0; left: 0; right: 0; bottom: 0;
      background: rgba(0,0,0,0.85);
      color: #eee;
      display: flex;
      justify-content: center;
      align-items: center;
      font-size: 1.5rem;
      z-index: 10;
      cursor: pointer;
      user-select: none;
    }
    #queueDropdown {
      margin-top: 10px;
      padding: 8px;
      font-size: 1rem;
      border-radius: 5px;
      border: none;
      background: #222;
      color: #eee;
      max-width: 700px;
      width: 100%;
      display: none;
    }
    #suggestForm {
      margin-bottom: 20px;
      width: 100%;
      max-width: 700px;
      display: flex;
    }
    #url {
      flex-grow: 1;
      padding: 10px;
      font-size: 1rem;
      border-radius: 5px 0 0 5px;
      border: none;
      outline: none;
    }
    button {
      padding: 10px 20px;
      font-size: 1rem;
      border-radius: 0 5px 5px 0;
      border: none;
      background: #4caf50;
      color: white;
      cursor: pointer;
      transition: background 0.3s;
    }
    button:hover {
      background: #45a049;
    }
    #nowPlayingText {
      font-weight: bold;
      margin-bottom: 10px;
    }
  </style>
</head>
<body>
  <h1>YouTube Queue</h1>

  <form id="suggestForm">
    <input id="url" type="text" placeholder="YouTube URL" required />
    <button type="submit">Add to Queue</button>
  </form>

  <a href="https://discord.gg/UWWf4RkSYm" target="_blank">Discord Server</a>

  <h2>Now Playing</h2>
  <div id="nowPlayingText">Nothing playing yet.</div>

  <select id="queueDropdown" size="5" title="Click to see queue"></select>

  <div id="player"></div>

  <div id="overlay">Press the screen so I can start playing the video.</div>

  <script src="https://www.youtube-nocookie.com/iframe_api"></script>
  <script>
    let queue = [];
    let player = null;
    let userStarted = false;

    const overlay = document.getElementById('overlay');
    const nowPlayingText = document.getElementById('nowPlayingText');
    const queueDropdown = document.getElementById('queueDropdown');
    const playerDiv = document.getElementById('player');
    const suggestForm = document.getElementById('suggestForm');
    const urlInput = document.getElementById('url');

    function extractID(url) {
      let id = null;
      const vMatch = url.match(/[?&]v=([^&]+)/);
      if (vMatch) id = vMatch[1];
      else {
        const shortMatch = url.match(/youtu\\.be\\/([^?&]+)/);
        if (shortMatch) id = shortMatch[1];
      }
      return id;
    }

    function createPlayer() {
      if (player) {
        player.destroy();
        player = null;
      }
     player = new YT.Player('player', {
     height: '390',
     width: '640',
     playerVars: {
     rel: 0,
     modestbranding: 1,
     origin: window.location.origin,
     playsinline: 1,
     controls: 0,
     iv_load_policy: 3,
     cc_load_policy: 0,
     fs: 0,
     showinfo: 0,
     autoplay: 0,
     mute: 0,
     host: 'https://www.youtube-nocookie.com'
     },
      events: {
       onReady: async () => {
        await updateQueue();
        if (userStarted) {
          const npRes = await fetch('/now');
          const data = await npRes.json();
          if (data.video_id) {
           loadVideoAtTime(data.video_id, data.start_time);
        }
      }
    },
    onStateChange: onPlayerStateChange
  }
});
    }

    overlay.onclick = async () => {
      if (userStarted) return;
      userStarted = true;
      overlay.style.display = 'none';
      await updateQueue();
      if (player && player.loadVideoById) {
        const npRes = await fetch('/now');
        const data = await npRes.json();
        if (data.video_id) {
          loadVideoAtTime(data.video_id, data.start_time);
        }
      }
    };

    async function updateQueue() {
      const res = await fetch('/queue');
      queue = await res.json();

      if (queue.length > 0) {
        queueDropdown.style.display = 'block';
        queueDropdown.innerHTML = '';
        queue.forEach((vid, i) => {
          const opt = document.createElement('option');
          opt.value = vid;
          opt.textContent = "https://youtube.com/watch?v=" + vid;
          if (i === 0) opt.style.fontWeight = 'bold';
          queueDropdown.appendChild(opt);
        });
      } else {
        queueDropdown.style.display = 'none';
        queueDropdown.innerHTML = '';
      }

      const npRes = await fetch('/now');
      const data = await npRes.json();

      if (data.title) {
        nowPlayingText.textContent = "Now playing: " + data.title + " (" + data.video_id + ")";
      } else {
        nowPlayingText.textContent = "Nothing playing yet.";
      }
    }

    async function loadVideoAtTime(videoId, startTime) {
      if (!player) return;
      const elapsed = Math.floor((Date.now() - startTime) / 1000);
      player.loadVideoById({videoId: videoId, startSeconds: elapsed > 0 ? elapsed : 0});
      player.playVideo();

      setTimeout(() => {
        const currentTime = player.getCurrentTime();
        if (Math.abs(currentTime - elapsed) > 2) {
          player.seekTo(elapsed, true);
        }
      }, 1000);
    }

    function onPlayerStateChange(event) {
      if (event.data === YT.PlayerState.PLAYING) {
        const title = player.getVideoData().title || "Playing Video";
        const video_id = player.getVideoData().video_id;
        const url = "https://www.youtube.com/watch?v=" + video_id;
        const duration = player.getDuration();

        fetch('/set_now_playing', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({
            title,
            url,
            video_id,
            start_time: Date.now(),
            duration
          })
        });
      }

      if (event.data === YT.PlayerState.ENDED) {
        fetch('/next', {method: 'POST'})
          .then(updateQueue)
          .then(() => {
            if (userStarted) loadNextVideo();
          });
      }
    }

    function loadNextVideo() {
      if (queue.length === 0) return;
      if (!userStarted) return;
      const vid = queue[0];
      if (vid && player && typeof player.loadVideoById === 'function') {
        player.loadVideoById({videoId: vid, startSeconds: 0});
        player.playVideo();
      }
    }

    suggestForm.onsubmit = async e => {
      e.preventDefault();
      const vid = extractID(urlInput.value.trim());
      if (vid) {
        await fetch('/suggest', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({url: vid})
        });
        urlInput.value = '';
        await updateQueue();
        if (userStarted && queue[0] === vid) loadNextVideo();
      }
    };

    setInterval(updateQueue, 5000);

    // start player after YT API loads
    function onYouTubeIframeAPIReady() {
      createPlayer();
    }
  </script>
</body>
</html>
"""

from flask import Flask, request, jsonify, send_file, Response

app = Flask(__name__)

@app.route('/')
def index():
    return Response(HTML, mimetype='text/html')

@app.route('/favicon.ico')
def favicon():
    try:
        return send_file('favicon.ico', mimetype='image/x-icon')
    except FileNotFoundError:
        return "Favicon not found", 404

@app.route('/queue')
def get_queue():
    return jsonify(list(queue))

@app.route('/now')
def get_now():
    return jsonify(now_playing)

@app.route('/suggest', methods=['POST'])
def suggest():
    data = request.get_json()
    url = data.get('url')
    if url and url not in queue:
        queue.append(url)
    return jsonify(success=True)

@app.route('/next', methods=['POST'])
def next_video():
    if queue:
        queue.popleft()
    return jsonify(success=True)

@app.route('/set_now_playing', methods=['POST'])
def set_now_playing():
    data = request.get_json()
    now_playing['title'] = data.get('title')
    now_playing['url'] = data.get('url')
    now_playing['video_id'] = data.get('video_id')
    now_playing['start_time'] = data.get('start_time')
    now_playing['duration'] = data.get('duration')
    return jsonify(success=True)

if __name__ == '__main__':
    print("EN:")
    print("Starting YouTube Queue server...")
    print("Visit http://localhost:80 to access the queue.")
    print("RO:")
    print("Pornirea serverului YouTube Queue...")
    print("Accesați http://localhost:80 pentru a vizualiza coada.")
    # Run the Flask app
    app.run(host='0.0.0.0', port=port)
    # Note: Running on port 80 requires root privileges on Unix systems.
    # Use a different port (e.g., 5000) if you don't want to run as root.