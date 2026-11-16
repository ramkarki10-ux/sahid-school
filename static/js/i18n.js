/**
 * Shahid Smriti Residential Secondary School
 * Lightweight, Full-Stack Multi-Language Localization Engine (NP / EN)
 */
(function() {
    'use strict';

    const STORAGE_KEY = 'sahid_school_lang';

    const translations = {
        np: {
            // Topbar
            phone_label: "फोन:",
            notice_board: "सूचना बोर्ड:",
            super_admin: "सुपर एडमिन",
            mobile_app: "मोबाइल एप",
            download: "डाउनलोड",
            signup: "दर्ता (Sign Up)",
            account_approval: "एकाउन्ट Approval",
            dashboard: "ड्यासबोर्ड",
            staff_login: "कर्मचारी लगइन",
            parent_portal: "अभिभावक पोर्टल",

            // Branding
            school_name: "सहिद स्मृति आवासीय माध्यमिक विद्यालय",
            school_subname: "Shahid Smriti Residential Secondary School",
            school_tagline: "गुणस्तरीय शिक्षा र आवासीय सुविधायुक्त नमुना विद्यालय, इटहरी–१९, सुनसरी",
            established: "स्थापना: २०६६",
            address_short: "इटहरी–१९, सुनसरी",

            // Nav Menus
            home: "गृहपृष्ठ",
            news_feed: "न्युज फिड",
            about_us: "हाम्रो विद्यालय",
            administration: "विद्यालय प्रशासन",
            smc: "व्यवस्थापन समिति",
            trustee: "गुठियार समिति",
            teachers: "शिक्षकहरु",
            leadership: "प्रधानाध्यापक तथा नेतृत्व",
            admin_structure: "समग्र प्रशासनिक संरचना",
            academics: "शैक्षिक कार्यक्रम",
            action_plan: "वार्षिक कार्ययोजना",
            academic_calendar: "शैक्षिक क्यालेण्डर",
            all_academics: "समग्र शैक्षिक कार्यक्रम",
            students: "विद्यार्थी",
            online_admission: "अनलाइन भर्ना (Admission)",
            exam_results: "परीक्षा नतिजा (Results)",
            alumni: "पुर्व विद्यार्थी (Alumni)",
            leave_application: "अनलाइन बिदा निवेदन",
            attendance_portal: "दैनिक हाजिरी पोर्टल",
            homework: "दैनिक गृहकार्य (Homework)",
            students_directory: "विद्यार्थी विवरण",
            bus_users: "विद्यालय bus प्रयोगकर्ता",
            citizen_charter: "नागरिक वडापत्र",
            gallery: "ग्यालेरी",
            photo_gallery: "फोटो ग्यालेरी",
            video_gallery: "भिडियो ग्यालेरी",
            support_partners: "सहयोग / साझेदार",
            contact: "सम्पर्क",
            all_menus: "सम्पूर्ण मेनु",

            // Common UI
            search: "खोज्नुहोस्",
            search_placeholder: "यहाँ खोज्नुहोस्...",
            filter: "फिल्टर",
            all: "सबै",
            add_new: "+ नयाँ थप्नुहोस्",
            edit: "सम्पादन",
            delete: "हटाउने",
            save: "सुरक्षित गर्नुहोस्",
            saving: "सुरक्षित गरिँदैछ...",
            cancel: "रद्द गर्नुहोस्",
            import_excel: "Excel/CSV आयात",
            download_template: "Template डाउनलोड",
            export_excel: "Excel निर्यात",
            actions: "कार्य",
            status: "स्थिति",
            active: "सक्रिय",
            inactive: "निष्क्रिय",
            sn: "क्र.सं.",
            remarks: "कैफियत",
            page: "पृष्ठ",
            of: "/",
            total: "कुल",
            records: "जना",
            showing: "देखाउँदै",
            prev: "अघिल्लो",
            next: "पछिल्लो",
            close: "बन्द गर्नुहोस्",
            success: "सफल भयो",
            error: "त्रुटि भयो",

            // Bus Users Page Specific
            bus_users_title: "विद्यालय bus प्रयोगकर्ता (School Bus Users)",
            bus_users_sub: "सहिद स्मृति आवासीय माध्यमिक विद्यालयका बस प्रयोग गर्ने सम्पूर्ण विद्यार्थीहरूको सूची तथा बस रुट व्यवस्थापन",
            bus_user_name: "विद्यार्थीको नाम, थर",
            bus_user_address: "ठेगाना",
            bus_user_guardian: "अभिभावकको नाम, थर",
            bus_user_contact: "सम्पर्क नम्बर",
            bus_user_stop: "वस चढ्ने स्थान (Bus Stop)",
            bus_user_bus: "बस नम्बर / रुट",
            bus_user_class: "कक्षा (Class)",
            bus_add_btn: "+ नयाँ प्रयोगकर्ता थप्नुहोस्",
            bus_search_placeholder: "विद्यार्थीको नाम वा बस स्टप खोज्नुहोस्...",
            all_bus_stops: "सबै बस स्टप (All Stops)",
            all_bus_routes: "सबै बस रुट (All Routes)",
            import_title: "Excel वा CSV बाट विद्यार्थी बस विवरण आयात गर्नुहोस्",
            import_note: "तपाईंले .xlsx वा .csv फाइल सिधै अपलोड गर्न सक्नुहुन्छ।"
        },
        en: {
            // Topbar
            phone_label: "Phone:",
            notice_board: "Notice Board:",
            super_admin: "Super Admin",
            mobile_app: "Mobile App",
            download: "Download",
            signup: "Sign Up",
            account_approval: "Account Approval",
            dashboard: "Dashboard",
            staff_login: "Staff Login",
            parent_portal: "Parent Portal",

            // Branding
            school_name: "Shahid Smriti Residential Secondary School",
            school_subname: "सहिद स्मृति आवासीय माध्यमिक विद्यालय",
            school_tagline: "A Model School with Quality Education & Residential Facilities, Itahari-19, Sunsari",
            established: "Est: 2009 AD (2066 BS)",
            address_short: "Itahari-19, Sunsari",

            // Nav Menus
            home: "Home",
            news_feed: "News Feed",
            about_us: "About Us",
            administration: "Administration",
            smc: "Management Committee",
            trustee: "Trustee Committee",
            teachers: "Teachers & Faculty",
            leadership: "Leadership",
            admin_structure: "Administration Structure",
            academics: "Academics",
            action_plan: "Action Plan",
            academic_calendar: "Academic Calendar",
            all_academics: "All Academics",
            students: "Students",
            online_admission: "Online Admission",
            exam_results: "Exam Results",
            alumni: "Alumni",
            leave_application: "Leave Application",
            attendance_portal: "Attendance Portal",
            homework: "Daily Homework",
            students_directory: "Students Directory",
            bus_users: "School Bus Users",
            citizen_charter: "Citizen Charter",
            gallery: "Gallery",
            photo_gallery: "Photo Gallery",
            video_gallery: "Video Gallery",
            support_partners: "Support & Partners",
            contact: "Contact",
            all_menus: "All Menus",

            // Common UI
            search: "Search",
            search_placeholder: "Search here...",
            filter: "Filter",
            all: "All",
            add_new: "+ Add New",
            edit: "Edit",
            delete: "Delete",
            save: "Save Changes",
            saving: "Saving...",
            cancel: "Cancel",
            import_excel: "Excel/CSV Import",
            download_template: "Download Template",
            export_excel: "Export to Excel",
            actions: "Actions",
            status: "Status",
            active: "Active",
            inactive: "Inactive",
            sn: "S.N.",
            remarks: "Remarks",
            page: "Page",
            of: "of",
            total: "Total",
            records: "Records",
            showing: "Showing",
            prev: "Previous",
            next: "Next",
            close: "Close",
            success: "Success",
            error: "Error",

            // Bus Users Page Specific
            bus_users_title: "School Bus Users Management",
            bus_users_sub: "Directory of all students using school transport, boarding points and bus route management",
            bus_user_name: "Student's Full Name",
            bus_user_address: "Address",
            bus_user_guardian: "Guardian's Name",
            bus_user_contact: "Contact Number",
            bus_user_stop: "Bus Stop / Boarding Point",
            bus_user_bus: "Bus No. / Route",
            bus_user_class: "Class / Grade",
            bus_add_btn: "+ Add Bus Student",
            bus_search_placeholder: "Search by student name or bus stop...",
            all_bus_stops: "All Bus Stops",
            all_bus_routes: "All Bus Routes",
            import_title: "Bulk Import Bus Users from Excel or CSV",
            import_note: "Upload an Excel (.xlsx, .xls) or CSV (.csv) file directly."
        }
    };

    // Mapping table for dynamic text replacement on nav links and headers
    const navTextPairs = [
        ["गृहपृष्ठ", "Home"],
        ["न्युज फिड (फेसबुक शैली)", "News Feed (FB Style)"],
        ["न्युज फिड", "News Feed"],
        ["हाम्रो विद्यालय", "About Us"],
        ["विद्यालय प्रशासन", "Administration"],
        ["व्यवस्थापन समिति", "Management Committee"],
        ["गुठियार समिति", "Trustee Committee"],
        ["शिक्षकहरु", "Teachers & Faculty"],
        ["शिक्षक शिक्षिका विवरण (हाम्रा शिक्षक)", "Teachers Directory"],
        ["प्रधानाध्यापक तथा नेतृत्व", "Principal & Leadership"],
        ["समग्र प्रशासनिक संरचना", "Administrative Structure"],
        ["शैक्षिक कार्यक्रम", "Academics"],
        ["वार्षिक कार्ययोजना", "Annual Action Plan"],
        ["शैक्षिक क्यालेण्डर", "Academic Calendar"],
        ["समग्र शैक्षिक कार्यक्रम", "All Academic Programs"],
        ["विद्यार्थी", "Students"],
        ["अनलाइन भर्ना (Admission)", "Online Admission"],
        ["अनलाइन भर्ना", "Online Admission"],
        ["परीक्षा नतिजा (Results)", "Exam Results"],
        ["परीक्षा नतिजा", "Exam Results"],
        ["पुर्व विद्यार्थी (Alumni)", "Alumni"],
        ["पूर्व विद्यार्थी (Alumni)", "Alumni"],
        ["अनलाइन बिदा निवेदन", "Leave Application"],
        ["बिदा निवेदन", "Leave Application"],
        ["दैनिक हाजिरी पोर्टल", "Daily Attendance Portal"],
        ["दैनिक हाजिरी (Daily Attendance)", "Daily Attendance"],
        ["दैनिक हाजिरी", "Daily Attendance"],
        ["दैनिक गृहकार्य (Homework)", "Daily Homework"],
        ["दैनिक गृहकार्य", "Daily Homework"],
        ["विद्यार्थी विवरण", "Students Directory"],
        ["विद्यार्थी सूची", "Students List"],
        ["विद्यालय bus प्रयोगकर्ता", "School Bus Users"],
        ["बस प्रयोगकर्ता (Bus Users)", "Bus Users"],
        ["बस प्रयोगकर्ता", "Bus Users"],
        ["नागरिक वडापत्र", "Citizen Charter"],
        ["ग्यालेरी", "Gallery"],
        ["फोटो ग्यालेरी", "Photo Gallery"],
        ["भिडियो ग्यालेरी", "Video Gallery"],
        ["सहयोग / साझेदार", "Support & Partners"],
        ["सहयोग/साझेदार", "Support & Partners"],
        ["सम्पर्क", "Contact"],
        ["मोबाइल एप", "Mobile App"],
        ["सुपर एडमिन", "Super Admin"],
        ["कर्मचारी लगइन", "Staff Login"],
        ["अभिभावक पोर्टल", "Parent Portal"],
        ["दर्ता (Sign Up)", "Sign Up"],
        ["डाउनलोड", "Download"],
        ["सम्पूर्ण मेनु", "All Menus"],
        ["छात्रावास (Hostel)", "Hostel"],
        ["यातायात (Transport)", "Transport"],
        ["सुविधा (Facilities)", "Facilities"],
        ["कागजात प्रमाणीकरण", "Document Verification"],
        ["कक्षा बढुवा (Promotion)", "Class Promotion"],
        ["Excel आयात (Import)", "Excel Import"],
        ["सूचना", "Notices"],
        ["सूचना व्यवस्थापन", "Notices Management"],
        ["समाचार", "News"],
        ["प्रकाशन (Publications)", "Publications"],
        ["प्रकाशन", "Publications"],
        ["भिडियो", "Videos"],
        ["उपलब्धि", "Achievements"]
    ];

    class SchoolI18n {
        constructor() {
            this.currentLang = this.getStoredLanguage();
            this.translations = translations;
            this.initialized = false;
        }

        getStoredLanguage() {
            try {
                const stored = localStorage.getItem(STORAGE_KEY);
                if (stored === 'en' || stored === 'np') return stored;
            } catch(e) {}
            return 'np';
        }

        setLanguage(lang) {
            if (lang !== 'np' && lang !== 'en') lang = 'np';
            this.currentLang = lang;

            try {
                localStorage.setItem(STORAGE_KEY, lang);
                document.cookie = `sahid_lang=${lang}; path=/; max-age=31536000; SameSite=Lax`;
            } catch(e) {}

            document.documentElement.setAttribute('lang', lang);

            this.updateSwitcherButtons();
            this.applyTranslations();

            // Dispatch event for any custom listeners
            try {
                document.dispatchEvent(new CustomEvent('schoolLanguageChanged', { detail: { lang } }));
            } catch(e) {}
        }

        updateSwitcherButtons() {
            const isEn = this.currentLang === 'en';

            // Desktop Topbar Buttons
            const btnNP = document.getElementById('langBtnNP');
            const btnEN = document.getElementById('langBtnEN');
            if (btnNP && btnEN) {
                if (isEn) {
                    btnNP.className = "px-2 py-0.5 bg-instBlue text-slate-300 hover:text-white transition cursor-pointer";
                    btnEN.className = "px-2 py-0.5 bg-instGold text-white font-black shadow-sm transition cursor-pointer";
                } else {
                    btnNP.className = "px-2 py-0.5 bg-instGold text-white font-black shadow-sm transition cursor-pointer";
                    btnEN.className = "px-2 py-0.5 bg-instBlue text-slate-300 hover:text-white transition cursor-pointer";
                }
            }

            // Mobile Drawer Buttons
            const btnNP_m = document.getElementById('langBtnNP_mobile');
            const btnEN_m = document.getElementById('langBtnEN_mobile');
            if (btnNP_m && btnEN_m) {
                if (isEn) {
                    btnNP_m.className = "px-3 py-1 bg-instBlue text-slate-300 hover:text-white rounded transition text-xs";
                    btnEN_m.className = "px-3 py-1 bg-amber-400 text-slate-950 font-bold rounded shadow transition text-xs";
                } else {
                    btnNP_m.className = "px-3 py-1 bg-amber-400 text-slate-950 font-bold rounded shadow transition text-xs";
                    btnEN_m.className = "px-3 py-1 bg-instBlue text-slate-300 hover:text-white rounded transition text-xs";
                }
            }

            // Admin Header Buttons
            const btnNP_a = document.getElementById('langBtnNP_admin');
            const btnEN_a = document.getElementById('langBtnEN_admin');
            if (btnNP_a && btnEN_a) {
                if (isEn) {
                    btnNP_a.className = "px-2 py-0.5 bg-slate-100 text-slate-600 hover:text-slate-900 transition text-[11px] font-bold";
                    btnEN_a.className = "px-2 py-0.5 bg-instBlue text-white font-bold transition text-[11px] shadow-sm";
                } else {
                    btnNP_a.className = "px-2 py-0.5 bg-instBlue text-white font-bold transition text-[11px] shadow-sm";
                    btnEN_a.className = "px-2 py-0.5 bg-slate-100 text-slate-600 hover:text-slate-900 transition text-[11px] font-bold";
                }
            }
        }

        t(key) {
            const dict = this.translations[this.currentLang] || this.translations.np;
            return dict[key] || key;
        }

        applyTranslations() {
            const lang = this.currentLang;
            const dict = this.translations[lang] || this.translations.np;

            // 1. data-i18n attributes
            document.querySelectorAll('[data-i18n]').forEach(el => {
                const key = el.getAttribute('data-i18n');
                if (dict[key]) {
                    el.innerText = dict[key];
                }
            });

            // 2. data-i18n-html attributes
            document.querySelectorAll('[data-i18n-html]').forEach(el => {
                const key = el.getAttribute('data-i18n-html');
                if (dict[key]) {
                    el.innerHTML = dict[key];
                }
            });

            // 3. data-i18n-placeholder attributes
            document.querySelectorAll('[data-i18n-placeholder]').forEach(el => {
                const key = el.getAttribute('data-i18n-placeholder');
                if (dict[key]) {
                    el.setAttribute('placeholder', dict[key]);
                }
            });

            // 4. Auto translate navigation menu spans and links
            const toEn = lang === 'en';
            navTextPairs.forEach(([npText, enText]) => {
                const from = toEn ? npText : enText;
                const to = toEn ? enText : npText;
                if (!from || !to) return;

                // Target nav links, spans, buttons
                const xpath = `//nav//span[text()='${from}'] | //nav//a[text()='${from}'] | //header//span[text()='${from}'] | //div[contains(@class,'nav-dropdown-box')]//span[text()='${from}'] | //div[@id='drawerPanel']//span[text()='${from}'] | //aside//span[text()='${from}']`;
                try {
                    const result = document.evaluate(xpath, document, null, XPathResult.UNORDERED_NODE_SNAPSHOT_TYPE, null);
                    for (let i = 0; i < result.snapshotLength; i++) {
                        result.snapshotItem(i).innerText = to;
                    }
                } catch(e) {}
            });
        }

        init() {
            this.updateSwitcherButtons();
            if (this.currentLang === 'en') {
                this.applyTranslations();
            }
            this.initialized = true;
        }
    }

    window.SchoolI18n = new SchoolI18n();

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => window.SchoolI18n.init());
    } else {
        window.SchoolI18n.init();
    }
})();
