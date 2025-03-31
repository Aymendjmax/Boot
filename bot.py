import os
import telebot
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, urlencode
from threading import Thread, Lock
from flask import Flask
import time
import logging
import atexit
import re
import json
import random

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
bot = telebot.TeleBot(TOKEN, threaded=True)

# المناهج الدراسية للسنة الرابعة متوسط
SUBJECTS_4AM = {
    "رياضيات": ["معادلات", "هندسة", "إحصاء", "احتمالات", "دوال", "متتاليات", "مثلثات", "تناسب", "حساب مثلثي", "نظرية فيثاغورس", "مبرهنة طاليس"],
    "علوم طبيعية": ["وظائف الحياة", "التنفس", "التكاثر", "الجهاز العصبي", "الجهاز الهضمي", "الجهاز التنفسي", "البيئة", "التلوث", "السلاسل الغذائية"],
    "فيزياء": ["الضوء", "الكهرباء", "المغناطيس", "الطاقة", "الحركة", "القوى", "الضغط", "الحرارة", "الكتلة", "الحجم", "الكثافة"],
    "عربية": ["قواعد", "بلاغة", "إعراب", "نصوص أدبية", "شعر", "نثر", "تعبير كتابي", "مفعول به", "مفعول مطلق", "فاعل", "مبتدأ", "خبر"],
    "فرنسية": ["grammaire", "conjugaison", "vocabulaire", "expression écrite", "lecture", "compréhension"],
    "إنجليزية": ["grammar", "vocabulary", "reading", "writing", "speaking", "listening"],
    "تاريخ": ["الثورة الجزائرية", "الاستعمار", "الحرب العالمية", "الحركة الوطنية", "المقاومة الشعبية"],
    "جغرافيا": ["التضاريس", "المناخ", "السكان", "الموارد الطبيعية", "الزراعة", "الصناعة", "التجارة"],
    "تربية إسلامية": ["العقيدة", "العبادات", "السيرة النبوية", "الأخلاق", "المعاملات", "الحديث", "القرآن"],
    "تربية مدنية": ["المواطنة", "الديمقراطية", "حقوق الإنسان", "المجتمع المدني", "المؤسسات"]
}

# المواقع ذات الأولوية للبحث
PRIORITY_SOURCES = {
    "DzExams": "https://dzexams.com/4am?s=",
    "Eddirasa": "https://www.eddirasa.com/search?q=",
    "الديوان الوطني": "http://www.onefd.edu.dz/?s=",
    "وزارة التربية": "http://www.education.gov.dz/?s=",
}

# باقي المصادر المقدمة مع روابط البحث الخاصة بها
SECONDARY_SOURCES = {
    "المكتبة الرقمية": "http://elearning.mesrs.dz/search?q=",
    "منصة الجزائر": "http://edu-dz.com/search?query=",
    "الأستاذ الجزائري": "https://www.prof-dz.com/search?q=",
    "تعليم نت": "https://www.taalimnet.com/search?query=",
    "طاسيلي": "https://www.tassilialgerie.com/recherche?q=",
    "مدرستي": "https://madrassati.com/search?q=",
    "Ta3lim": "https://www.ta3lim.com/search?q=",
    "فروض dz": "https://www.frodz.com/search?q=",
    "امتحانات dz": "https://www.examens-dz.com/search?q=",
    "4AM Exams": "https://www.4am-exams.com/search?q=",
    "Moyennes": "https://www.moyennes-dz.com/search?q=",
    "Madrassati Exams": "https://madrassati-exams.com/search?q=",
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
    'search': 'بحث في المنهاج',
    'youtube': 'بحث في يوتيوب'
}

@app.route('/')
def home():
    return "EdoBot is running!"

@app.route('/health')
def health():
    return "OK", 200

def set_bot_commands():
    with bot_lock:
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
/youtube - للبحث عن فيديوهات تعليمية
/reset - لمسح المحادثة

يمكنك أيضًا إرسال سؤالك مباشرة وسأبحث في المنهاج الجزائري لرابعة متوسط"""
    bot.send_message(message.chat.id, welcome_msg)

@bot.message_handler(commands=['who'])
def who_are_you(message):
    with bot_lock:
        bot.reply_to(message, "أنا EdoBot، روبوت مساعد لطلاب السنة الرابعة متوسط في الجزائر 📚")

@bot.message_handler(commands=['creator'])
def who_created_you(message):
    with bot_lock:
        bot.reply_to(message, "صممني المطور Aymen dj max. 🌟\nزوروا موقعه: adm-web.ct.ws")

@bot.message_handler(commands=['job'])
def your_job(message):
    with bot_lock:
        bot.reply_to(message, "وظيفتي مساعدتك في:\n- حل أسئلة المنهاج\n- شرح الدروس\n- توفير مصادر موثوقة\n- البحث عن فيديوهات تعليمية")

@bot.message_handler(commands=['reset'])
def reset_chat(message):
    with bot_lock:
        bot.reply_to(message, "تم إعادة تعيين الدردشة بنجاح ✅")

@bot.message_handler(commands=['search'])
def handle_search(message):
    with bot_lock:
        msg = bot.reply_to(message, "أدخل سؤالك الدراسي:")
        bot.register_next_step_handler(msg, process_search)

@bot.message_handler(commands=['youtube'])
def handle_youtube_search(message):
    with bot_lock:
        msg = bot.reply_to(message, "أدخل موضوع البحث للحصول على فيديوهات تعليمية:")
        bot.register_next_step_handler(msg, process_youtube_search)

def process_search(message):
    try:
        handle_edu_question(message)
    except Exception as e:
        logger.error(f"Search error: {str(e)}")
        with bot_lock:
            bot.reply_to(message, "حدث خطأ أثناء البحث. يرجى المحاولة لاحقًا.")

def process_youtube_search(message):
    try:
        query = message.text + " سنة رابعة متوسط شرح درس"
        videos = search_youtube(query)
        
        if videos:
            response = "🎬 فيديوهات تعليمية متعلقة بالموضوع:\n\n"
            for video in videos[:2]:
                response += f"📺 {video['title']}\n"
                response += f"👁️ {video['views']} مشاهدة\n"
                response += f"🔗 {video['url']}\n\n"
            with bot_lock:
                bot.reply_to(message, response)
        else:
            with bot_lock:
                bot.reply_to(message, "للأسف لم أجد فيديوهات مناسبة. حاول استخدام كلمات مفتاحية أخرى.")
    except Exception as e:
        logger.error(f"YouTube search error: {str(e)}")
        with bot_lock:
            bot.reply_to(message, "حدث خطأ أثناء البحث في يوتيوب. يرجى المحاولة لاحقًا.")

def is_4am_curriculum_related(text):
    """فحص دقيق إذا كان السؤال متعلق بمنهاج السنة الرابعة متوسط"""
    
    # قائمة بالكلمات المفتاحية للمنهاج
    text_lower = text.lower()
    
    # تحديد اللغة الأساسية للسؤال
    is_arabic = bool(re.search(r'[\u0600-\u06FF]', text))
    is_french = bool(re.search(r'[éèêëàâçùûüÿôîïœæ]|^[a-z\s]+$', text_lower))
    is_english = bool(re.search(r'^[a-z\s\.,:;!\?]+$', text_lower))
    
    # كلمات تشير إلى السنة الرابعة متوسط
    grade_indicators = [
        "رابعة متوسط", "4 متوسط", "4am", "4eme", "4année", "quatrième", 
        "السنة الرابعة", "السنة ٤", "السنة 4", "صف رابع", "صف ٤", "صف 4"
    ]
    
    # تحقق من إشارة إلى المستوى الدراسي
    has_grade_indicator = any(indicator in text_lower for indicator in grade_indicators)
    
    # إذا لم يذكر المستوى، نتحقق من محتوى السؤال
    if not has_grade_indicator:
        # البحث في مواضيع كل مادة
        for subject, topics in SUBJECTS_4AM.items():
            # فحص اسم المادة
            if subject in text_lower:
                return True
                
            # فحص موضوعات المادة
            for topic in topics:
                if topic in text_lower:
                    return True
    else:
        return True
    
    # فحص إضافي للعبارات التي تشير إلى محتوى دراسي
    educational_terms = [
        "واجب", "فرض", "اختبار", "امتحان", "درس", "شرح", "تمرين", "حل", 
        "قانون", "مسألة", "سؤال", "منهاج", "برنامج", "تعليم", "مراجعة",
        "devoir", "examen", "cours", "exercice", "solution", "problème",
        "homework", "test", "lesson", "exercise", "problem", "review"
    ]
    
    return any(term in text_lower for term in educational_terms)

def search_youtube(query):
    """البحث في يوتيوب وترتيب النتائج حسب عدد المشاهدات"""
    try:
        # بناء رابط البحث
        search_query = quote(query)
        url = f"https://www.youtube.com/results?search_query={search_query}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            logger.error(f"YouTube search failed with status code: {response.status_code}")
            return []
            
        # استخراج بيانات الفيديوهات باستخدام BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # البحث عن البيانات المضمنة في صفحة البحث (الطريقة الأكثر موثوقية)
        videos = []
        
        # استخراج البيانات من النص
        pattern = r'var ytInitialData = (.+?);</script>'
        matches = re.search(pattern, response.text)
        
        if not matches:
            # طريقة بديلة للبحث
            video_elements = soup.select('div#contents ytd-video-renderer, div#contents ytd-compact-video-renderer')
            
            for element in video_elements[:5]:
                title_element = element.select_one('h3 a#video-title') or element.select_one('a#video-title')
                if not title_element:
                    continue
                    
                title = title_element.text.strip()
                video_id = title_element.get('href', '').split('?v=')[-1].split('&')[0]
                url = f"https://www.youtube.com/watch?v={video_id}"
                
                # محاولة استخراج عدد المشاهدات
                views_element = element.select_one('span.style-scope.ytd-video-meta-block:contains("views")')
                views = views_element.text.strip() if views_element else "غير معروف"
                
                videos.append({
                    'title': title,
                    'url': url,
                    'views': views
                })
            
            # إذا لم نجد أي فيديو بالطريقة البديلة
            if not videos:
                # استخدام طريقة أخرى للبحث عن الفيديوهات
                script_elements = soup.find_all('script')
                for script in script_elements:
                    if 'var ytInitialData' in script.text:
                        data_text = script.text.split('var ytInitialData = ')[1].split(';</script>')[0]
                        data = json.loads(data_text)
                        
                        # استخراج محتويات الفيديو من البيانات
                        try:
                            video_items = data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents']
                            
                            for item in video_items:
                                if 'videoRenderer' in item:
                                    video_data = item['videoRenderer']
                                    video_id = video_data.get('videoId', '')
                                    
                                    if not video_id:
                                        continue
                                        
                                    title = video_data.get('title', {}).get('runs', [{}])[0].get('text', 'بدون عنوان')
                                    view_count_text = video_data.get('viewCountText', {}).get('simpleText', 'غير معروف')
                                    
                                    videos.append({
                                        'title': title,
                                        'url': f"https://www.youtube.com/watch?v={video_id}",
                                        'views': view_count_text
                                    })
                        except Exception as e:
                            logger.error(f"Error parsing YouTube data: {str(e)}")
        else:
            try:
                data = json.loads(matches.group(1))
                video_items = data['contents']['twoColumnSearchResultsRenderer']['primaryContents']['sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents']
                
                for item in video_items:
                    if 'videoRenderer' in item:
                        video_data = item['videoRenderer']
                        video_id = video_data.get('videoId', '')
                        
                        if not video_id:
                            continue
                            
                        title = video_data.get('title', {}).get('runs', [{}])[0].get('text', 'بدون عنوان')
                        
                        # استخراج عدد المشاهدات
                        view_count_text = "غير معروف"
                        if 'viewCountText' in video_data:
                            view_count_text = video_data['viewCountText'].get('simpleText', 'غير معروف')
                            # تحويل النص إلى رقم للترتيب
                            try:
                                view_count = ''.join(filter(str.isdigit, view_count_text))
                            except:
                                view_count = 0
                        
                        videos.append({
                            'title': title,
                            'url': f"https://www.youtube.com/watch?v={video_id}",
                            'views': view_count_text
                        })
            except Exception as e:
                logger.error(f"Error extracting YouTube data: {str(e)}")
        
        # طريقة بديلة أخيرة في حالة فشل الطرق السابقة
        if not videos:
            # استخدام تعبير منتظم للبحث عن روابط الفيديو
            video_links = re.findall(r'href=\"\/watch\?v=([^\"]+)\"', response.text)
            seen_ids = set()
            
            for video_id in video_links:
                if video_id in seen_ids:
                    continue
                seen_ids.add(video_id)
                
                videos.append({
                    'title': f"فيديو تعليمي عن {query}",
                    'url': f"https://www.youtube.com/watch?v={video_id}",
                    'views': "غير معروف"
                })
        
        # اختيار الفيديوهات الأكثر مشاهدة
        videos = videos[:5]  # أخذ أول 5 فيديوهات للتصفية
        
        # محاولة ترتيب حسب المشاهدات إذا كانت متوفرة
        try:
            videos = sorted(videos, key=lambda x: int(''.join(filter(str.isdigit, x['views'])) or 0), reverse=True)
        except:
            # في حالة فشل الترتيب، نستخدم الترتيب الحالي
            pass
            
        return videos[:2]  # إرجاع أعلى فيديوهين من حيث عدد المشاهدات
        
    except Exception as e:
        logger.error(f"Error in YouTube search: {str(e)}")
        return []

def search_priority_sources(query):
    """البحث في المصادر ذات الأولوية"""
    results = []
    
    for name, url in PRIORITY_SOURCES.items():
        try:
            search_url = url + quote(query)
            response = requests.get(search_url, timeout=5, headers={'User-Agent': 'Mozilla/5.0'})
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                links = []
                
                # إستراتيجيات بحث مخصصة حسب الموقع
                if "dzexams" in url.lower():
                    # خاص بموقع DzExams
                    articles = soup.select('article.post')
                    for article in articles[:3]:
                        title_elem = article.select_one('h2.entry-title a')
                        if title_elem:
                            title = title_elem.text.strip()
                            href = title_elem['href']
                            links.append(f"{title}\n{href}")
                            
                elif "eddirasa" in url.lower():
                    # خاص بموقع eddirasa
                    results_div = soup.select('div.search-results article')
                    for article in results_div[:3]:
                        title_elem = article.select_one('h3 a')
                        if title_elem:
                            title = title_elem.text.strip()
                            href = title_elem['href']
                            links.append(f"{title}\n{href}")
                else:
                    # البحث العام للمواقع الأخرى
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
    
    return results

def search_all_sources(query):
    """البحث في جميع المصادر المتاحة"""
    # أولاً: البحث في المصادر ذات الأولوية
    results = search_priority_sources(query)
    
    # ثانياً: البحث في المصادر الثانوية
    for name, url in SECONDARY_SOURCES.items():
        try:
            search_url = url + quote(query)
            response = requests.get(search_url, timeout=3, headers={'User-Agent': 'Mozilla/5.0'})
            
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
    
    # ثالثاً: البحث في المصادر الخاصة
    for url in SPECIAL_SOURCES:
        try:
            response = requests.get(url, timeout=3)
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

def get_ai_response(query):
    """محاولة الحصول على إجابة من نموذج AI بديل في حالة فشل جيميناي"""
    try:
        # محاولة استخدام جيميناي API أولاً
        headers = {"Content-Type": "application/json"}
        data = {
            "contents": [{
                "parts": [{
                    "text": f"أجب بدقة كمعلم جزائري متخصص في منهاج السنة الرابعة متوسط: {query}"
                }]
            }]
        }
        
        try:
            response = requests.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={API_KEY}",
                json=data,
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    return result['candidates'][0]['content']['parts'][0]['text']
        except Exception as e:
            logger.error(f"Gemini API Error: {str(e)}")
        
        # إذا فشل جيميناي، نستخدم بديل محلي بسيط (قاعدة إجابات مسبقة)
        common_responses = {
            "معادلة": "في السنة الرابعة متوسط، تدرس المعادلات من الدرجة الأولى بمجهول واحد. القانون الأساسي: ax + b = 0 حيث الحل x = -b/a",
            "هندسة": "تشمل الهندسة في السنة الرابعة متوسط نظرية فيثاغورس، مبرهنة طاليس، التشابه، والتناسب في المثلثات.",
            "فيثاغورس": "نظرية فيثاغورس: في مثلث قائم الزاوية، مربع طول الوتر يساوي مجموع مربعي طولي الضلعين الآخرين. a² + b² = c²",
            "طاليس": "مبرهنة طاليس: إذا قطع مستقيمان متوازيان قطعتان على مستقيمين، فإن النسبة بين قياسي قطعتين من احدى القطع تساوي النسبة بين قياسي القطعتين من القطع الأخرى.",
            "اختبار": "تتكون اختبارات الرياضيات للسنة الرابعة متوسط عادة من ثلاثة تمارين: تمرين حول المعادلات والحساب الجبري، تمرين في الهندسة، وتمرين في الإحصاء والاحتمالات.",
            "فرنسية": "في اللغة الفرنسية للسنة الرابعة متوسط، تدرس القواعد الأساسية مثل الأزمنة (Présent
