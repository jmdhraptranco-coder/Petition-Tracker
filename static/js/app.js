// Petition Tracker - Frontend JS

// Auto-dismiss flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('themeToggle');
    const langToggleGroups = document.querySelectorAll('.lang-toggle');
    const themeStorageKey = 'ui_theme_mode';
    const langStorageKey = 'ui_lang';
    const rootEl = document.documentElement;
    const viewportMobile = 768;
    const viewportTablet = 1100;
    const i18nVersion = '20260225-3';
    const originalTextNodes = new WeakMap();
    const originalAttrValues = new WeakMap();
    let activeLanguage = 'en';
    let activeDictionary = {};
    let isApplyingAutoTranslation = false;

    const escapeRegex = (text) => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

    const hasManualI18n = (el) => {
        if (!el || !el.closest) return false;
        return Boolean(el.closest('[data-i18n], [data-i18n-placeholder], [data-i18n-value], [data-no-auto-i18n]'));
    };

    const translateWithAutoMap = (text, dict) => {
        if (!text || typeof text !== 'string') return text;
        const auto = dict && dict.__auto__ ? dict.__auto__ : {};
        const phraseMap = auto.phrases || {};
        const wordMap = auto.words || {};
        let translated = text;

        const phraseEntries = Object.entries(phraseMap)
            .filter(([en, te]) => Boolean(en && te))
            .sort((a, b) => b[0].length - a[0].length);
        phraseEntries.forEach(([en, te]) => {
            const key = String(en).trim();
            if (!key || !te) return;
            const looksLikeSingleAsciiWord = /^[A-Za-z][A-Za-z'/-]*$/.test(key);
            if (looksLikeSingleAsciiWord && key.length < 4) return;
            const pattern = looksLikeSingleAsciiWord ? `\\b${escapeRegex(key)}\\b` : escapeRegex(key);
            const rx = new RegExp(pattern, 'gi');
            translated = translated.replace(rx, te);
        });

        translated = translated.replace(/\b([A-Za-z][A-Za-z'/-]*)\b/g, (token) => {
            const mapped = wordMap[token.toLowerCase()];
            return mapped || token;
        });
        return translated;
    };

    const applyAutoTranslations = (lang, dict) => {
        if (!document.body) return;
        isApplyingAutoTranslation = true;
        try {
            const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
            let node = walker.nextNode();
            while (node) {
                const parent = node.parentElement;
                const nodeValue = node.nodeValue || '';
                if (!parent || !nodeValue.trim()) {
                    node = walker.nextNode();
                    continue;
                }
                if (['SCRIPT', 'STYLE', 'NOSCRIPT', 'TEXTAREA', 'PRE', 'CODE', 'SVG'].includes(parent.tagName)) {
                    node = walker.nextNode();
                    continue;
                }
                if (hasManualI18n(parent)) {
                    node = walker.nextNode();
                    continue;
                }
                if (!originalTextNodes.has(node)) {
                    originalTextNodes.set(node, nodeValue);
                }
                const original = originalTextNodes.get(node) || nodeValue;
                node.nodeValue = lang === 'te' ? translateWithAutoMap(original, dict) : original;
                node = walker.nextNode();
            }

            const attrTargets = document.querySelectorAll('[placeholder], [title], [aria-label], input[type=\"submit\"], input[type=\"button\"], input[type=\"reset\"], button');
            attrTargets.forEach((el) => {
                if (hasManualI18n(el)) return;
                const attrs = [];
                if (el.hasAttribute('placeholder')) attrs.push('placeholder');
                if (el.hasAttribute('title')) attrs.push('title');
                if (el.hasAttribute('aria-label')) attrs.push('aria-label');
                if (el.tagName === 'INPUT' && ['submit', 'button', 'reset'].includes((el.getAttribute('type') || '').toLowerCase()) && el.hasAttribute('value')) {
                    attrs.push('value');
                }
                attrs.forEach((attr) => {
                    const cur = el.getAttribute(attr);
                    if (!cur || !cur.trim()) return;
                    let bag = originalAttrValues.get(el);
                    if (!bag) {
                        bag = {};
                        originalAttrValues.set(el, bag);
                    }
                    if (!Object.prototype.hasOwnProperty.call(bag, attr)) {
                        bag[attr] = cur;
                    }
                    const original = bag[attr];
                    const next = lang === 'te' ? translateWithAutoMap(original, dict) : original;
                    el.setAttribute(attr, next);
                });
            });
        } finally {
            isApplyingAutoTranslation = false;
        }
    };

    const applyTheme = (mode) => {
        rootEl.setAttribute('data-theme', mode);
        if (themeToggle) {
            const isDark = mode === 'dark';
            themeToggle.setAttribute('aria-pressed', String(isDark));
            themeToggle.setAttribute('title', isDark ? 'Switch to day mode' : 'Switch to night mode');
            themeToggle.setAttribute('aria-label', isDark ? 'Switch to day mode' : 'Switch to night mode');
        }
    };

    const savedTheme = localStorage.getItem(themeStorageKey);
    applyTheme(savedTheme === 'light' ? 'light' : 'dark');

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const next = rootEl.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            applyTheme(next);
            localStorage.setItem(themeStorageKey, next);
        });
    }

    const applyTranslations = (dict) => {
        document.querySelectorAll('[data-i18n]').forEach((el) => {
            const key = el.getAttribute('data-i18n');
            if (!key) return;
            if (Object.prototype.hasOwnProperty.call(dict, key)) {
                el.textContent = dict[key];
            }
        });
        document.querySelectorAll('[data-i18n-placeholder]').forEach((el) => {
            const key = el.getAttribute('data-i18n-placeholder');
            if (!key) return;
            if (Object.prototype.hasOwnProperty.call(dict, key)) {
                el.setAttribute('placeholder', dict[key]);
            }
        });
        document.querySelectorAll('[data-i18n-value]').forEach((el) => {
            const key = el.getAttribute('data-i18n-value');
            if (!key) return;
            if (Object.prototype.hasOwnProperty.call(dict, key)) {
                el.value = dict[key];
            }
        });
    };

    const loadLanguage = async (lang) => {
        try {
            const res = await fetch(`/static/i18n/${lang}.json?v=${i18nVersion}`, { cache: 'reload' });
            if (!res.ok) return;
            const dict = await res.json();
            activeLanguage = lang;
            activeDictionary = dict || {};
            applyTranslations(activeDictionary);
            applyAutoTranslations(activeLanguage, activeDictionary);
        } catch (e) {
            // eslint-disable-next-line no-console
            console.error('Language load failed:', lang, e);
            // keep default rendered text if translation file is unavailable
        }
    };

    const setLangUiState = (lang) => {
        rootEl.setAttribute('lang', lang === 'te' ? 'te' : 'en');
        langToggleGroups.forEach((group) => {
            group.setAttribute('data-active-lang', lang);
            group.querySelectorAll('.lang-pill[data-lang]').forEach((btn) => {
                const active = btn.getAttribute('data-lang') === lang;
                btn.classList.toggle('is-active', active);
                btn.setAttribute('aria-pressed', String(active));
            });
        });
    };

    const savedLang = localStorage.getItem(langStorageKey) || 'en';
    activeLanguage = savedLang;
    setLangUiState(savedLang);
    langToggleGroups.forEach((group) => {
        const setLanguage = async (nextLang) => {
            localStorage.setItem(langStorageKey, nextLang);
            setLangUiState(nextLang);
            await loadLanguage(nextLang);
        };

        group.querySelectorAll('.lang-pill[data-lang]').forEach((btn) => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const nextLang = btn.getAttribute('data-lang') || 'en';
                await setLanguage(nextLang);
            });
        });

        group.addEventListener('click', async () => {
            const current = group.getAttribute('data-active-lang') || activeLanguage || 'en';
            const nextLang = current === 'te' ? 'en' : 'te';
            await setLanguage(nextLang);
        });
    });
    loadLanguage(savedLang);

    const notifToggle = document.getElementById('notifToggle');
    const notifMenu = document.getElementById('notifMenu');
    const profileMenuToggle = document.getElementById('profileMenuToggle');
    const profileMenu = document.getElementById('profileMenu');
    if (notifToggle && notifMenu) {
        const isMobileViewport = () => window.matchMedia('(max-width: 768px)').matches;
        const placeTopMenu = (menuEl, toggleEl) => {
            if (!menuEl || !toggleEl) return;
            if (!isMobileViewport()) {
                menuEl.style.top = '';
                menuEl.style.left = '';
                menuEl.style.right = '';
                menuEl.style.width = '';
                return;
            }
            const rect = toggleEl.getBoundingClientRect();
            const top = Math.max(56, Math.round(rect.bottom + 8));
            menuEl.style.top = `${top}px`;
            menuEl.style.left = '10px';
            menuEl.style.right = '10px';
            menuEl.style.width = 'auto';
        };

        const closeNotif = () => {
            notifMenu.hidden = true;
            notifToggle.setAttribute('aria-expanded', 'false');
        };
        const openNotif = () => {
            if (profileMenu && profileMenuToggle) {
                profileMenu.hidden = true;
                profileMenuToggle.setAttribute('aria-expanded', 'false');
            }
            notifMenu.hidden = false;
            notifToggle.setAttribute('aria-expanded', 'true');
            placeTopMenu(notifMenu, notifToggle);
        };
        notifToggle.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const willOpen = notifMenu.hidden;
            if (willOpen) openNotif();
            else closeNotif();
        });
        document.addEventListener('click', (e) => {
            if (notifMenu.hidden) return;
            if (!notifMenu.contains(e.target) && !notifToggle.contains(e.target)) {
                closeNotif();
            }
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeNotif();
        });
        window.addEventListener('resize', () => {
            if (!notifMenu.hidden) placeTopMenu(notifMenu, notifToggle);
        });
    }

    if (profileMenuToggle && profileMenu) {
        const isMobileViewport = () => window.matchMedia('(max-width: 768px)').matches;
        const placeTopMenu = (menuEl, toggleEl) => {
            if (!menuEl || !toggleEl) return;
            if (!isMobileViewport()) {
                menuEl.style.top = '';
                menuEl.style.left = '';
                menuEl.style.right = '';
                menuEl.style.width = '';
                return;
            }
            const rect = toggleEl.getBoundingClientRect();
            const top = Math.max(56, Math.round(rect.bottom + 8));
            menuEl.style.top = `${top}px`;
            menuEl.style.left = '10px';
            menuEl.style.right = '10px';
            menuEl.style.width = 'auto';
        };

        const closeProfileMenu = () => {
            profileMenu.hidden = true;
            profileMenuToggle.setAttribute('aria-expanded', 'false');
        };
        const openProfileMenu = () => {
            if (notifMenu && notifToggle) {
                notifMenu.hidden = true;
                notifToggle.setAttribute('aria-expanded', 'false');
            }
            profileMenu.hidden = false;
            profileMenuToggle.setAttribute('aria-expanded', 'true');
            placeTopMenu(profileMenu, profileMenuToggle);
        };
        profileMenuToggle.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            const willOpen = profileMenu.hidden;
            if (willOpen) openProfileMenu();
            else closeProfileMenu();
        });
        document.addEventListener('click', (e) => {
            if (profileMenu.hidden) return;
            if (!profileMenu.contains(e.target) && !profileMenuToggle.contains(e.target)) {
                closeProfileMenu();
            }
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') closeProfileMenu();
        });
        window.addEventListener('resize', () => {
            if (!profileMenu.hidden) placeTopMenu(profileMenu, profileMenuToggle);
        });
    }

    const flashMessages = document.querySelectorAll('.flash-msg');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            msg.style.transform = 'translateY(-8px)';
            setTimeout(() => msg.remove(), 300);
        }, 5000);
    });

    // Auto-set target_cvo based on received_at for CVO/DSP offices
    const receivedAt = document.getElementById('received_at');
    const targetCvo = document.getElementById('target_cvo');
    if (receivedAt && targetCvo) {
        receivedAt.addEventListener('change', () => {
            const mapping = {
                'cvo_apspdcl_tirupathi': 'apspdcl',
                'cvo_apepdcl_vizag': 'apepdcl',
                'cvo_apscpdcl_vijayawada': 'apscpdcl'
            };
            if (mapping[receivedAt.value]) {
                targetCvo.value = mapping[receivedAt.value];
            }
        });
    }

    // Confirm dangerous actions
    document.querySelectorAll('.btn-danger').forEach(btn => {
        btn.addEventListener('click', (e) => {
            if (!confirm('Are you sure you want to proceed?')) {
                e.preventDefault();
            }
        });
    });

    // Dynamic sidebar: desktop compact rail + mobile drawer with overlay.
    const appLayout = document.querySelector('.app-layout');
    const sidebar = document.getElementById('sidebar');
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebarToggleText = sidebarToggle ? sidebarToggle.querySelector('.sidebar-toggle-text') : null;
    const sidebarOverlay = document.getElementById('sidebarOverlay');
    const mobileMq = window.matchMedia('(max-width: 768px)');
    const storageKey = 'sidebar_compact';
    const attentionSeenKey = 'sidebar_toggle_seen';
    let sidebarFlowTimer = null;

    if (appLayout && sidebar && sidebarToggle) {
        const applyViewportMode = () => {
            const w = window.innerWidth || document.documentElement.clientWidth || 0;
            const mode = w <= viewportMobile ? 'mobile' : (w <= viewportTablet ? 'tablet' : 'desktop');
            rootEl.setAttribute('data-screen-size', mode);
        };

        applyViewportMode();
        window.addEventListener('resize', applyViewportMode);
        window.addEventListener('orientationchange', applyViewportMode);

        if (sessionStorage.getItem(attentionSeenKey) !== '1') {
            sidebarToggle.classList.add('attention');
        }

        const syncAria = () => {
            let label = 'Collapse Menu';
            if (mobileMq.matches) {
                const mobileExpanded = sidebar.classList.contains('mobile-expanded');
                sidebarToggle.setAttribute('aria-expanded', String(mobileExpanded));
                label = mobileExpanded ? 'Hide Menu' : 'Open Menu';
            } else {
                const expanded = !appLayout.classList.contains('sidebar-compact');
                sidebarToggle.setAttribute('aria-expanded', String(expanded));
                label = expanded ? 'Collapse Menu' : 'Expand Menu';
            }
            sidebarToggle.setAttribute('title', label);
            sidebarToggle.setAttribute('aria-label', label);
            if (sidebarToggleText) sidebarToggleText.textContent = label;
        };

        const closeMobileSidebar = () => {
            if (!mobileMq.matches) return;
            sidebar.classList.remove('mobile-expanded');
            if (sidebarOverlay) sidebarOverlay.classList.remove('active');
            syncAria();
        };

        const applySidebarMode = () => {
            if (mobileMq.matches) {
                appLayout.classList.remove('sidebar-compact');
                sidebar.classList.remove('collapsed');
                sidebar.classList.remove('mobile-expanded');
                if (sidebarOverlay) sidebarOverlay.classList.remove('active');
            } else {
                sidebar.classList.remove('collapsed');
                sidebar.classList.remove('mobile-expanded');
                const shouldCompact = localStorage.getItem(storageKey) === '1';
                appLayout.classList.toggle('sidebar-compact', shouldCompact);
            }
            syncAria();
        };

        applySidebarMode();

        sidebarToggle.addEventListener('click', () => {
            sidebarToggle.classList.remove('attention');
            sessionStorage.setItem(attentionSeenKey, '1');
            sidebarToggle.classList.remove('flowing');
            if (sidebarFlowTimer) clearTimeout(sidebarFlowTimer);
            requestAnimationFrame(() => sidebarToggle.classList.add('flowing'));
            sidebarFlowTimer = setTimeout(() => sidebarToggle.classList.remove('flowing'), 420);

            if (mobileMq.matches) {
                sidebar.classList.toggle('mobile-expanded');
                if (sidebarOverlay) {
                    sidebarOverlay.classList.toggle('active', sidebar.classList.contains('mobile-expanded'));
                }
                syncAria();
                return;
            }

            const compactNow = !appLayout.classList.contains('sidebar-compact');
            appLayout.classList.toggle('sidebar-compact', compactNow);
            localStorage.setItem(storageKey, compactNow ? '1' : '0');
            syncAria();
        });

        if (sidebarOverlay) {
            sidebarOverlay.addEventListener('click', closeMobileSidebar);
        }

        sidebar.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', closeMobileSidebar);
        });

        window.addEventListener('resize', applySidebarMode);
    }

    initStatCardAnimations();
    initWorkflowConnectorAnimations();
    initActionPanelDrawers();
    initResponsiveTables();
    initReportCompactAccordion();
    initPetitionRowNavigation();
});

function initStatCardAnimations() {
    const counters = document.querySelectorAll('.countup[data-target]');
    counters.forEach((el) => {
        const target = Number(el.dataset.target || 0);
        if (Number.isNaN(target)) return;
        const duration = 900;
        const start = performance.now();
        const from = 0;
        const step = (now) => {
            const progress = Math.min((now - start) / duration, 1);
            const eased = 1 - Math.pow(1 - progress, 3);
            const value = Math.round(from + (target - from) * eased);
            el.textContent = value.toLocaleString('en-IN');
            if (progress < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
    });

    document.querySelectorAll('.stat-card').forEach((card, index) => {
        const metric = card.dataset.metric || `metric_${index}`;
        const countEl = card.querySelector('.countup');
        const count = Number((countEl && countEl.dataset ? countEl.dataset.target : 0) || 0);
        const sparklineWrap = card.querySelector('.stat-sparkline');
        if (sparklineWrap) {
            sparklineWrap.innerHTML = buildSparklineSvg(metric, count);
        }
        if (card.classList.contains('sla-stat') && card.dataset.thresholdCrossed === '1') {
            card.classList.add('sla-threshold-alert');
        }
    });
}

function buildSparklineSvg(seedText, value) {
    const width = 128;
    const height = 32;
    const points = 12;
    let seed = 0;
    for (let i = 0; i < seedText.length; i += 1) seed += seedText.charCodeAt(i) * (i + 1);
    seed += Math.max(0, value);
    const rand = () => {
        seed = (seed * 9301 + 49297) % 233280;
        return seed / 233280;
    };
    const base = 8 + Math.min(12, value % 13);
    const coords = [];
    for (let i = 0; i < points; i += 1) {
        const x = Math.round((i / (points - 1)) * (width - 4)) + 2;
        const volatility = 5 + (value % 5);
        const y = Math.round(Math.max(3, Math.min(height - 3, height - (base + rand() * volatility + (i * 0.6)))));
        coords.push(`${x},${y}`);
    }
    return `<svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="presentation" aria-hidden="true">
        <polyline fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" points="${coords.join(' ')}"></polyline>
    </svg>`;
}

function initWorkflowConnectorAnimations() {
    const connectors = document.querySelectorAll('.workflow-connector.active');
    connectors.forEach((connector, idx) => {
        connector.style.setProperty('--flow-delay', `${idx * 0.14}s`);
    });
}

function initActionPanelDrawers() {
    const groups = document.querySelectorAll('.action-panels');
    groups.forEach((group) => {
        const panels = [...group.querySelectorAll('.action-panel')].filter((panel) => !panel.classList.contains('action-closed'));
        if (panels.length <= 1) return;
        group.querySelectorAll('.action-divider').forEach((div) => { div.style.display = 'none'; });
        panels.forEach((panel, idx) => {
            if (panel.dataset.drawerEnhanced === '1') return;
            const heading = panel.querySelector('h4');
            if (!heading) return;
            panel.dataset.drawerEnhanced = '1';
            panel.classList.add('action-drawer');
            if (idx === 0) panel.classList.add('drawer-open');

            const toggle = document.createElement('button');
            toggle.type = 'button';
            toggle.className = 'action-drawer-toggle';
            toggle.setAttribute('aria-expanded', idx === 0 ? 'true' : 'false');
            toggle.innerHTML = `<span>${heading.textContent.trim()}</span><span class="drawer-chevron" aria-hidden="true">+</span>`;
            heading.remove();
            panel.prepend(toggle);

            const body = document.createElement('div');
            body.className = 'action-drawer-body';
            while (toggle.nextSibling) {
                body.appendChild(toggle.nextSibling);
            }
            panel.appendChild(body);

            if (idx !== 0) body.style.maxHeight = '0px';
            else body.style.maxHeight = `${body.scrollHeight + 24}px`;

            toggle.addEventListener('click', () => {
                const open = panel.classList.contains('drawer-open');
                panel.classList.toggle('drawer-open', !open);
                toggle.setAttribute('aria-expanded', String(!open));
                body.style.maxHeight = open ? '0px' : `${body.scrollHeight + 24}px`;
            });
        });
    });
}

function initResponsiveTables() {
    const tables = document.querySelectorAll('.data-table');
    tables.forEach((table) => {
        const headers = [...table.querySelectorAll('thead th')].map((th) => (th.textContent || '').trim());
        if (!headers.length) return;
        table.querySelectorAll('tbody tr').forEach((tr) => {
            tr.querySelectorAll('td').forEach((td, idx) => {
                if (!td.dataset.label && headers[idx]) {
                    td.dataset.label = headers[idx];
                }
            });
        });
    });
}

function initReportCompactAccordion() {
    const groups = document.querySelectorAll('.report-compact-list');
    groups.forEach((group) => {
        const items = [...group.querySelectorAll('details.report-compact-item')];
        items.forEach((item) => {
            item.addEventListener('toggle', () => {
                if (!item.open) return;
                items.forEach((other) => {
                    if (other !== item) other.open = false;
                });
            });
        });
    });
}

function initPetitionRowNavigation() {
    const rows = document.querySelectorAll('.js-petition-row[data-href]');
    rows.forEach((row) => {
        const href = row.getAttribute('data-href');
        if (!href) return;

        row.addEventListener('click', (event) => {
            if (event.target.closest('a, button, input, select, textarea, label')) return;
            window.location.href = href;
        });

        row.addEventListener('keydown', (event) => {
            if (event.key !== 'Enter' && event.key !== ' ') return;
            if (event.target.closest('a, button, input, select, textarea, label')) return;
            event.preventDefault();
            window.location.href = href;
        });
    });
}


