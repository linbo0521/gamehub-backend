# -*- coding: utf-8 -*-
"""
PythonAnywhere WSGI 入口文件
"""
import sys
import os

# 将项目目录加入 Python 路径
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.append(project_dir)

from app import app as application