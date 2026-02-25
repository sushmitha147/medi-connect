/* ═══════════════════════════════════════════════════════════
   MediConnect – Main JavaScript
   Voice Chatbot + Google Translate + OTP Sign-In + Sidebar
   ═══════════════════════════════════════════════════════════ */

// ─── Sidebar Toggle ─────────────────────────────
function toggleSidebar() {
    document.getElementById('sidebar')?.classList.toggle('open');
    document.getElementById('sidebarOverlay')?.classList.toggle('show');
}

// ═══════════════════════════════════════════════
// CHATBOT – Voice Input, Voice Output, Multilingual
// ═══════════════════════════════════════════════

let voiceOutputEnabled = true;
let isListening = false;
let recognition = null;

function toggleChat() {
    document.getElementById('chatPanel')?.classList.toggle('open');
}

function toggleVoiceOutput() {
    voiceOutputEnabled = !voiceOutputEnabled;
    const btn = document.getElementById('voiceOutputBtn');
    if (btn) {
        btn.innerHTML = voiceOutputEnabled ? '<i class="fas fa-volume-up"></i>' : '<i class="fas fa-volume-mute"></i>';
        btn.style.opacity = voiceOutputEnabled ? '0.9' : '0.4';
    }
}

function speak(text, lang) {
    if (!voiceOutputEnabled) return;
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = lang || document.documentElement.lang || 'en-IN';
    utter.rate = 0.95;
    utter.pitch = 1;
    window.speechSynthesis.speak(utter);
}

function startVoiceInput() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        showAlert('Voice input not supported in this browser. Please use Chrome.', 'error');
        return;
    }
    if (isListening) {
        recognition?.stop();
        return;
    }
    recognition = new SpeechRecognition();
    const lang = localStorage.getItem('mc_lang') || 'en';
    const langMap = { en: 'en-IN', hi: 'hi-IN', ta: 'ta-IN', te: 'te-IN', bn: 'bn-IN', mr: 'mr-IN', kn: 'kn-IN', ml: 'ml-IN', gu: 'gu-IN', pa: 'pa-IN' };
    recognition.lang = langMap[lang] || 'en-IN';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => {
        isListening = true;
        document.getElementById('micIcon').className = 'fas fa-stop';
        document.getElementById('micBtn').style.background = 'var(--danger)';
    };
    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        document.getElementById('chatInput').value = transcript;
        sendChat();
    };
    recognition.onend = () => {
        isListening = false;
        document.getElementById('micIcon').className = 'fas fa-microphone';
        document.getElementById('micBtn').style.background = 'var(--accent)';
    };
    recognition.onerror = () => {
        isListening = false;
        document.getElementById('micIcon').className = 'fas fa-microphone';
        document.getElementById('micBtn').style.background = 'var(--accent)';
    };
    recognition.start();
}

// ─── Google Translate (free browser endpoint) ─────
async function translateText(text, targetLang) {
    if (!targetLang || targetLang === 'en') return text;
    try {
        const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=${targetLang}&dt=t&q=${encodeURIComponent(text)}`;
        const res = await fetch(url);
        const data = await res.json();
        return data[0].map(seg => seg[0]).join('');
    } catch {
        return text; // Fallback to original
    }
}

// ─── Chatbot send ──────────────────────────────
async function sendChat() {
    const input = document.getElementById('chatInput');
    const messages = document.getElementById('chatMessages');
    if (!input || !messages) return;
    const text = input.value.trim();
    if (!text) return;
    const userLang = localStorage.getItem('mc_lang') || 'en';

    messages.innerHTML += `<div class="chat-msg user"><div class="chat-bubble">${escapeHtml(text)}</div></div>`;
    input.value = '';
    messages.scrollTop = messages.scrollHeight;

    const typingId = 'typing-' + Date.now();
    messages.innerHTML += `<div class="chat-msg bot" id="${typingId}"><div class="chat-bubble"><i class="fas fa-spinner fa-spin"></i> Thinking...</div></div>`;
    messages.scrollTop = messages.scrollHeight;

    try {
        // Translate user message to English for backend processing
        const englishText = await translateText(text, 'en');

        const res = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: englishText, lang: userLang })
        });
        const data = await res.json();
        document.getElementById(typingId)?.remove();

        // Translate reply to user's selected language
        let reply = data.reply;
        if (userLang && userLang !== 'en') {
            reply = await translateText(reply, userLang);
        }

        messages.innerHTML += `<div class="chat-msg bot"><div class="chat-bubble">${reply}</div></div>`;
        messages.scrollTop = messages.scrollHeight;

        // Speak the reply
        const speechLangMap = { en: 'en-IN', hi: 'hi-IN', ta: 'ta-IN', te: 'te-IN', bn: 'bn-IN', mr: 'mr-IN', kn: 'kn-IN', ml: 'ml-IN', gu: 'gu-IN', pa: 'pa-IN' };
        speak(reply, speechLangMap[userLang] || 'en-IN');

    } catch {
        document.getElementById(typingId)?.remove();
        messages.innerHTML += `<div class="chat-msg bot"><div class="chat-bubble">Sorry, I'm having trouble connecting. Please try again.</div></div>`;
        messages.scrollTop = messages.scrollHeight;
    }
}

// ═══════════════════════════════════════════════
// OTP SIGN-IN
// ═══════════════════════════════════════════════

function openSignIn() {
    document.getElementById('signInModal')?.classList.add('show');
    document.getElementById('otpStep1').style.display = 'block';
    document.getElementById('otpStep2').style.display = 'none';
}

function closeSignIn() {
    document.getElementById('signInModal')?.classList.remove('show');
}

async function sendOTP() {
    const email = document.getElementById('otpEmail').value.trim();
    if (!email || !email.includes('@')) {
        showAlert('Please enter a valid email address.', 'error');
        return;
    }
    try {
        const res = await fetch('/api/send-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email })
        });
        const data = await res.json();
        if (data.success) {
            document.getElementById('otpEmailDisplay').textContent = email;
            document.getElementById('otpStep1').style.display = 'none';
            document.getElementById('otpStep2').style.display = 'block';
            showAlert('OTP sent to ' + email + '! Check your inbox.');
        } else {
            showAlert(data.message || 'Failed to send OTP', 'error');
        }
    } catch {
        showAlert('Failed to send OTP. Please try again.', 'error');
    }
}

async function verifyOTP() {
    const email = document.getElementById('otpEmail').value.trim();
    const code = document.getElementById('otpCode').value.trim();
    if (!code || code.length < 4) {
        showAlert('Please enter the OTP from your email.', 'error');
        return;
    }
    try {
        const res = await fetch('/api/verify-otp', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, otp: code })
        });
        const data = await res.json();
        if (data.success) {
            closeSignIn();
            showAlert('✅ Signed in successfully! Welcome to MediConnect.');
            localStorage.setItem('mc_user_email', email);
        } else {
            showAlert(data.message || 'Invalid OTP. Please try again.', 'error');
        }
    } catch {
        showAlert('Verification failed. Please try again.', 'error');
    }
}

// ═══════════════════════════════════════════════
// FULL-PAGE TRANSLATIONS (data-i18n system)
// ═══════════════════════════════════════════════
const translations = {
    en: {},

    hi: {
        'Home': 'होम', 'Emergency 108': 'आपातकाल 108', 'Symptom Checker': 'लक्षण जांचक',
        'Appointments': 'अपॉइंटमेंट', 'Medicines': 'दवाइयाँ', 'Telemedicine': 'टेलीमेडिसिन',
        'Patient Portal': 'रोगी पोर्टल', 'Care Plans': 'देखभाल योजना',
        'Analytics': 'विश्लेषण', 'My Profile': 'मेरी प्रोफ़ाइल',
        'Organ Donors': 'अंग दाता', 'Diet & Lifestyle': 'आहार और जीवनशैली',
        'UPI Payment': 'UPI भुगतान', 'Main Menu': 'मुख्य मेनू',
        'Digital Health': 'डिजिटल स्वास्थ्य', 'Account': 'खाता',
        'Emergency 108 & Hospitals': 'आपातकाल 108 और अस्पताल',
        'Call 108 Now': '108 अभी कॉल करें', 'Book Ambulance': 'एम्बुलेंस बुक करें',
        'Share Location': 'स्थान साझा करें', 'Ambulance Tracker': 'एम्बुलेंस ट्रैकर',
        'Est. Arrival': 'अनुमानित आगमन', 'Distance': 'दूरी', 'Avg Speed': 'औसत गति',
        'All Partner Hospitals': 'सभी साझेदार अस्पताल',
        'Share Emergency Details': 'आपातकालीन विवरण साझा करें',
        'Your Address': 'आपका पता', 'Contact Number': 'संपर्क नंबर',
        'Emergency Contact': 'आपातकालीन संपर्क', 'Share with Hospital': 'अस्पताल के साथ साझा करें',
        'Organ Donors & Blood Bank': 'अंग दाता और रक्त बैंक',
        'Registered Donors': 'पंजीकृत दाता', 'Partner Hospitals': 'साझेदार अस्पताल',
        'Total Blood Units': 'कुल रक्त इकाइयाँ', 'KMC Affiliated Hospitals': 'KMC संबद्ध अस्पताल',
        'Blood Availability': 'रक्त उपलब्धता', 'Register as Donor': 'दाता के रूप में पंजीकरण',
        'Full Name': 'पूरा नाम', 'Blood Group': 'रक्त समूह', 'City': 'शहर',
        'Organs to Donate': 'दान करने वाले अंग',
        'Diet & Lifestyle Plans': 'आहार और जीवनशैली योजनाएं',
        'UPI Payment Gateway': 'UPI भुगतान द्वार',
        'Make a Payment': 'भुगतान करें', 'Pay Securely': 'सुरक्षित भुगतान करें',
        'Supported UPI Apps': 'समर्थित UPI ऐप', 'Recent Transactions': 'हाल के लेनदेन',
        'Explore More Services': 'अधिक सेवाएं देखें',
        'Everything you need for your healthcare journey, all in one place.': 'आपकी स्वास्थ्य यात्रा के लिए सब कुछ एक जगह।',
    },

    ta: {
        'Home': 'முகப்பு', 'Emergency 108': 'அவசரம் 108', 'Symptom Checker': 'அறிகுறி சரிபார்ப்பு',
        'Appointments': 'சந்திப்புகள்', 'Medicines': 'மருந்துகள்', 'Telemedicine': 'தொலைமருத்துவம்',
        'Patient Portal': 'நோயாளி போர்டல்', 'Care Plans': 'பராமரிப்பு திட்டங்கள்',
        'Analytics': 'பகுப்பாய்வு', 'My Profile': 'என் சுயவிவரம்',
        'Organ Donors': 'உறுப்பு தானம்', 'Diet & Lifestyle': 'உணவு மற்றும் வாழ்க்கை',
        'UPI Payment': 'UPI கட்டணம்', 'Main Menu': 'பிரதான மெனு',
        'Digital Health': 'டிஜிட்டல் சுகாதாரம்', 'Account': 'கணக்கு',
        'Call 108 Now': '108 இப்போது அழைக்க', 'Book Ambulance': 'ஆம்புலன்ஸ் பதிவு செய்க',
        'Share Location': 'இடத்தை பகிர்', 'Ambulance Tracker': 'ஆம்புலன்ஸ் கண்காணிப்பு',
        'All Partner Hospitals': 'அனைத்து கூட்டாளி மருத்துவமனைகள்',
        'Registered Donors': 'பதிவு செய்த தானியாளர்கள்',
        'Blood Group': 'இரத்த வகை', 'City': 'நகரம்',
        'Pay Securely': 'பாதுகாப்பாக செலுத்துங்கள்',
        'Explore More Services': 'மேலும் சேவைகளை ஆராயுங்கள்',
    },

    te: {
        'Home': 'హోమ్', 'Emergency 108': 'అత్యవసరం 108', 'Symptom Checker': 'లక్షణ పరీక్షకం',
        'Appointments': 'అపాయింట్‌మెంట్లు', 'Medicines': 'మందులు', 'Telemedicine': 'టెలిమెడిసిన్',
        'Patient Portal': 'రోగి పోర్టల్', 'Care Plans': 'సంరక్షణ ప్రణాళికలు',
        'Analytics': 'విశ్లేషణ', 'My Profile': 'నా ప్రొఫైల్',
        'Organ Donors': 'అవయవ దాతలు', 'Diet & Lifestyle': 'ఆహారం మరియు జీవనశైలి',
        'UPI Payment': 'UPI చెల్లింపు', 'Main Menu': 'ప్రధాన మెను',
        'Digital Health': 'డిజిటల్ ఆరోగ్యం', 'Account': 'ఖాతా',
        'Call 108 Now': '108 ఇప్పుడే కాల్ చేయండి', 'Book Ambulance': 'అంబులెన్స్ బుక్ చేయండి',
        'Blood Group': 'రక్త సమూహం', 'City': 'నగరం',
        'Pay Securely': 'సురక్షితంగా చెల్లించండి',
        'Explore More Services': 'మరిన్ని సేవలు అన్వేషించండి',
    },

    bn: {
        'Home': 'হোম', 'Emergency 108': 'জরুরি ১০৮', 'Symptom Checker': 'লক্ষণ পরীক্ষক',
        'Appointments': 'অ্যাপয়েন্টমেন্ট', 'Medicines': 'ওষুধ', 'Telemedicine': 'টেলিমেডিসিন',
        'Patient Portal': 'রোগী পোর্টাল', 'Care Plans': 'যত্ন পরিকল্পনা',
        'Analytics': 'বিশ্লেষণ', 'My Profile': 'আমার প্রোফাইল',
        'Organ Donors': 'অঙ্গ দাতা', 'Diet & Lifestyle': 'খাদ্য ও জীবনধারা',
        'UPI Payment': 'UPI পেমেন্ট', 'Main Menu': 'প্রধান মেনু',
        'Digital Health': 'ডিজিটাল স্বাস্থ্য', 'Account': 'অ্যাকাউন্ট',
        'Call 108 Now': '১০৮ এখনই কল করুন', 'Book Ambulance': 'অ্যাম্বুলেন্স বুক করুন',
        'Blood Group': 'রক্তের গ্রুপ', 'City': 'শহর',
        'Pay Securely': 'নিরাপদে পরিশোধ করুন',
        'Explore More Services': 'আরও পরিষেবা অন্বেষণ করুন',
    },

    mr: {
        'Home': 'मुख्यपृष्ठ', 'Emergency 108': 'आणीबाणी १०८', 'Symptom Checker': 'लक्षण तपासणी',
        'Appointments': 'भेटी', 'Medicines': 'औषधे', 'Telemedicine': 'टेलिमेडिसिन',
        'Patient Portal': 'रुग्ण पोर्टल', 'Care Plans': 'काळजी योजना',
        'Analytics': 'विश्लेषण', 'My Profile': 'माझी प्रोफाइल',
        'Organ Donors': 'अवयव दाते', 'Diet & Lifestyle': 'आहार व जीवनशैली',
        'UPI Payment': 'UPI देयक', 'Main Menu': 'मुख्य मेनू',
        'Digital Health': 'डिजिटल आरोग्य', 'Account': 'खाते',
        'Call 108 Now': '१०८ आत्ता कॉल करा', 'Book Ambulance': 'रुग्णवाहिका बुक करा',
        'Blood Group': 'रक्तगट', 'City': 'शहर',
        'Pay Securely': 'सुरक्षितपणे पेमेंट करा',
        'Explore More Services': 'अधिक सेवा एक्सप्लोर करा',
    },

    kn: {
        'Home': 'ಮುಖಪುಟ', 'Emergency 108': 'ತುರ್ತು ೧೦೮', 'Symptom Checker': 'ರೋಗಲಕ್ಷಣ ಪರೀಕ್ಷಕ',
        'Appointments': 'ಅಪಾಯಿಂಟ್‌ಮೆಂಟ್', 'Medicines': 'ಔಷಧಿಗಳು', 'Telemedicine': 'ಟೆಲಿಮೆಡಿಸಿನ್',
        'Patient Portal': 'ರೋಗಿ ಪೋರ್ಟಲ್', 'Care Plans': 'ಆರೈಕೆ ಯೋಜನೆಗಳು',
        'Analytics': 'ವಿಶ್ಲೇಷಣೆ', 'My Profile': 'ನನ್ನ ಪ್ರೊಫೈಲ್',
        'Organ Donors': 'ಅಂಗ ದಾನಿಗಳು', 'Diet & Lifestyle': 'ಆಹಾರ ಮತ್ತು ಜೀವನಶೈಲಿ',
        'UPI Payment': 'UPI ಪಾವತಿ', 'Main Menu': 'ಮುಖ್ಯ ಮೆನು',
        'Digital Health': 'ಡಿಜಿಟಲ್ ಆರೋಗ್ಯ', 'Account': 'ಖಾತೆ',
        'Call 108 Now': '೧೦೮ ಈಗ ಕರೆ ಮಾಡಿ', 'Book Ambulance': 'ಆ್ಯಂಬ್ಯುಲೆನ್ಸ್ ಬುಕ್ ಮಾಡಿ',
        'Blood Group': 'ರಕ್ತದ ಗುಂಪು', 'City': 'ನಗರ',
        'Pay Securely': 'ಸುರಕ್ಷಿತವಾಗಿ ಪಾವತಿ ಮಾಡಿ',
        'Explore More Services': 'ಹೆಚ್ಚಿನ ಸೇವೆಗಳನ್ನು ಅನ್ವೇಷಿಸಿ',
    },

    gu: {
        'Home': 'હોમ', 'Emergency 108': 'કટોકટી ૧૦૮', 'Symptom Checker': 'લક્ષણ ચેકર',
        'Appointments': 'મુલાકાત', 'Medicines': 'દવાઓ', 'Telemedicine': 'ટેલિમેડિસિન',
        'Patient Portal': 'દર્દી પોર્ટલ', 'Care Plans': 'સંભાળ યોજના',
        'Analytics': 'વિશ્લેષણ', 'My Profile': 'મારી પ્રોફ़ाઇલ',
        'Organ Donors': 'અંગ દાતા', 'Diet & Lifestyle': 'આહાર અને જીવનશૈલી',
        'UPI Payment': 'UPI ચુકવણી', 'Main Menu': 'મુખ્ય મેનૂ',
        'Digital Health': 'ડિજિટલ આરોગ્ય', 'Account': 'એકાઉન્ટ',
        'Call 108 Now': '૧૦૮ હમણાં કૉલ કરો', 'Book Ambulance': 'એમ્બ્યુલન્સ બુક કરો',
        'Blood Group': 'રક્ત જૂથ', 'City': 'શહેર',
        'Pay Securely': 'સુરક્ષિત ચૂકવો',
        'Explore More Services': 'વધુ સેવાઓ એક્સ્પ્લોર કરો',
    },

    ml: {
        'Home': 'ഹോം', 'Emergency 108': 'അടിയന്തര 108', 'Symptom Checker': 'ലക്ഷണ പരിശോധന',
        'Appointments': 'അപ്പോയിന്റ്‌മെന്റ്', 'Medicines': 'മരുന്നുകൾ', 'Telemedicine': 'ടെലിമെഡിസിൻ',
        'Patient Portal': 'രോഗി പോർട്ടൽ', 'Care Plans': 'പരിചരണ പദ്ധതികൾ',
        'Analytics': 'വിശകലനം', 'My Profile': 'എന്റെ പ്രൊഫൈൽ',
        'Organ Donors': 'അവയവ ദാതാക്കൾ', 'Diet & Lifestyle': 'ഭക്ഷണവും ജീവിതശൈലിയും',
        'UPI Payment': 'UPI പേമെന്റ്', 'Main Menu': 'പ്രധാന മെനു',
        'Digital Health': 'ഡിജിറ്റൽ ആരോഗ്യം', 'Account': 'അക്കൗണ്ട്',
        'Call 108 Now': '108 ഇപ്പോൾ വിളിക്കൂ', 'Book Ambulance': 'ആംബുലൻസ് ബുക്ക് ചെയ്യൂ',
        'Blood Group': 'രക്ത ഗ്രൂപ്പ്', 'City': 'നഗരം',
        'Pay Securely': 'സുരക്ഷിതമായി അടയ്ക്കൂ',
        'Explore More Services': 'കൂടുതൽ സേവനങ്ങൾ പര്യവേക്ഷണം ചെയ്യൂ',
    },

    pa: {
        'Home': 'ਘਰ', 'Emergency 108': 'ਐਮਰਜੈਂਸੀ 108', 'Symptom Checker': 'ਲੱਛਣ ਜਾਂਚਕ',
        'Appointments': 'ਅਪਾਇੰਟਮੈਂਟ', 'Medicines': 'ਦਵਾਈਆਂ', 'Telemedicine': 'ਟੈਲੀਮੈਡੀਸਿਨ',
        'Patient Portal': 'ਮਰੀਜ਼ ਪੋਰਟਲ', 'Care Plans': 'ਦੇਖਭਾਲ ਯੋਜਨਾਵਾਂ',
        'Analytics': 'ਵਿਸ਼ਲੇਸ਼ਣ', 'My Profile': 'ਮੇਰੀ ਪ੍ਰੋਫਾਈਲ',
        'Organ Donors': 'ਅੰਗ ਦਾਨੀ', 'Diet & Lifestyle': 'ਖੁਰਾਕ ਅਤੇ ਜੀਵਨਸ਼ੈਲੀ',
        'UPI Payment': 'UPI ਭੁਗਤਾਨ', 'Main Menu': 'ਮੁੱਖ ਮੀਨੂ',
        'Digital Health': 'ਡਿਜੀਟਲ ਸਿਹਤ', 'Account': 'ਖਾਤਾ',
        'Call 108 Now': '108 ਹੁਣੇ ਕਾਲ ਕਰੋ', 'Book Ambulance': 'ਐਂਬੂਲੈਂਸ ਬੁੱਕ ਕਰੋ',
        'Blood Group': 'ਖੂਨ ਦਾ ਗਰੁੱਪ', 'City': 'ਸ਼ਹਿਰ',
        'Pay Securely': 'ਸੁਰੱਖਿਅਤ ਭੁਗਤਾਨ ਕਰੋ',
        'Explore More Services': 'ਹੋਰ ਸੇਵਾਵਾਂ ਦੀ ਪੜਚੋਲ ਕਰੋ',
    },
};

// ═══════════════════════════════════════════════
// APPLY TRANSLATIONS to all data-i18n elements
// ═══════════════════════════════════════════════
function applyTranslations(lang) {
    const dict = translations[lang] || {};
    document.querySelectorAll('[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (dict[key] && el.children.length === 0) {
            el.textContent = dict[key];
        }
    });
    document.querySelectorAll('.sidebar-link span[data-i18n]').forEach(span => {
        const key = span.getAttribute('data-i18n');
        if (dict[key]) span.textContent = dict[key];
    });
    document.querySelectorAll('.cross-nav-card span[data-i18n]').forEach(span => {
        const key = span.getAttribute('data-i18n');
        if (dict[key]) span.textContent = dict[key];
    });
    document.documentElement.lang = lang;
    document.querySelectorAll('.sidebar-nav-label[data-i18n]').forEach(el => {
        const key = el.getAttribute('data-i18n');
        if (dict[key]) el.textContent = dict[key];
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
        const key = el.getAttribute('data-i18n-placeholder');
        if (dict[key]) el.placeholder = dict[key];
    });

    // Update chat language label
    const langNames = { en: 'EN', hi: 'हिं', ta: 'த', te: 'తె', bn: 'বাং', mr: 'मरा', kn: 'ಕ', ml: 'മ', gu: 'ગ', pa: 'ਪੰ' };
    const chatLabel = document.getElementById('chatLangLabel');
    if (chatLabel && lang !== 'en') chatLabel.textContent = '· ' + (langNames[lang] || lang.toUpperCase());
    else if (chatLabel) chatLabel.textContent = '';
}

// ─── Full-page dynamic translation using Google Translate API ─────
async function translatePageContent(targetLang) {
    if (targetLang === 'en') return; // English is the base

    // Collect unique text segments from the page (excluding scripts, style, etc.)
    const elements = document.querySelectorAll('p, h1, h2, h3, h4, h5, li, td, th, label, .btn, .badge, .card p, footer p, footer a');
    const uniqueTexts = new Map();

    elements.forEach(el => {
        if (el.children.length === 0 && el.textContent.trim().length > 1) {
            const txt = el.textContent.trim();
            if (!uniqueTexts.has(txt)) uniqueTexts.set(txt, []);
            uniqueTexts.get(txt).push(el);
        }
    });

    // Batch translate (up to 50 items at a time to avoid URL length issues)
    const textArr = [...uniqueTexts.keys()].slice(0, 50);
    if (textArr.length === 0) return;

    try {
        const joined = textArr.join('\n');
        const url = `https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=${targetLang}&dt=t&q=${encodeURIComponent(joined)}`;
        const res = await fetch(url);
        const data = await res.json();
        const translatedJoined = data[0].map(seg => seg[0]).join('');
        const translatedLines = translatedJoined.split('\n');
        textArr.forEach((originalText, idx) => {
            if (translatedLines[idx]) {
                uniqueTexts.get(originalText).forEach(el => {
                    el.textContent = translatedLines[idx];
                });
            }
        });
    } catch (e) {
        console.warn('Page translation failed, using static dictionary', e);
    }
}

function switchLanguage(lang) {
    if (lang) localStorage.setItem('mc_lang', lang);
    applyTranslations(lang || 'en');
    if (lang && lang !== 'en') {
        translatePageContent(lang);
    }
}

// Restore language on every page load
document.addEventListener('DOMContentLoaded', () => {
    const saved = localStorage.getItem('mc_lang') || 'en';
    const sel = document.getElementById('langSwitcher');
    if (sel) sel.value = saved;
    applyTranslations(saved);
    if (saved && saved !== 'en') translatePageContent(saved);

    // Close sign-in modal on overlay click
    document.getElementById('signInModal')?.addEventListener('click', function (e) {
        if (e.target === this) closeSignIn();
    });
});

// ─── Utility ───────────────────────────────────
function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function showAlert(msg, type = 'success') {
    let banner = document.getElementById('alertBanner');
    if (!banner) {
        banner = document.createElement('div');
        banner.id = 'alertBanner';
        banner.className = 'alert-banner';
        document.querySelector('.main-content')?.prepend(banner);
    }
    banner.className = `alert-banner ${type} show`;
    banner.innerHTML = `<i class="fas fa-${type === 'success' ? 'check-circle' : 'exclamation-circle'}"></i> ${msg}`;
    setTimeout(() => banner.classList.remove('show'), 6000);
}

function formatINR(amount) {
    return '₹' + Number(amount).toLocaleString('en-IN');
}

// ─── Tab switcher ──────────────────────────────
function switchTab(btn, tabId, groupClass) {
    document.querySelectorAll(`.${groupClass} .tab-btn`).forEach(b => b.classList.remove('active'));
    document.querySelectorAll(`#${tabId}`)?.forEach(c => { });
    document.querySelectorAll('.tab-content').forEach(c => {
        if ([`tab-donors`, `tab-register`, `tab-blood`, `tab-checker`, `tab-organ`].includes(c.id)) {
            c.classList.remove('active');
        }
    });
    btn.classList.add('active');
    document.getElementById(tabId)?.classList.add('active');
}
