import os
import telebot
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from threading import Thread, Lock
from flask import Flask
import time
import logging
import re

# ... (ابقى على إعدادات السجل وتهيئة Flask كما هي)

# مصادر البحث المحدثة
SEARCH_SOURCES = {
    "الدروس": "https://www.eddirasa.com/?s=",
    "الفروض": "https://www.dzexams.com/search?q="
}

# إعدادات يوتيوب
YOUTUBE_API_KEY = os.environ.get('YOUTUBE_API_KEY')  # يحتاج مفتاح YouTube API
YOUTUBE_SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"

def search_youtube(query):
    try:
        params = {
            'part': 'snippet',
            'q': query + " منهاج الجزائر رابعة متوسط",
            'type': 'video',
            'maxResults': 3,
            'order': 'viewCount',  # الترتيب حسب المشاهدات
            'key': YOUTUBE_API_KEY
        }
        
        response = requests.get(YOUTUBE_SEARCH_URL, params=params, timeout=10)
        results = []
        
        for item in response.json().get('items', []):
            video_id = item['id']['videoId']
            title = item['snippet']['title']
            url = f"https://youtu.be/{video_id}"
            results.append(f"{title}\n{url}")
        
        return results if results else None
        
    except Exception as e:
        logger.error(f"خطأ في بحث يوتيوب: {str(e)}")
        return None

def search_websites(query):
    results = []
    for source_name, url in SEARCH_SOURCES.items():
        try:
            search_url = url + quote(query)
            response = requests.get(search_url, timeout=5)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            links = []
            for link in soup.find_all('a', href=True):
                if re.search(r'(درس|ملخص|تمرين|فرض|اختبار)', link.text, re.IGNORECASE):
                    links.append(f"{link.text.strip()}\n{link['href']}")
                    if len(links) >= 2:
                        break
            
            if links:
                results.append(f"🔍 نتائج من {source_name}:\n" + "\n".join(links))
                
        except Exception as e:
            logger.error(f"خطأ في البحث بموقع {source_name}: {str(e)}")
    
    return results if results else None

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    try:
        text = message.text.lower()
        
        # معالجة الترحيب والتعريف (ابقى كما هي)
        
        # البحث المتكامل
        website_results = search_websites(text)
        youtube_results = search_youtube(text)
        
        response = []
        
        if website_results:
            response.extend(website_results)
            
        if youtube_results:
            response.append("🎬 فيديوهات مقترحة:\n" + "\n".join(youtube_results))
            
        if not response:
            # استخدام Gemini كحل أخير
            gemini_response = ask_gemini(text)
            response.append(gemini_response)
            
        bot.reply_to(message, "\n\n".join(response) if response else "لم أجد نتائج، حاول صياغة السؤال بشكل آخر")
        
    except Exception as e:
        logger.error(f"خطأ في معالجة الرسالة: {str(e)}")
        bot.reply_to(message, "حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.")

# ... (ابقى على باقي الدوال وإعدادات التشغيل كما هي)
