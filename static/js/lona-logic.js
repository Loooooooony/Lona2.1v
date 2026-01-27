const LonaLogic = {
    // Translations
    lang: {
        'ar': {
            // Personality: Iraqi Dialect
            'save_btn': 'حفظ يا بطل',
            'delete_btn': 'احذفه وخلصنا 🗑️',
            'error_msg': 'يبووو صار غلط 😭',
            'success_msg': 'عاشت ايدك 💃🏻',
            'welcome_back': 'هلا والله بالنور كله!',

            // Sidebar
            'dashboard_title': 'مركز القيادة ✨',
            'game_studio': 'استوديو الألعاب',
            'moderation': 'التحكم والمشرفين',

            // Select Server
            'select_title': 'LonaBot Dashboard',
            'select_subtitle': 'تحكم بسيرفرك بذكاء وأناقة. اختر السيرفر للبدء.',
            'manage_server': 'إدارة السيرفر',

            // Dashboard Main
            'dash_header': 'مركز القيادة 🚀',
            'system_active': 'نظام التحليل المباشر يعمل',
            'total_members': 'الإجمالي',
            'members_label': 'عضو بالسيرفر',
            'active_now': 'نشط الآن',
            'online_label': 'متصل حالياً',
            'messages_stat': 'الرسائل',
            'messages_label': 'خلال الفترة',
            'channels_stat': 'القنوات',
            'channels_label': 'روم وقناة',
            'chart_title': 'تحليل النشاط العام',
            'top_chatters': 'ملوك التفاعل (Top 5)',
            'no_data': 'لا توجد بيانات كافية!'
        },
        'en': {
            // Personality: Gen-Z / Sassy
            'save_btn': 'Slay & Save ✨',
            'delete_btn': 'Yeet it 🗑️',
            'error_msg': 'Oof! Big Yikes 😭',
            'success_msg': 'Slayed it! 💃🏻',
            'welcome_back': 'Welcome back Bestie!',

            // Sidebar
            'dashboard_title': 'Command Center 💅🏻',
            'game_studio': 'Game Studio',
            'moderation': 'Moderation',

            // Select Server
            'select_title': 'LonaBot Dashboard',
            'select_subtitle': 'Control your server with style. Pick one to start.',
            'manage_server': 'Manage Server',

            // Dashboard Main
            'dash_header': 'Command Center 🚀',
            'system_active': 'Live Analytics System Active',
            'total_members': 'Total Members',
            'members_label': 'Members',
            'active_now': 'Active Now',
            'online_label': 'Online',
            'messages_stat': 'Messages',
            'messages_label': 'In Period',
            'channels_stat': 'Channels',
            'channels_label': 'Channels',
            'chart_title': 'General Activity Analysis',
            'top_chatters': 'Top Chatters (Top 5)',
            'no_data': 'Not enough data!'
        }
    },

    init: function() {
        // Load Theme
        const savedTheme = localStorage.getItem('lona-theme') || 'midnight';
        this.applyTheme(savedTheme);

        // Load Lang
        const savedLang = localStorage.getItem('lona-lang') || 'ar';
        this.applyLang(savedLang);

        // Bind Listeners
        this.bindEvents();
    },

    applyTheme: function(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        const icon = document.getElementById('theme-icon');
        if(icon) {
            icon.className = theme === 'pink' ? 'fas fa-moon' : 'fas fa-sun';
        }
    },

    applyLang: function(lang) {
        document.documentElement.setAttribute('lang', lang);
        document.documentElement.setAttribute('dir', lang === 'ar' ? 'rtl' : 'ltr');
        this.updateText(lang);
    },

    toggleTheme: function() {
        const current = document.documentElement.getAttribute('data-theme') || 'midnight';
        const next = current === 'pink' ? 'midnight' : 'pink';
        this.applyTheme(next);
        localStorage.setItem('lona-theme', next);
    },

    toggleLang: function() {
        const current = document.documentElement.getAttribute('lang') || 'ar';
        const next = current === 'en' ? 'ar' : 'en';
        this.applyLang(next);
        localStorage.setItem('lona-lang', next);
    },

    updateText: function(lang) {
        document.querySelectorAll('[data-lang-key]').forEach(el => {
            const key = el.getAttribute('data-lang-key');
            if (this.lang[lang][key]) {
                el.innerText = this.lang[lang][key];
            }
        });

        // Dynamic Button Updates (if any specific IDs)
        // Example: Update save buttons if they have class 'lona-btn-save'
        /*
        document.querySelectorAll('.lona-btn-primary').forEach(btn => {
            if(btn.innerText.includes('حفظ') || btn.innerText.includes('Save')) {
                // This is risky without specific IDs, so we rely on data-lang-key mostly.
            }
        });
        */
    },

    bindEvents: function() {
        const themeBtn = document.getElementById('theme-toggle-btn');
        if(themeBtn) themeBtn.onclick = () => this.toggleTheme();

        const langBtn = document.getElementById('lang-toggle-btn');
        if(langBtn) langBtn.onclick = () => this.toggleLang();
    }
};

document.addEventListener('DOMContentLoaded', () => {
    LonaLogic.init();
});
