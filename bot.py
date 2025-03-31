import os
import telebot
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from threading import Thread, Lock
from flask import Flask
import time
import logging

# إعدادات السجل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# تهيئة Flask
app = Flask(__name__)

# قفل للعمليات الحرجة
bot_lock = Lock()

# الحصول على المتغيرات البيئية
TOKEN = os.environ.get('TOKEN')
API_KEY = os.environ.get('API_KEY')
bot = telebot.TeleBot(TOKEN)

# المصادر التعليمية المحدثة
EDUCATION_SOURCES = {
    "الدروس والقوانين": {
        "eddirasa": "https://www.eddirasa.com/?s=",
        "profdz": "https://www.prof-dz.com/search?q="
    },
    "الفروض والاختبارات": {
        "dzexams": "https://www.dzexams.com/search?q=",
        "tassili": "https://www.tassilialgerie.com/recherche?q="
    },
    "اليوتيوب التعليمي": {
        "قناة الأستاذ نور الدين": "https://www.youtube.com/c/ProfesseurNoureddine/search?query=",
        "قناة تعليم نت": "https://www.youtube.com/c/TaalamMaana/search?query="
    }
}

# تحسين فهم الترحيب
GREETINGS = ["مرحبا", "اهلا", "سلام", "السلام عليكم", "اهلين", "هلا"]
INTRODUCTION = ["من انت", "من أنت", "تعريف", "عرف نفسك"]
CREATOR = ["من صنعك", "من صممك", "المطور", "البرمجة"]

# نظام تصنيف الأسئلة باستخدام Gemini
def classify_question(text):
    try:
        prompt = f"""صنف هذا النص هل هو متعلق بالمنهاج الدراسي الجزائري للسنة الرابعة متوسط؟
        أجب بنعم أو لا فقط.
        النص: {text}"""
        
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            params={"key": API_KEY},
            timeout=10
        )
        return "نعم" in response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        logger.error(f"تصنيف السؤال فشل: {str(e)}")
        return False

# البحث في المصادر التعليمية
def search_educational_content(query):
    try:
        # البحث أولاً في المواقع التعليمية
        results = []
        for category, sites in EDUCATION_SOURCES.items():
            for site_name, url in sites.items():
                try:
                    search_url = url + quote(query)
                    response = requests.get(search_url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        links = []
                        
                        for link in soup.find_all('a', href=True):
                            href = link.get('href')
                            title = link.text.strip()[:100]
                            if href and title:
                                links.append(f"{title}\n{href}")
                        
                        if links:
                            results.append(f"🔍 نتائج من {site_name}:\n" + "\n".join(links[:2]))
                except Exception as e:
                    logger.error(f"خطأ في البحث بموقع {site_name}: {str(e)}")
        
        if results:
            return "\n\n".join(results)
        
        # إذا لم يجد في المصادر، يستخدم Gemini
        prompt = f"""أجب كمعلم جزائري متخصص في منهاج السنة الرابعة متوسط:
        السؤال: {query}
        - قدم إجابة مختصرة واضحة
        - إن لم تفهم السؤال قل: "لم أفهم سؤالك، يرجى التوضيح"
        - لا تجب عن أي شيء غير دراسي"""
        
        response = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
            json={"contents": [{"parts": [{"text": prompt}]}]},
            params={"key": API_KEY},
            timeout=15
        )
        return response.json()['candidates'][0]['content']['parts'][0]['text']
        
    except Exception as e:
        logger.error(f"البحث فشل: {str(e)}")
        return "عذرًا، لا يمكن الإجابة الآن. يرجى المحاولة لاحقًا."

@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    try:
        text = message.text.lower()
        
        # التحقق من الترحيب والتعريف
        if any(greeting in text for greeting in GREETINGS):
            bot.reply_to(message, "مرحبًا بك! أنا مساعدك الدراسي لرابعة متوسط. اسألني أي شيء عن المنهاج.")
            return
            
        if any(intro in text for intro in INTRODUCTION):
            bot.reply_to(message, "أنا EdoBot، مساعد دراسي متخصص في منهاج السنة الرابعة متوسط في الجزائر.")
            return
            
        if any(creator in text for creator in CREATOR):
            bot.reply_to(message, "صممني المطور Aymen dj max. تابع مشاريعه على: adm-web.ct.ws")
            return
        
        # التصنيف الآني باستخدام Gemini
        is_educational = classify_question(text)
        
        if not is_educational:
            bot.reply_to(message, "عذرًا، أنا متخصص فقط في الأسئلة الدراسية لمنهاج السنة الرابعة متوسط.")
            return
            
        # البحث والإجابة
        response = search_educational_content(message.text)
        bot.reply_to(message, response)
            
    except Exception as e:
        logger.error(f"خطأ في معالجة الرسالة: {str(e)}")
        bot.reply_to(message, "حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.")

# نظام التشغيل المستمر
def run_bot():
    while True:
        try:
            bot.polling(non_stop=True, timeout=30)
        except Exception as e:
            logger.error(f"تعطل البوت: {str(e)} - إعادة التشغيل خلال 10 ثوان")
            time.sleep(10)

if __name__ == "__main__":
    Thread(target=run_bot, daemon=True).start()
    app.run(host='0.0.0.0', port=8080)
