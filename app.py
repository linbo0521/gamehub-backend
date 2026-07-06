# -*- coding: utf-8 -*-
"""
Gamehub 后端 - 邮箱验证码 + 注册/登录 + 账户管理
使用 Flask + PythonAnywhere 邮件 API
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import random
import time
import re
import os
import urllib.request
import urllib.error
import json

app = Flask(__name__)
CORS(app)

# ===== 邮件配置（163 邮箱 SMTP） =====
SMTP_SERVER = 'smtp.163.com'
SMTP_PORT = 465
SMTP_USER = 'water98754@163.com'
SMTP_PASS = 'ZApCAz6yemKvzUxb'
FROM_EMAIL = SMTP_USER

# ===== 文件上传配置 =====
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'avatars')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ===== 验证码存储（内存） =====
code_store = {}

# ===== 用户存储 =====
# users[email] = { 'name': str, 'password': str, 'avatar': str (base64), 'games': [str] }
users = {}
# name_owner[name] = email  (保证用户名唯一)
name_owner = {}

def generate_code():
    return str(random.randint(100000, 999999))

import smtplib
from email.mime.text import MIMEText
from email.header import Header

def send_email(target_email, code, purpose='注册'):
    """
    通过 PythonAnywhere 本地 SMTP 发送验证码
    免费版用户：25 端口不需要认证
    每日发送限制以 PythonAnywhere 免费版为准
    """
    subject = 'Gamehub - 邮箱验证码'
    body_html = f"""
    <div style="max-width:600px;margin:0 auto;font-family:'Helvetica Neue',Arial,sans-serif;padding:30px;">
        <div style="text-align:center;margin-bottom:30px;">
            <h1 style="color:#1d1d1f;font-size:28px;font-weight:700;">Gamehub 游戏中心</h1>
        </div>
        <div style="background:#f5f5f7;border-radius:20px;padding:40px;">
            <h2 style="color:#1d1d1f;font-size:20px;margin-bottom:20px;">验证您的邮箱</h2>
            <p style="color:#6e6e73;font-size:15px;line-height:1.6;margin-bottom:24px;">
                您正在{purpose} Gamehub 账户，请使用以下验证码完成验证：
            </p>
            <div style="text-align:center;margin:32px 0;">
                <span style="display:inline-block;font-size:36px;font-weight:700;letter-spacing:8px;color:#007aff;background:#e8f0ff;padding:16px 32px;border-radius:12px;">
                    {code}
                </span>
            </div>
            <p style="color:#86868b;font-size:13px;line-height:1.5;">
                验证码有效期为5分钟，请尽快使用。<br>
                如果您没有申请，请忽略此邮件。
            </p>
        </div>
        <div style="text-align:center;margin-top:20px;color:#86868b;font-size:12px;">
            Copyright &copy; 2026 Rainbow Inc.
        </div>
    </div>
    """
    msg = MIMEText(body_html, 'html', 'utf-8')
    msg['From'] = Header(f'Gamehub <{FROM_EMAIL}>')
    msg['To'] = Header(target_email)
    msg['Subject'] = Header(subject, 'utf-8')
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.sendmail(FROM_EMAIL, [target_email], msg.as_string())
        server.quit()
        print(f'[邮件发送成功] {target_email}')
        return True, None
    except Exception as e:
        print(f'[邮件发送失败] {target_email}: {e}')
        return False, str(e)

# ===== API 路由 =====

@app.route('/api/send_code', methods=['POST'])
def send_code():
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({'success': False, 'message': '请提供邮箱地址'}), 400
    email = data['email'].strip().lower()
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return jsonify({'success': False, 'message': '邮箱格式不正确'}), 400
    last_send = code_store.get(email + '_time')
    if last_send and time.time() - last_send < 60:
        remaining = int(60 - (time.time() - last_send))
        return jsonify({'success': False, 'message': f'请 {remaining} 秒后再获取验证码', 'cooldown': remaining}), 429
    code = generate_code()
    code_store[email] = code
    code_store[email + '_time'] = time.time()
    print(f'[验证码发送] {email} -> {code}')
    success, error = send_email(email, code)
    if success:
        return jsonify({'success': True, 'message': '验证码已发送到您的邮箱，请查收'})
    else:
        code_store.pop(email, None)
        code_store.pop(email + '_time', None)
        print(f'[发送失败] {email}: {error}')
        return jsonify({'success': False, 'message': f'邮件发送失败：{error}'}), 500

@app.route('/api/verify_code', methods=['POST'])
def verify_code():
    data = request.get_json()
    if not data or 'email' not in data or 'code' not in data:
        return jsonify({'success': False, 'message': '请提供邮箱和验证码'}), 400
    email = data['email'].strip().lower()
    code = data['code'].strip()
    stored_code = code_store.get(email)
    if not stored_code:
        return jsonify({'success': False, 'message': '验证码已过期，请重新获取'}), 400
    if code == stored_code:
        return jsonify({'success': True, 'message': '验证码正确'})
    else:
        return jsonify({'success': False, 'message': '验证码错误，请重新输入'}), 400

@app.route('/api/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or 'email' not in data or 'code' not in data or 'password' not in data or 'name' not in data:
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
    email = data['email'].strip().lower()
    code = data['code'].strip()
    password = data['password'].strip()
    name = data['name'].strip()
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', email):
        return jsonify({'success': False, 'message': '邮箱格式不正确'}), 400
    if len(name) < 2:
        return jsonify({'success': False, 'message': '用户名至少2个字符'}), 400
    if len(password) < 6:
        return jsonify({'success': False, 'message': '密码至少6位'}), 400
    if email in users:
        return jsonify({'success': False, 'message': '该邮箱已注册，请直接登录'}), 400
    if name in name_owner:
        return jsonify({'success': False, 'message': '该用户名已被占用，请换一个'}), 400
    stored_code = code_store.get(email)
    if not stored_code:
        return jsonify({'success': False, 'message': '验证码已过期，请重新获取'}), 400
    if code != stored_code:
        return jsonify({'success': False, 'message': '验证码错误'}), 400
    code_store.pop(email, None)
    code_store.pop(email + '_time', None)
    users[email] = {'name': name, 'password': password, 'avatar': None, 'games': []}
    name_owner[name] = email
    print(f'[注册成功] {email} 用户名:{name}')
    return jsonify({'success': True, 'message': '注册成功', 'user': {'email': email, 'name': name}})

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or 'email' not in data or 'password' not in data:
        return jsonify({'success': False, 'message': '请提供邮箱和密码'}), 400
    email = data['email'].strip().lower()
    password = data['password'].strip()
    user = users.get(email)
    if not user:
        return jsonify({'success': False, 'message': '该邮箱未注册，请先注册'}), 400
    if user['password'] != password:
        return jsonify({'success': False, 'message': '密码错误，请重试'}), 400
    print(f'[登录成功] {email}')
    return jsonify({
        'success': True, 'message': '登录成功',
        'user': {
            'email': email,
            'name': user['name'],
            'avatar': user.get('avatar'),
            'games': user.get('games', [])
        }
    })

@app.route('/api/change_password', methods=['POST'])
def change_password():
    data = request.get_json()
    if not data or 'email' not in data or 'old_password' not in data or 'new_password' not in data:
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
    email = data['email'].strip().lower()
    old_password = data['old_password'].strip()
    new_password = data['new_password'].strip()
    user = users.get(email)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 400
    if user['password'] != old_password:
        return jsonify({'success': False, 'message': '原密码错误'}), 400
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': '新密码至少6位'}), 400
    user['password'] = new_password
    print(f'[密码修改] {email}')
    return jsonify({'success': True, 'message': '密码修改成功'})

@app.route('/api/change_password_verified', methods=['POST'])
def change_password_verified():
    """重置密码（通过验证码验证后使用，不需要旧密码）"""
    data = request.get_json()
    if not data or 'email' not in data or 'new_password' not in data:
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
    email = data['email'].strip().lower()
    new_password = data['new_password'].strip()
    user = users.get(email)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 400
    if len(new_password) < 6:
        return jsonify({'success': False, 'message': '新密码至少6位'}), 400
    user['password'] = new_password
    print(f'[密码重置] {email}')
    return jsonify({'success': True, 'message': '密码重置成功'})

@app.route('/api/change_email', methods=['POST'])
def change_email():
    """修改邮箱（需要新邮箱验证码验证）"""
    data = request.get_json()
    if not data or 'old_email' not in data or 'new_email' not in data or 'code' not in data:
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
    old_email = data['old_email'].strip().lower()
    new_email = data['new_email'].strip().lower()
    code = data['code'].strip()

    # 验证旧邮箱存在
    user = users.get(old_email)
    if not user:
        return jsonify({'success': False, 'message': '原邮箱对应的用户不存在'}), 400

    # 新邮箱格式
    if not re.match(r'^[^\s@]+@[^\s@]+\.[^\s@]+$', new_email):
        return jsonify({'success': False, 'message': '新邮箱格式不正确'}), 400

    # 新邮箱未被占用
    if new_email in users and new_email != old_email:
        return jsonify({'success': False, 'message': '该新邮箱已被其他账户使用'}), 400

    # 验证码验证
    stored_code = code_store.get(new_email)
    if not stored_code:
        return jsonify({'success': False, 'message': '验证码已过期，请重新获取'}), 400
    if code != stored_code:
        return jsonify({'success': False, 'message': '验证码错误'}), 400

    # 验证码正确后清除
    code_store.pop(new_email, None)
    code_store.pop(new_email + '_time', None)

    # 从 name_owner 更新
    name_owner[user['name']] = new_email

    # 转移用户数据到新邮箱
    users[new_email] = user
    if new_email != old_email:
        del users[old_email]

    print(f'[邮箱修改] {old_email} -> {new_email}')
    return jsonify({
        'success': True, 'message': '邮箱修改成功',
        'user': {
            'email': new_email,
            'name': user['name'],
            'avatar': user.get('avatar'),
            'games': user.get('games', [])
        }
    })

@app.route('/api/change_name', methods=['POST'])
def change_name():
    """修改用户名"""
    data = request.get_json()
    if not data or 'email' not in data or 'new_name' not in data:
        return jsonify({'success': False, 'message': '缺少必要参数'}), 400
    email = data['email'].strip().lower()
    new_name = data['new_name'].strip()
    user = users.get(email)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 400
    if len(new_name) < 2:
        return jsonify({'success': False, 'message': '用户名至少2个字符'}), 400
    if new_name in name_owner and name_owner[new_name] != email:
        return jsonify({'success': False, 'message': '该用户名已被占用，请换一个'}), 400

    # 释放旧用户名
    old_name = user['name']
    if old_name in name_owner and name_owner[old_name] == email:
        del name_owner[old_name]

    user['name'] = new_name
    name_owner[new_name] = email
    print(f'[用户名修改] {email}: {old_name} -> {new_name}')
    return jsonify({
        'success': True, 'message': '用户名修改成功',
        'user': {
            'email': email,
            'name': new_name,
            'avatar': user.get('avatar'),
            'games': user.get('games', [])
        }
    })

@app.route('/api/upload_avatar', methods=['POST'])
def upload_avatar():
    data = request.get_json()
    if not data or 'email' not in data or 'avatar' not in data:
        return jsonify({'success': False, 'message': '缺少参数'}), 400
    email = data['email'].strip().lower()
    avatar_data = data['avatar']  # base64 图片数据
    user = users.get(email)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 400
    user['avatar'] = avatar_data
    print(f'[头像上传] {email}')
    return jsonify({'success': True, 'message': '头像上传成功', 'avatar': avatar_data})

@app.route('/api/user_info', methods=['POST'])
def user_info():
    data = request.get_json()
    if not data or 'email' not in data:
        return jsonify({'success': False, 'message': '请提供邮箱'}), 400
    email = data['email'].strip().lower()
    user = users.get(email)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 400
    return jsonify({
        'success': True,
        'user': {
            'email': email,
            'name': user['name'],
            'avatar': user.get('avatar'),
            'games': user.get('games', [])
        }
    })

@app.route('/api/add_game', methods=['POST'])
def add_game():
    """记录用户最近玩的游戏"""
    data = request.get_json()
    if not data or 'email' not in data or 'game' not in data:
        return jsonify({'success': False, 'message': '缺少参数'}), 400
    email = data['email'].strip().lower()
    game = data['game'].strip()
    user = users.get(email)
    if not user:
        return jsonify({'success': False, 'message': '用户不存在'}), 400
    games = user.get('games', [])
    if game in games:
        games.remove(game)
    games.insert(0, game)
    if len(games) > 20:
        games = games[:20]
    user['games'] = games
    return jsonify({'success': True, 'message': '已记录', 'games': games})

# ===== 静态文件服务（首页 + 前端页面） =====
# 在 PythonAnywhere 部署时，打开 https://你的用户名.pythonanywhere.com/ 即可

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/<path:filename>')
def serve_static(filename):
    # 安全检查：防止路径穿越
    filename = filename.replace('\\', '/')
    if '..' in filename:
        return jsonify({'error': 'Forbidden'}), 403
    filepath = os.path.join(os.path.dirname(__file__), filename)
    if os.path.isfile(filepath):
        return send_from_directory(os.path.dirname(__file__), filename)
    return jsonify({'error': 'Not found'}), 404

@app.route('/')
def serve_index():
    return send_from_directory(os.path.dirname(__file__), 'game_portal.html')

if __name__ == '__main__':
    print('=' * 50)
    print('  Gamehub 服务启动')
    print('=' * 50)
    print(f'  邮件:    PythonAnywhere API (100封/天)')
    print(f'  地址:    http://0.0.0.0:5000')
    print('  注意: 用户数据存储在内存中，重启后丢失')
    print('=' * 50)
    app.run(host='0.0.0.0', port=5000, debug=True)
