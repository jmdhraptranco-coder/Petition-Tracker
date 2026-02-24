// Petition Tracker - Frontend JS

// Auto-dismiss flash messages after 5 seconds
document.addEventListener('DOMContentLoaded', () => {
    const themeToggle = document.getElementById('themeToggle');
    const themeStorageKey = 'ui_theme_mode';
    const rootEl = document.documentElement;
    const viewportMobile = 768;
    const viewportTablet = 1100;

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
    applyTheme(savedTheme === 'dark' ? 'dark' : 'light');

    if (themeToggle) {
        themeToggle.addEventListener('click', () => {
            const next = rootEl.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
            applyTheme(next);
            localStorage.setItem(themeStorageKey, next);
        });
    }

    const notifToggle = document.getElementById('notifToggle');
    const notifMenu = document.getElementById('notifMenu');
    if (notifToggle && notifMenu) {
        const closeNotif = () => {
            notifMenu.hidden = true;
            notifToggle.setAttribute('aria-expanded', 'false');
        };
        const openNotif = () => {
            notifMenu.hidden = false;
            notifToggle.setAttribute('aria-expanded', 'true');
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
    }

    const flashMessages = document.querySelectorAll('.flash-msg');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            msg.style.transform = 'translateY(-8px)';
            setTimeout(() => msg.remove(), 300);
        }, 5000);
    });

    // Auto-set target_cvo based on received_at for CVO offices
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
                sidebarToggle.setAttribute('aria-expanded', String(sidebar.classList.contains('collapsed')));
                label = sidebar.classList.contains('collapsed') ? 'Hide Menu' : 'Open Menu';
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
            sidebar.classList.remove('collapsed');
            if (sidebarOverlay) sidebarOverlay.classList.remove('active');
            syncAria();
        };

        const applySidebarMode = () => {
            if (mobileMq.matches) {
                appLayout.classList.remove('sidebar-compact');
                if (sidebarOverlay) sidebarOverlay.classList.remove('active');
            } else {
                sidebar.classList.remove('collapsed');
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
                sidebar.classList.toggle('collapsed');
                if (sidebarOverlay) {
                    sidebarOverlay.classList.toggle('active', sidebar.classList.contains('collapsed'));
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

