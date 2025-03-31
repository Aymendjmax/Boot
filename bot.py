import os
import telebot
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote
from threading import Thread
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

# الحصول على المتغيرات البيئية
TOKEN = os.environ.get('7321228467:AAHI0kDCkoUcRvQ_HyDc5ommu6bweWOG_Ow')
API_KEY = os.environ.get('AIzaSyBIulm0-B7LKL0WQOAkppg1bxpfa6TZQdg')
bot = telebot.TeleBot(TOKEN)

# جميع المصادر المقدمة مع روابط البحث الخاصة بها
OFFICIAL_SOURCES = {
    # المواقع الرسمية
    "الديوان الوطني": "http://www.onefd.edu.dz/?s=",
    "وزارة التربية": "http://www.education.gov.dz/?s=",
    "المكتبة الرقمية": "http://elearning.mesrs.dz/search?q=",
    "منصة الجزائر": "http://edu-dz.com/search?query=",
    "الأستاذ الجزائري": "https://www.prof-dz.com/search?q=",
    "تعليم نت": "https://www.taalimnet.com/search?query=",
    "الدراسة الجزائرية": "https://www.eddirasa.net/search?q=",
    "طاسيلي": "https://www.tassilialgerie.com/recherche?q=",
    "مدرستي": "https://madrassati.com/search?q=",
    "Ta3lim": "https://www.ta3lim.com/search?q=",
    
    # مواقع الفروض
    "فروض dz": "https://www.frodz.com/search?q=",
    "امتحانات dz": "https://www.examens-dz.com/search?q=",
    "4AM Exams": "https://www.4am-exams.com/search?q=",
    "Moyennes": "https://www.moyennes-dz.com/search?q=",
    "Madrassati Exams": "https://madrassati-exams.com/search?q=",
    
    # المدونات
    "مدونة التعليم": "https://education-algerie.blogspot.com/search?q=",
    "مدونة الفروض": "https://frodj-4am.blogspot.com/search?q=",
    "مدونة الأستاذ": "https://prof-algerien.blogspot.com/search?q="
}

# مصادر لا تحتوي على صفحة بحث
SPECIAL_SOURCES = [
    "https://4am.frodz.com",
    "https://www.examens-education.dz",
    "https://www.model-exams.com",
    "https://www.moyenne-exams.com",
    "https://www.old-exams.dz"
]

# الأوامر العربية
ARABIC_COMMANDS = {
    'start': 'بدء التشغيل',
    'who': 'من أنت',
    'creator': 'المطور',
    'job': 'وظيفتي',
    'reset': 'إعادة تعيين',
    'search': 'بحث في المنهاج'
}

@app.route('/')
def home():
    return "EdoBot is running!"

@app.route('/health')
def health():
    return "OK", 200

def set_bot_commands():
    commands = [
        telebot.types.BotCommand(cmd, desc) 
        for cmd, desc in ARABIC_COMMANDS.items()
    ]
    bot.set_my_commands(commands)

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_msg = """مرحباً! أنا EdoBot مساعدك الدراسي 🎓

استخدم هذه الأوامر:
/who - للتعريف بي
/creator - لمعرفة المطور
/job - لمعرفة وظيفتي
/search - للبحث في المنهاج
/reset - لمسح المحادثة

يمكنك أيضًا إرسال سؤالك مباشرة وسأبحث في المنهاج الجزائري لرابعة متوسط"""
    bot.send_message(message.chat.id, welcome_msg)

@bot.message_handler(commands=['who'])
def who_are_you(message):
    bot.reply_to(message, "أنا EdoBot، روبوت مساعد لطلاب السنة الرابعة متوسط في الجزائر 📚")

@bot.message_handler(commands=['creator'])
def who_created_you(message):
    bot.reply_to(message, "صممني المطور Aymen dj max. 🌟\nزوروا موقعه: adm-web.ct.ws")

@bot.message_handler(commands=['job'])
def your_job(message):
    bot.reply_to(message, "وظيفتي مساعدتك في:\n- حل أسئلة المنهاج\n- شرح الدروس\n- توفير مصادر موثوقة")

@bot.message_handler(commands=['reset'])
def reset_chat(message):
    bot.reply_to(message, "تم إعادة تعيين الدردشة بنجاح ✅")

@bot.message_handler(commands=['search'])
def handle_search(message):
    msg = bot.reply_to(message, "أدخل سؤالك الدراسي:")
    bot.register_next_step_handler(msg, process_search)

def process_search(message):
    try:
        handle_edu_question(message)
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        bot.reply_to(message, "حدث خطأ أثناء البحث. يرجى المحاولة لاحقًا.")

def is_study_related(text):
    subjects = ["رياضيات", "علوم", "فيزياء", "عربية", "فرنسية", 
                "تاريخ", "جغرافيا", "إسلامية", "تكنولوجيا", "4am", "متوسط"]
    return any(sub in text.lower() for sub in subjects)

def search_all_sources(query):
    results = []
    
    # البحث في المصادر ذات صفحة البحث
    for name, url in OFFICIAL_SOURCES.items():
        try:
            search_url = url + quote(query)
            response = requests.get(search_url, timeout=10, headers={'User-Agent': 'Mozilla/5.0'})
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                links = []
                
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    if any(kw in href.lower() for kw in ["cours", "article", "4am", "examen", "درس"]):
                        title = link.text.strip()[:100]
                        if title and not any(ext in href for ext in ['.pdf', '.doc']):
                            links.append(f"{title}\n{href}")
                
                if links:
                    results.append((name, "\n".join(links[:2])))
        except Exception as e:
            logger.error(f"Error searching {name}: {str(e)}")
            continue
    
    # البحث في المصادر الخاصة
    for url in SPECIAL_SOURCES:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                found_links = []
                
                for link in soup.find_all('a', href=True):
                    if query.split()[0].lower() in link.text.lower():
                        full_url = requests.compat.urljoin(url, link['href'])
                        found_links.append(f"{link.text.strip()}\n{full_url}")
                
                if found_links:
                    domain = url.split('//')[1].split('/')[0]
                    results.append((domain, "\n".join(found_links[:2])))
        except Exception as e:
            logger.error(f"Error with {url}: {str(e)}")
            continue
    
    return results

def ask_gemini(query):
    try:
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{
                "parts": [{
                    "text": f"أجب بدقة كمعلم جزائري متخصص في منهاج السنة الرابعة متوسط: {query}"
                }]
            }]
        }
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}",
            json=data,
            headers=headers,
            timeout=20
        )
        return response.json()['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        logger.error(f"Gemini API Error: {str(e)}")
        return "عذرًا، حدث خطأ أثناء الحصول على الإجابة."

def handle_edu_question(message):
    text = message.text
        
    # فلترة الأسئلة غير الدراسية
    if not is_study_related(text):
        bot.reply_to(message, "عذرًا، أنا متخصص في الأسئلة الدراسية فقط. ركز على منهاج السنة الرابعة متوسط.")
        return
    
    # البحث في المصادر الرسمية
    source_results = search_all_sources(text)
    
    if source_results:
        response = "🔍 نتائج البحث من المصادر الرسمية:\n\n"
        for i, (name, result) in enumerate(source_results[:3], 1):
            response += f"{i}. {name}:\n{result}\n\n"
        bot.reply_to(message, response)
    else:
        gemini_res = ask_gemini(text)
        bot.reply_to(message, f"إجابة من المحتوى التعليمي:\n{gemini_res}")

@bot.message_handler(func=lambda m: True)
def handle_message(message):
    try:
        if message.text.startswith('/'):
            return
            
        text = message.text.lower()
        
        # الرد على التحيات والتعريف بالنفس
        if any(w in text for w in ["مرحبا", "اهلا", "سلام"]):
            bot.reply_to(message, "مرحباً بك! أنا EdoBot، مساعدك الدراسي. 💡")
            return
        elif "من انت" in text:
            bot.reply_to(message, "أنا EdoBot، روبوت مساعد لطلاب السنة الرابعة متوسط في الجزائر.")
            return
        elif "من صممك" in text:
            bot.reply_to(message, "صممني المطور Aymen dj max. 🌟 زوروا موقعه: adm-web.ct.ws")
            return
        
        handle_edu_question(message)
            
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        bot.reply_to(message, "عذرًا، حدث خطأ غير متوقع. يرجى المحاولة لاحقًا.")

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def run_bot():
    while True:
        try:
            logger.info("Starting bot polling...")
            bot.polling(none_stop=True, timeout=60)
        except Exception as e:
            logger.error(f"Bot crashed: {str(e)}. Restarting in 10 seconds...")
            time.sleep(10)

if __name__ == "__main__":
    set_bot_commands()
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()
    run_bot()
