/**
 * Dynamic Cascading Multi-Select Teaching Subject (अध्यापन विषय) Component
 * Supports:
 * - 4 Educational Levels: प्रारम्भिक बालविकास, प्राथमिक तह, आधारभूत तह, माध्यमिक तह
 * - Dynamic subject checklist per level
 * - Multi-select checkboxes
 * - Custom 'अन्य' subject addition ("थप विषय लेख्न मिल्ने") with tag deletion
 * - Devanagari typography, search filter, select all / clear
 * - Two-way sync with hidden input for seamless form submission and editing
 */

(function(window) {
    'use strict';

    const LEVEL_SUBJECTS = {
        'प्रारम्भिक बालविकास': [
            'शारीरिक विकास र स्वास्थ्य (Physical Development & Health)',
            'संज्ञानात्मक तथा बौद्धिक विकास (Cognitive Development - रङ, आकार, सङ्ख्या र अक्षरको प्रारम्भिक पहिचान)',
            'भाषा तथा सञ्चार विकास (Language & Communication - मौखिक नेपाली तथा अंग्रेजी भाषा, कविता, कथा)',
            'सामाजिक तथा भावनात्मक विकास (Social & Emotional Development)',
            'सिर्जनात्मक कला (Creative Arts - चित्रकला, हस्तकला, सङ्गीत र नाटक)'
        ],
        'प्राथमिक तह': [
            'नेपाली',
            'अंग्रेजी (English)',
            'गणित (Mathematics)',
            'हाम्रो सेरोफेरो',
            'विज्ञान तथा प्रविधि (Science and Technology)',
            'सामाजिक अध्ययन तथा मानव मूल्य शिक्षा (Social Studies and Human Values Education)',
            'स्वास्थ्य, शारीरिक तथा सिर्जनात्मक कला (Health, Physical and Creative Arts)',
            'मातृभाषा / स्थानीय विषय'
        ],
        'आधारभूत तह': [
            'नेपाली',
            'अंग्रेजी (English)',
            'गणित (Mathematics)',
            'विज्ञान तथा प्रविधि (Science and Technology)',
            'सामाजिक अध्ययन तथा नागरिक शिक्षा (Social Studies and Civic Education)',
            'स्वास्थ्य तथा शारीरिक शिक्षा (Health and Physical Education)',
            'नैतिक शिक्षा (Moral Education)',
            'स्थानीय विषय / मातृभाषा',
            'व्यवसायिक शिक्षा / सूचना प्रविधि (ICT)'
        ],
        'माध्यमिक तह': [
            'नेपाली',
            'अंग्रेजी (English)',
            'गणित (Mathematics)',
            'विज्ञान तथा प्रविधि (Science and Technology)',
            'सामाजिक अध्ययन तथा नागरिक शिक्षा (Social Studies and Civic Education)',
            'ऐच्छिक गणित (Opt. Mathematics)',
            'अर्थशास्त्र (Economics)',
            'लेखाशास्त्र (Accounting)',
            'कृषि',
            'कम्प्युटर विज्ञान (Computer Science)'
        ]
    };

    function normalizeLevel(lvl) {
        if (!lvl) return 'माध्यमिक तह';
        const s = String(lvl).trim();
        if (s.includes('बालविकास') || s.includes('ECCD') || s.includes('ECD') || s.includes('Pre-Primary')) {
            return 'प्रारम्भिक बालविकास';
        }
        if (s.includes('प्राथमिक') || s.includes('Primary')) {
            return 'प्राथमिक तह';
        }
        if (s.includes('आधारभूत') || s.includes('निम्न माध्यमिक') || s.includes('नि.मा.वि') || s.includes('Basic')) {
            return 'आधारभूत तह';
        }
        if (s.includes('माध्यमिक') || s.includes('मा.वि') || s.includes('Secondary')) {
            return 'माध्यमिक तह';
        }
        return 'माध्यमिक तह';
    }

    const instances = {};

    class SubjectPicker {
        constructor(config) {
            this.id = config.id;
            this.levelSelectId = config.levelSelectId;
            this.hiddenInputId = config.hiddenInputId;
            this.containerId = config.containerId;
            
            this.selectedSubjects = [];
            this.currentLevel = 'माध्यमिक तह';

            this.levelSelect = document.getElementById(this.levelSelectId);
            this.hiddenInput = document.getElementById(this.hiddenInputId);
            this.container = document.getElementById(this.containerId);

            if (!this.container) return;

            this.renderHTML();
            this.bindEvents();
            this.updateLevel(this.levelSelect ? this.levelSelect.value : 'माध्यमिक तह');
        }

        renderHTML() {
            this.container.innerHTML = `
                <div class="space-y-1.5 relative select-none" id="${this.id}_wrapper">
                    <div class="flex items-center justify-between">
                        <label class="block font-semibold text-slate-700 text-xs">
                            अध्यापन विषय (Teaching Subject) *
                        </label>
                        <span id="${this.id}_counter" class="text-[10px] text-instBlue font-bold bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full">
                            ० विषय छानियो
                        </span>
                    </div>

                    <!-- Trigger Box with Selected Badges -->
                    <div id="${this.id}_trigger" class="min-h-[38px] p-1.5 bg-white border border-slate-300 rounded-lg cursor-pointer flex items-center justify-between gap-1.5 shadow-sm hover:border-slate-400 focus-within:ring-2 focus-within:ring-instBlue focus-within:border-instBlue transition">
                        <div id="${this.id}_badges" class="flex flex-wrap gap-1 items-center flex-1">
                            <span class="text-slate-400 text-xs italic px-1" id="${this.id}_placeholder">विषयहरू छान्नुहोस् वा तल थप्नुहोस्...</span>
                        </div>
                        <div class="flex items-center gap-1 text-slate-400 pr-1 flex-shrink-0">
                            <i data-lucide="chevron-down" class="w-4 h-4 transition-transform duration-150" id="${this.id}_arrow"></i>
                        </div>
                    </div>

                    <!-- Dropdown Checklist Panel -->
                    <div id="${this.id}_dropdown" class="hidden absolute z-50 left-0 right-0 top-full mt-1.5 bg-white border border-slate-300 rounded-xl shadow-2xl p-3 space-y-2.5 max-h-[340px] overflow-hidden flex flex-col animate-in fade-in zoom-in-95 duration-100">
                        <!-- Dropdown Header -->
                        <div class="flex items-center justify-between border-b pb-2">
                            <div class="flex items-center gap-1.5">
                                <span class="w-2 h-2 rounded-full bg-instBlue"></span>
                                <span class="text-[11px] font-bold text-slate-700" id="${this.id}_level_title">माध्यमिक तहका विषयहरू:</span>
                            </div>
                            <div class="flex items-center gap-2">
                                <button type="button" id="${this.id}_btn_select_all" class="text-[10px] text-instBlue hover:underline font-semibold">सबै छान्नुहोस्</button>
                                <span class="text-slate-300">|</span>
                                <button type="button" id="${this.id}_btn_clear_all" class="text-[10px] text-rose-600 hover:underline font-semibold">खाली गर्नुहोस्</button>
                            </div>
                        </div>

                        <!-- Search Filter -->
                        <div class="relative">
                            <input type="text" id="${this.id}_search" placeholder="विषय खोज्नुहोस्..." class="w-full pl-7 pr-3 py-1 bg-slate-50 border border-slate-200 rounded-lg text-xs focus:bg-white focus:outline-none focus:ring-1 focus:ring-instBlue">
                            <i data-lucide="search" class="w-3.5 h-3.5 text-slate-400 absolute left-2 top-2"></i>
                        </div>

                        <!-- Checkbox Options List -->
                        <div id="${this.id}_options_list" class="space-y-1 overflow-y-auto max-h-44 pr-1 text-xs">
                            <!-- Populated dynamically -->
                        </div>

                        <!-- Custom 'अन्य' Subject Input Feature -->
                        <div class="pt-2 border-t border-slate-100 bg-slate-50 -mx-3 -mb-3 p-2.5 rounded-b-xl space-y-1.5">
                            <label class="block text-[10px] font-bold text-slate-600">
                                अन्य (सूचीमा नभएको थप विषय लेख्नुहोस्):
                            </label>
                            <div class="flex gap-1.5">
                                <input type="text" id="${this.id}_custom_input" placeholder="जस्तै: भौतिक विज्ञान, रोबोटिक्स..." class="flex-1 px-2.5 py-1 text-xs bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-instBlue">
                                <button type="button" id="${this.id}_btn_add_custom" class="px-3 py-1 bg-instBlue hover:bg-instBlue-dark text-white rounded-lg text-xs font-bold shadow-sm transition inline-flex items-center gap-1">
                                    <i data-lucide="plus" class="w-3 h-3 text-instGold"></i>
                                    <span>थप्नुहोस्</span>
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            if (window.lucide) lucide.createIcons();
        }

        bindEvents() {
            const trigger = document.getElementById(`${this.id}_trigger`);
            const dropdown = document.getElementById(`${this.id}_dropdown`);
            const arrow = document.getElementById(`${this.id}_arrow`);
            const search = document.getElementById(`${this.id}_search`);
            const customInput = document.getElementById(`${this.id}_custom_input`);
            const btnAddCustom = document.getElementById(`${this.id}_btn_add_custom`);
            const btnSelectAll = document.getElementById(`${this.id}_btn_select_all`);
            const btnClearAll = document.getElementById(`${this.id}_btn_clear_all`);

            // Toggle dropdown
            if (trigger) {
                trigger.addEventListener('click', (e) => {
                    // Prevent toggle if clicking a delete badge button
                    if (e.target.closest(`.${this.id}_remove_btn`)) return;
                    const isHidden = dropdown.classList.contains('hidden');
                    if (isHidden) {
                        this.openDropdown();
                    } else {
                        this.closeDropdown();
                    }
                });
            }

            // Close when clicking outside
            document.addEventListener('click', (e) => {
                const wrapper = document.getElementById(`${this.id}_wrapper`);
                if (wrapper && !wrapper.contains(e.target)) {
                    this.closeDropdown();
                }
            });

            // Level change listener on associated select
            if (this.levelSelect) {
                this.levelSelect.addEventListener('change', (e) => {
                    this.updateLevel(e.target.value);
                });
            }

            // Search filter
            if (search) {
                search.addEventListener('input', (e) => {
                    const q = e.target.value.toLowerCase().trim();
                    const items = document.querySelectorAll(`.${this.id}_option_item`);
                    items.forEach(el => {
                        const text = el.textContent.toLowerCase();
                        el.style.display = text.includes(q) ? 'flex' : 'none';
                    });
                });
            }

            // Add custom subject
            const handleAddCustom = () => {
                if (!customInput) return;
                const val = customInput.value.trim();
                if (!val) return;
                this.addSubject(val);
                customInput.value = '';
                customInput.focus();
            };

            if (btnAddCustom) btnAddCustom.addEventListener('click', handleAddCustom);
            if (customInput) {
                customInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddCustom();
                    }
                });
            }

            // Select All & Clear All
            if (btnSelectAll) {
                btnSelectAll.addEventListener('click', () => {
                    const available = LEVEL_SUBJECTS[this.currentLevel] || [];
                    available.forEach(s => {
                        if (!this.selectedSubjects.includes(s)) {
                            this.selectedSubjects.push(s);
                        }
                    });
                    this.syncUI();
                });
            }

            if (btnClearAll) {
                btnClearAll.addEventListener('click', () => {
                    this.selectedSubjects = [];
                    this.syncUI();
                });
            }
        }

        openDropdown() {
            const dropdown = document.getElementById(`${this.id}_dropdown`);
            const arrow = document.getElementById(`${this.id}_arrow`);
            if (dropdown) dropdown.classList.remove('hidden');
            if (arrow) arrow.style.transform = 'rotate(180deg)';
            const search = document.getElementById(`${this.id}_search`);
            if (search) {
                search.value = '';
                search.focus();
            }
            if (window.lucide) lucide.createIcons();
        }

        closeDropdown() {
            const dropdown = document.getElementById(`${this.id}_dropdown`);
            const arrow = document.getElementById(`${this.id}_arrow`);
            if (dropdown) dropdown.classList.add('hidden');
            if (arrow) arrow.style.transform = 'rotate(0deg)';
        }

        updateLevel(rawLevel) {
            this.currentLevel = normalizeLevel(rawLevel);
            
            // Sync level select value if needed
            if (this.levelSelect && this.levelSelect.value !== this.currentLevel) {
                const opt = Array.from(this.levelSelect.options).find(o => normalizeLevel(o.value) === this.currentLevel);
                if (opt) this.levelSelect.value = opt.value;
            }

            const titleEl = document.getElementById(`${this.id}_level_title`);
            if (titleEl) {
                titleEl.innerText = `${this.currentLevel}का विषयहरू:`;
            }

            this.renderOptionsList();
            this.syncUI();
        }

        renderOptionsList() {
            const listEl = document.getElementById(`${this.id}_options_list`);
            if (!listEl) return;

            const subjects = LEVEL_SUBJECTS[this.currentLevel] || [];
            let html = '';

            subjects.forEach((subj, idx) => {
                const isChecked = this.selectedSubjects.includes(subj);
                const optId = `${this.id}_opt_${idx}`;
                html += `
                    <label for="${optId}" class="${this.id}_option_item flex items-center gap-2.5 p-2 rounded-lg hover:bg-blue-50 cursor-pointer transition border border-transparent hover:border-blue-100">
                        <input type="checkbox" id="${optId}" value="${subj.replace(/"/g, '&quot;')}" ${isChecked ? 'checked' : ''} class="${this.id}_checkbox w-4 h-4 text-instBlue rounded border-slate-300 focus:ring-instBlue cursor-pointer">
                        <span class="text-xs text-slate-800 font-medium leading-tight flex-1">${subj}</span>
                    </label>
                `;
            });

            listEl.innerHTML = html;

            // Bind checkbox changes
            const checkboxes = listEl.querySelectorAll(`.${this.id}_checkbox`);
            checkboxes.forEach(cb => {
                cb.addEventListener('change', (e) => {
                    const subj = e.target.value;
                    if (e.target.checked) {
                        this.addSubject(subj);
                    } else {
                        this.removeSubject(subj);
                    }
                });
            });
        }

        addSubject(subj) {
            const s = subj.trim();
            if (!s) return;
            if (!this.selectedSubjects.includes(s)) {
                this.selectedSubjects.push(s);
            }
            this.syncUI();
        }

        removeSubject(subj) {
            this.selectedSubjects = this.selectedSubjects.filter(item => item !== subj);
            this.syncUI();
        }

        syncUI() {
            // 1. Update hidden input with comma separated string
            const finalStr = this.selectedSubjects.join(', ');
            if (this.hiddenInput) {
                this.hiddenInput.value = finalStr;
            }

            // 2. Update badges inside trigger box
            const badgesContainer = document.getElementById(`${this.id}_badges`);
            if (badgesContainer) {
                if (this.selectedSubjects.length === 0) {
                    badgesContainer.innerHTML = `<span class="text-slate-400 text-xs italic px-1" id="${this.id}_placeholder">विषयहरू छान्नुहोस् वा तल थप्नुहोस्...</span>`;
                } else {
                    let badgesHtml = '';
                    this.selectedSubjects.forEach(s => {
                        const shortName = s.split('(')[0].trim();
                        badgesHtml += `
                            <span class="inline-flex items-center gap-1 bg-blue-50 text-instBlue border border-blue-200 px-2 py-0.5 rounded-md text-[11px] font-semibold shadow-xs">
                                <span title="${s.replace(/"/g, '&quot;')}">${shortName || s}</span>
                                <button type="button" class="${this.id}_remove_btn text-blue-400 hover:text-rose-600 font-bold ml-0.5 text-xs focus:outline-none" data-subject="${s.replace(/"/g, '&quot;')}">×</button>
                            </span>
                        `;
                    });
                    badgesContainer.innerHTML = badgesHtml;

                    // Bind delete badge buttons
                    badgesContainer.querySelectorAll(`.${this.id}_remove_btn`).forEach(btn => {
                        btn.addEventListener('click', (e) => {
                            e.stopPropagation();
                            const toRemove = btn.getAttribute('data-subject');
                            this.removeSubject(toRemove);
                        });
                    });
                }
            }

            // 3. Update counter badge
            const counter = document.getElementById(`${this.id}_counter`);
            if (counter) {
                const count = this.selectedSubjects.length;
                counter.innerText = count === 0 ? '० विषय छानियो' : `${count} विषय छानियो`;
                if (count > 0) {
                    counter.className = 'text-[10px] text-emerald-700 font-bold bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full';
                } else {
                    counter.className = 'text-[10px] text-instBlue font-bold bg-blue-50 border border-blue-200 px-2 py-0.5 rounded-full';
                }
            }

            // 4. Update checkboxes in options list
            const checkboxes = document.querySelectorAll(`.${this.id}_checkbox`);
            checkboxes.forEach(cb => {
                cb.checked = this.selectedSubjects.includes(cb.value);
            });
        }

        setValues(level, subjectsString) {
            this.currentLevel = normalizeLevel(level);
            if (this.levelSelect) {
                const opt = Array.from(this.levelSelect.options).find(o => normalizeLevel(o.value) === this.currentLevel);
                if (opt) this.levelSelect.value = opt.value;
            }

            this.selectedSubjects = [];
            if (subjectsString && typeof subjectsString === 'string') {
                const parts = subjectsString.split(/[,/]/).map(p => p.trim()).filter(Boolean);
                const standardList = LEVEL_SUBJECTS[this.currentLevel] || [];

                parts.forEach(p => {
                    // Check if exact match in standard list
                    const match = standardList.find(s => s === p || s.startsWith(p) || p.startsWith(s));
                    if (match && !this.selectedSubjects.includes(match)) {
                        this.selectedSubjects.push(match);
                    } else if (!this.selectedSubjects.includes(p)) {
                        this.selectedSubjects.push(p);
                    }
                });
            }

            this.updateLevel(this.currentLevel);
        }

        clear() {
            this.selectedSubjects = [];
            this.syncUI();
            this.closeDropdown();
        }

        getValues() {
            return {
                level: this.currentLevel,
                subjects: this.selectedSubjects,
                subjectString: this.selectedSubjects.join(', ')
            };
        }
    }

    window.TeacherSubjectPicker = {
        init: function(config) {
            const picker = new SubjectPicker(config);
            instances[config.id] = picker;
            return picker;
        },
        get: function(id) {
            return instances[id];
        },
        LEVELS: Object.keys(LEVEL_SUBJECTS),
        LEVEL_SUBJECTS: LEVEL_SUBJECTS,
        normalizeLevel: normalizeLevel
    };

})(window);

