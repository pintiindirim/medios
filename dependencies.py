# dependencies.py
import subprocess
from dotenv import load_dotenv
import warnings
import concurrent.futures
import logging
import sys
import threading
import asyncio
import queue
import json
import time
import os
import hashlib
from datetime import datetime
import winsound
from concurrent.futures import ThreadPoolExecutor
import pyttsx3
import re
import aiomysql
import urllib.parse
from playwright.async_api import async_playwright
import httpx
import zmq.asyncio
import requests
from bs4 import BeautifulSoup
from PyQt5.QtGui import QFont, QPixmap, QIcon
from numba import njit
from PyQt5.QtCore import Qt, QTimer, QObject, QRunnable, pyqtSignal, pyqtSlot, QThreadPool, QPropertyAnimation, QEasingCurve
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QScrollArea, QFrame, QLineEdit, QPushButton, QMenu, QGraphicsOpacityEffect, QGraphicsDropShadowEffect)
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import QGridLayout
from asyncio import WindowsSelectorEventLoopPolicy
asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())
import zmq.asyncio
import asyncio
from logconfig import logger  
CENTRAL_PUSH_ENDPOINT = "tcp://127.0.0.1:5560"
async def zmq_publish_message(message):
    context = zmq.asyncio.Context.instance()
    socket = context.socket(zmq.PUSH)
    try:
        socket.connect(CENTRAL_PUSH_ENDPOINT)
        await socket.send_string(message)
        logger.info("Mesaj merkezi servise gonderildi: %s", message)
    except Exception as e:
        logger.error("Mesaj gonderme hatasi: %s", e)
    finally:
        socket.close()
