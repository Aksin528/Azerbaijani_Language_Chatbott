# Azerbaijani Language Chatbot 🤖

Salam! Bu layihə Azərbaycan dilində ünsiyyət qura bilən sadə bir chatbot yaratmaq üçündür. Layihə Flask framework-u əsasında qurulub və istifadəçinin suallarına cavab verir.

---

## 🔧 Quraşdırma

### Əvvəlcədən tələblər:
- Python 3
- Flask (`pip install flask`)

### Adımlar:

```bash
git clone https://github.com/Aksin528/Azerbaijani_Language_Chatbott.git
cd Azerbaijani_Language_Chatbott
python app.py

```
🧠 Necə işləyir?
Layihə Flask ilə yazılıb. İstifadəçi sual verdikdə chatbot cavab verir. Bütün danışıqlar conversation_history.json faylında saxlanılır. Verilənlər bazası isə users.db faylı ilə SQLite üzərində qurulub.

📁 Fayl strukturu
📁 templates/
   ├── auth.html             → Giriş/Qeydiyyat səhifəsi
   ├── chat.html             → Chat interfeysi
   └── profile.html          → İstifadəçi profili

📁 uploads/                  → Yüklənmiş fayllar (şəkil və s.)

📄 app.py                    → Flask tətbiqinin əsas faylı
📄 conversation_history.json → Danışıq tarixçəsi
📄 create_database.sql       → Verilənlər bazasının yaradılması üçün SQL
📄 users.db                  → SQLite verilənlər bazası
📄 README.md                 → Layihə haqqında sənəd
👤 Müəllif
Aksin Abdullayev
📧 Email: infosec467@gmail.com
💻 GitHub: Aksin528

📄 Lisenziya
Bu layihə öyrənmə və təcrübə məqsədilə yaradılıb. Açıq mənbəlidir. İstəyənlər inkişaf etdirə və uyğun şəkildə istifadə edə bilər.
