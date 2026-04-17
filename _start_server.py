# -*- coding: utf-8 -*-
"""快速启动预测记录网页服务器"""
import http.server
import socketserver
import webbrowser
import threading
import time
import sys

PORT = 8765

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # 静默日志

Handler.extensions_map.update({
    '.html': 'text/html',
    '.json': 'application/json',
    '.js': 'application/javascript',
    '.css': 'text/css',
})

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    print(f"🏃 服务器已启动: http://localhost:{PORT}/predict_records.html")
    print(f"📊 预测记录网页: http://localhost:{PORT}/predict_records.html")
    print(f"按 Ctrl+C 停止服务器")
    
    # 自动打开浏览器
    time.sleep(1)
    webbrowser.open(f'http://localhost:{PORT}/predict_records.html')
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务器已停止")
