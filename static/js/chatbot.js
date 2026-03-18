/* ================================================
   Nigaa Chatbot Assistant – Premium UI v2.0
   ================================================ */

(function () {
    'use strict';

    /* ── State ──────────────────────────────────── */
    let isOpen = false;
    let welcomeShown = false;

    /* ── DOM refs ───────────────────────────────── */
    let widget, fab, panel, messagesEl, inputEl, sendBtn,
        welcomeBubble, welcomeDismissBtn, panelOverlay;

    /* ── Status badge colours ───────────────────── */
    const STATUS_COLORS = {
        received:                  '#3b82f6',
        forwarded_to_cvo:          '#8b5cf6',
        sent_for_permission:       '#f59e0b',
        permission_approved:       '#22c55e',
        permission_rejected:       '#ef4444',
        assigned_to_inspector:     '#06b6d4',
        sent_back_for_reenquiry:   '#f97316',
        enquiry_in_progress:       '#a78bfa',
        enquiry_report_submitted:  '#34d399',
        forwarded_to_jmd:          '#8b5cf6',
        forwarded_to_po:           '#6366f1',
        action_instructed:         '#f59e0b',
        action_taken:              '#10b981',
        lodged:                    '#22c55e',
        closed:                    '#6b7280',
    };

    /* ── Role-specific workflow guide ──────────── */
    const ACTION_GUIDES = {
        inspector: {
            title: '📋 Inspector Workflow',
            color: '#06b6d4',
            steps: [
                { icon: '📥', label: 'Check Assigned Petitions', desc: 'Review all petitions assigned to you under "Pending" tab.', link: '/petitions?status=assigned_to_inspector' },
                { icon: '🔍', label: 'Start Enquiry', desc: 'Open the petition → click "Start Enquiry" to begin field investigation.', link: null },
                { icon: '📝', label: 'Submit Enquiry Report', desc: 'Once investigation is complete, upload your report and submit.', link: null },
                { icon: '🔁', label: 'Re-enquiry Cases', desc: 'Check petitions marked for re-enquiry and address them promptly.', link: '/petitions?status=sent_back_for_reenquiry' },
            ]
        },
        cvo_apspdcl: {
            title: '📋 CVO Workflow',
            color: '#8b5cf6',
            steps: [
                { icon: '📥', label: 'Review Received Petitions', desc: 'Check all newly received petitions awaiting your review.', link: '/petitions?status=received' },
                { icon: '👨‍💼', label: 'Assign to Inspector', desc: 'Select an inspector and forward the petition for field enquiry.', link: null },
                { icon: '🔐', label: 'Request Permission (if needed)', desc: 'For sensitive cases, send for permission before proceeding.', link: null },
                { icon: '📊', label: 'Monitor Progress', desc: 'Track enquiry reports and status updates across all cases.', link: '/petitions' },
            ]
        },
        po: {
            title: '📋 PO Workflow',
            color: '#6366f1',
            steps: [
                { icon: '📥', label: 'Review Forwarded Petitions', desc: 'Check petitions forwarded to you for action instruction.', link: '/petitions?status=forwarded_to_po' },
                { icon: '✅', label: 'Approve / Reject Permission', desc: 'Review permission requests from CVOs and respond.', link: '/petitions?status=sent_for_permission' },
                { icon: '📣', label: 'Issue Action Instructions', desc: 'Instruct relevant CMD/CGM to take specific action.', link: null },
                { icon: '📊', label: 'SLA & Overdue Review', desc: 'Check petitions beyond SLA to prevent escalation.', link: '/petitions?status=beyond_sla' },
            ]
        },
        data_entry: {
            title: '📋 Data Entry Workflow',
            color: '#f59e0b',
            steps: [
                { icon: '➕', label: 'Register New Petition', desc: 'Add new petitions with petitioner details and subject.', link: '/petitions/new' },
                { icon: '📎', label: 'Upload E-Receipt', desc: 'Attach scanned E-Receipt document to each petition.', link: null },
                { icon: '🏢', label: 'Assign to CVO Office', desc: 'Route petition to the correct CVO based on jurisdiction.', link: null },
                { icon: '🔍', label: 'Track & Verify', desc: 'Follow up on pending petitions to ensure correct processing.', link: '/petitions' },
            ]
        },
        super_admin: {
            title: '📋 Admin Workflow',
            color: '#ef4444',
            steps: [
                { icon: '👥', label: 'Manage Users', desc: 'Create, edit, and manage officer accounts and roles.', link: '/users' },
                { icon: '📊', label: 'Full Dashboard Overview', desc: 'Monitor all petition statuses and SLA compliance.', link: '/' },
                { icon: '⚠️', label: 'Overdue Escalation', desc: 'Review and escalate petitions beyond SLA threshold.', link: '/petitions?status=beyond_sla' },
                { icon: '📂', label: 'Reports & Audit', desc: 'Generate reports and review audit activity across the system.', link: null },
            ]
        },
    };
    ACTION_GUIDES.cvo_apepdcl = ACTION_GUIDES.cvo_apspdcl;
    ACTION_GUIDES.cvo_apcpdcl = ACTION_GUIDES.cvo_apspdcl;
    ACTION_GUIDES.dsp          = ACTION_GUIDES.cvo_apspdcl;
    ACTION_GUIDES.cmd_apspdcl  = {
        title: '📋 CMD/CGM Workflow', color: '#10b981',
        steps: [
            { icon: '📥', label: 'Check Action Instructions', desc: 'Review petitions with action instructions assigned to you.', link: '/petitions?status=action_instructed' },
            { icon: '✅', label: 'Take Action', desc: 'Complete required action and update the petition status.', link: null },
            { icon: '📤', label: 'Submit Action Report', desc: 'Report back with action taken and supporting evidence.', link: null },
            { icon: '📊', label: 'Track Closed Cases', desc: 'Review completed cases for compliance records.', link: '/petitions?status=action_taken' },
        ]
    };
    ACTION_GUIDES.cmd_apepdcl = ACTION_GUIDES.cmd_apspdcl;
    ACTION_GUIDES.cmd_apcpdcl = ACTION_GUIDES.cmd_apspdcl;
    ACTION_GUIDES.cgm_hr_transco = ACTION_GUIDES.cmd_apspdcl;

    /* ── Quick action chips ─────────────────────── */
    const QUICK_ACTIONS = [
        { label: '⏳ Pending',    msg: 'pending' },
        { label: '🔔 Updates',   msg: 'updates' },
        { label: '💡 What Next', msg: 'what next' },
        { label: '📅 Today',     msg: 'today' },
        { label: '📈 Report',    msg: 'report' },
        { label: '❓ Help',      msg: 'help' },
    ];

    /* ═══════════════════════════════════════════════
       INIT
    ══════════════════════════════════════════════ */
    function init() {
        widget        = document.getElementById('nigaaChatWidget');
        fab           = document.getElementById('nigaaFab');
        panel         = document.getElementById('nigaaPanel');
        messagesEl    = document.getElementById('nigaaMessages');
        inputEl       = document.getElementById('nigaaInput');
        sendBtn       = document.getElementById('nigaaSend');
        welcomeBubble = document.getElementById('nigaaWelcome');
        welcomeDismissBtn = document.getElementById('nigaaWelcomeDismiss');
        panelOverlay  = document.getElementById('nigaaPanelOverlay');

        if (!widget) return;

        fab.addEventListener('click', togglePanel);
        sendBtn.addEventListener('click', handleSend);
        inputEl.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
        });
        document.getElementById('nigaaClose')?.addEventListener('click', closePanel);
        welcomeDismissBtn?.addEventListener('click', dismissWelcome);
        panelOverlay?.addEventListener('click', closePanel);

        buildQuickActions();

        setTimeout(showWelcome, 1800);
    }

    /* ═══════════════════════════════════════════════
       WELCOME BUBBLE
    ══════════════════════════════════════════════ */
    function showWelcome() {
        if (!welcomeBubble) return;
        welcomeShown = true;
        welcomeBubble.style.display = '';
        welcomeBubble.classList.remove('dismissing');
        welcomeBubble.classList.add('visible');
        setTimeout(() => dismissWelcome(), 9000);
    }

    function dismissWelcome() {
        if (!welcomeBubble) return;
        welcomeBubble.classList.remove('visible');
        welcomeBubble.classList.add('dismissing');
        setTimeout(() => { welcomeBubble.style.display = 'none'; }, 400);
    }

    /* ═══════════════════════════════════════════════
       PANEL OPEN / CLOSE
    ══════════════════════════════════════════════ */
    function togglePanel() { if (isOpen) closePanel(); else openPanel(); }

    function openPanel() {
        isOpen = true;
        dismissWelcome();
        panel.classList.add('open');
        panelOverlay?.classList.add('active');
        fab.classList.add('active');
        fab.setAttribute('aria-expanded', 'true');
        if (window.innerWidth <= 768) document.body.style.overflow = 'hidden';
        inputEl.focus();

        if (messagesEl.children.length === 0) {
            addBotMessage(
                "Hi! I'm **Nigaa** 👋 — your AI petition assistant.\n\n" +
                "Here's what I can help you with:\n" +
                "• _\"what next\"_ — get personalized next action suggestions\n" +
                "• _\"today\"_ — your daily summary\n" +
                "• _\"pending\"_ — petitions needing your action\n" +
                "• _\"report\"_ — open analysis report & download\n" +
                "• _\"urgent\"_ — SLA breach / overdue cases\n" +
                "• _\"stats\"_ — petition statistics\n" +
                "• _\"guide\"_ — step-by-step workflow"
            );
        }
    }

    function closePanel() {
        isOpen = false;
        panel.classList.remove('open');
        panelOverlay?.classList.remove('active');
        fab.classList.remove('active');
        fab.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
    }

    /* ═══════════════════════════════════════════════
       QUICK ACTIONS
    ══════════════════════════════════════════════ */
    function buildQuickActions() {
        const container = document.getElementById('nigaaQuickActions');
        if (!container) return;
        QUICK_ACTIONS.forEach(({ label, msg }) => {
            const btn = document.createElement('button');
            btn.className = 'nigaa-chip';
            btn.textContent = label;
            btn.addEventListener('click', () => {
                if (msg.endsWith(' ')) {
                    inputEl.value = msg;
                    inputEl.focus();
                } else {
                    inputEl.value = msg;
                    handleSend();
                }
            });
            container.appendChild(btn);
        });
    }

    /* ═══════════════════════════════════════════════
       SEND MESSAGE
    ══════════════════════════════════════════════ */
    function handleSend() {
        const text = inputEl.value.trim();
        if (!text) return;

        addUserMessage(text);
        inputEl.value = '';
        inputEl.disabled = true;
        sendBtn.disabled = true;

        showTyping();

        fetch('/api/chatbot', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message: text }),
        })
            .then(r => r.json())
            .then(data => { hideTyping(); handleResponse(data); })
            .catch(() => { hideTyping(); addBotMessage('⚠️ Connection error. Please try again.'); })
            .finally(() => { inputEl.disabled = false; sendBtn.disabled = false; inputEl.focus(); });
    }

    /* ═══════════════════════════════════════════════
       RESPONSE HANDLERS
    ══════════════════════════════════════════════ */
    function handleResponse(data) {
        switch (data.type) {
            case 'text':         addBotMessage(data.text); break;
            case 'help':         addHelpCard(); break;
            case 'stats':        addStatsCard(data.stats); break;
            case 'petitions':    addPetitionResults(data.petitions, data.query, data.search_type); break;
            case 'pending':      addPendingCard(data.petitions, data.role); break;
            case 'updates':      addUpdatesCard(data.petitions, data.role); break;
            case 'action_guide': addActionGuideCard(data.role); break;
            case 'role_info':    addRoleInfoCard(data.role_data, data.user_name); break;
            case 'download':     addDownloadCard(data); break;
            case 'summary':      addSummaryCard(data); break;
            case 'urgent':       addUrgentCard(data); break;
            case 'suggest':      addSuggestionCard(data); break;
            default:             addBotMessage(data.text || 'Got it!');
        }
        if (data.suggestions && data.suggestions.length) {
            addSuggestionsChips(data.suggestions);
        }
    }

    /* ─── Text bubble with typewriter effect ────── */
    function addBotMessage(text, instant = false) {
        const el = createBubble('bot');
        appendMsg(el);
        if (instant || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
            el.innerHTML = markdownLite(text);
        } else {
            typewriterRender(el, text);
        }
    }
    function addUserMessage(text) {
        const el = createBubble('user');
        el.textContent = text;
        appendMsg(el);
    }

    /* ─── Typewriter: word-by-word, adaptive speed ─ */
    function typewriterRender(el, text) {
        const words = text.split(/(\s+)/);   // keep whitespace tokens
        const totalWords = words.filter(w => w.trim()).length;
        // Adaptive: cap total animation at ~1.2 s
        const delay = Math.min(55, Math.max(18, Math.round(1200 / Math.max(totalWords, 1))));
        let i = 0;
        let built = '';

        // cursor span
        const cursor = document.createElement('span');
        cursor.className = 'nigaa-cursor';
        cursor.textContent = '▋';
        el.innerHTML = '';
        el.appendChild(cursor);

        function step() {
            if (i >= words.length) {
                el.innerHTML = markdownLite(text);   // final render with full markdown
                scrollToBottom();
                return;
            }
            built += words[i];
            i++;
            el.innerHTML = markdownLite(built) + '<span class="nigaa-cursor">▋</span>';
            scrollToBottom();
            // Skip whitespace-only tokens instantly
            const token = words[i - 1];
            setTimeout(step, token.trim() ? delay : 0);
        }
        step();
    }

    function createBubble(role) {
        const wrap = document.createElement('div');
        wrap.className = `nigaa-msg nigaa-msg-${role}`;
        if (role === 'bot') {
            const av = document.createElement('div');
            av.className = 'nigaa-msg-avatar';
            av.innerHTML = miniRobotSVG();
            wrap.appendChild(av);
        }
        const bubble = document.createElement('div');
        bubble.className = 'nigaa-bubble';
        wrap.appendChild(bubble);
        return bubble;
    }

    /* ─── Help card ──────────────────────────────── */
    function addHelpCard() {
        const wrap = makeBotWrap();
        const card = document.createElement('div');
        card.className = 'nigaa-card nigaa-help-card';
        card.innerHTML = `
          <div class="nigaa-card-title">🤖 What I can do</div>
          <ul class="nigaa-help-list">
            <li><kbd>what next</kbd> — Personalized next action suggestions</li>
            <li><kbd>today</kbd> — Your daily summary &amp; overview</li>
            <li><kbd>pending</kbd> — Petitions needing your action</li>
            <li><kbd>updates</kbd> — Recent activity &amp; status changes</li>
            <li><kbd>urgent</kbd> — SLA breach &amp; overdue cases</li>
            <li><kbd>guide</kbd> — Step-by-step workflow for your role</li>
            <li><kbd>stats</kbd> — View petition statistics</li>
            <li><kbd>report</kbd> — Open analysis report &amp; download</li>
            <li><kbd>my role</kbd> — Your responsibilities</li>
            <li><kbd>search [name]</kbd> — Search by petitioner name</li>
            <li><kbd>eoffice [no]</kbd> — Search by E-Office file number</li>
            <li><kbd>ereceipt [no]</kbd> — Search by E-Receipt number</li>
            <li><kbd>sno [no]</kbd> — Search by serial number</li>
          </ul>
        `;
        wrap.appendChild(card);
        appendMsg(wrap);
    }

    /* ─── Stats card ─────────────────────────────── */
    function addStatsCard(stats) {
        const wrap = makeBotWrap();
        const card = document.createElement('div');
        card.className = 'nigaa-card nigaa-stats-card';
        card.innerHTML = `
          <div class="nigaa-card-title">📊 Petition Statistics</div>
          <div class="nigaa-stats-grid">
            <div class="nigaa-stat-item nigaa-stat-total">
              <span class="nigaa-stat-num">${stats.total || 0}</span>
              <span class="nigaa-stat-lbl">Total</span>
            </div>
            <div class="nigaa-stat-item nigaa-stat-open">
              <span class="nigaa-stat-num">${stats.open || 0}</span>
              <span class="nigaa-stat-lbl">Open</span>
            </div>
            <div class="nigaa-stat-item nigaa-stat-closed">
              <span class="nigaa-stat-num">${stats.closed || 0}</span>
              <span class="nigaa-stat-lbl">Closed</span>
            </div>
            <div class="nigaa-stat-item nigaa-stat-received">
              <span class="nigaa-stat-num">${stats.received || 0}</span>
              <span class="nigaa-stat-lbl">Received</span>
            </div>
          </div>
          <a href="/petitions" class="nigaa-view-all-link">View all petitions →</a>
        `;
        wrap.appendChild(card);
        appendMsg(wrap);
    }

    /* ─── Petition search results ────────────────── */
    function addPetitionResults(petitions, query, searchType) {
        const wrap = makeBotWrap();
        const container = document.createElement('div');
        container.style.maxWidth = '100%';

        if (!petitions || petitions.length === 0) {
            const bubble = document.createElement('div');
            bubble.className = 'nigaa-bubble';
            bubble.textContent = `No petitions found for "${query}". Try a different search term.`;
            container.appendChild(bubble);
        } else {
            const header = document.createElement('div');
            header.className = 'nigaa-bubble nigaa-results-header';
            header.innerHTML = `Found <strong>${petitions.length}</strong> petition${petitions.length > 1 ? 's' : ''} for <em>"${escHtml(query)}"</em>`;
            container.appendChild(header);
            petitions.forEach(p => container.appendChild(buildPetitionCard(p)));
        }

        wrap.appendChild(container);
        appendMsg(wrap);
    }

    /* ─── Pending petitions card ─────────────────── */
    function addPendingCard(petitions, role) {
        const wrap = makeBotWrap();
        const container = document.createElement('div');
        container.style.maxWidth = '100%';

        if (!petitions || petitions.length === 0) {
            const bubble = document.createElement('div');
            bubble.className = 'nigaa-bubble nigaa-empty-bubble';
            bubble.innerHTML = '✅ <strong>All clear!</strong> No pending petitions require your action right now.';
            container.appendChild(bubble);
        } else {
            const header = document.createElement('div');
            header.className = 'nigaa-section-header nigaa-section-pending';
            header.innerHTML = `
              <span class="nigaa-section-icon">⏳</span>
              <span><strong>${petitions.length}</strong> Petition${petitions.length > 1 ? 's' : ''} Needing Action</span>
              <span class="nigaa-section-badge nigaa-badge-warn">${petitions.length}</span>
            `;
            container.appendChild(header);
            petitions.forEach(p => container.appendChild(buildPetitionCard(p, true)));

            const footer = document.createElement('a');
            footer.href = '/petitions';
            footer.className = 'nigaa-view-all-link';
            footer.textContent = 'View all petitions →';
            container.appendChild(footer);
        }

        wrap.appendChild(container);
        appendMsg(wrap);
    }

    /* ─── Recent updates card ────────────────────── */
    function addUpdatesCard(petitions, role) {
        const wrap = makeBotWrap();
        const container = document.createElement('div');
        container.style.maxWidth = '100%';

        if (!petitions || petitions.length === 0) {
            const bubble = document.createElement('div');
            bubble.className = 'nigaa-bubble nigaa-empty-bubble';
            bubble.innerHTML = 'ℹ️ No updates so far today in your scope.';
            container.appendChild(bubble);
        } else {
            const header = document.createElement('div');
            header.className = 'nigaa-section-header nigaa-section-updates';
            header.innerHTML = `
              <span class="nigaa-section-icon">🔔</span>
              <span><strong>Today's Updates</strong></span>
              <span class="nigaa-section-badge nigaa-badge-info">${petitions.length}</span>
            `;
            container.appendChild(header);

            petitions.forEach(p => {
                const item = document.createElement('div');
                item.className = 'nigaa-update-item';
                const color = STATUS_COLORS[p.status] || '#6b7280';
                item.innerHTML = `
                  <div class="nigaa-update-dot" style="background:${color}"></div>
                  <div class="nigaa-update-body">
                    <div class="nigaa-update-name">${escHtml(p.petitioner_name)}
                      <span class="nigaa-petition-status" style="--sc:${color}">${escHtml(p.status_label)}</span>
                    </div>
                    <div class="nigaa-update-subject">${escHtml(p.subject)}</div>
                    <div class="nigaa-update-meta">
                      <span>🕒 ${escHtml(p.updated_at || '-')}</span>
                      ${p.sno !== '-' ? `<span>${escHtml(p.sno)}</span>` : ''}
                    </div>
                    <a href="/petitions/${p.id}" class="nigaa-petition-link">View &amp; Act →</a>
                  </div>
                `;
                container.appendChild(item);
            });

            const footer = document.createElement('a');
            footer.href = '/petitions';
            footer.className = 'nigaa-view-all-link';
            footer.textContent = 'View all petitions →';
            container.appendChild(footer);
        }

        wrap.appendChild(container);
        appendMsg(wrap);
    }

    /* ─── Action guide card ──────────────────────── */
    function addActionGuideCard(role) {
        const guide = ACTION_GUIDES[role];
        const wrap = makeBotWrap();

        if (!guide) {
            const bubble = document.createElement('div');
            bubble.className = 'nigaa-bubble';
            bubble.innerHTML = markdownLite(
                "Here's how to get started:\n\n" +
                "• 📥 Check your **Petitions** page for items assigned to you\n" +
                "• 🔍 Use **search** to find specific petitions\n" +
                "• 📊 Check **stats** for an overview\n\n" +
                "Contact your administrator if you need role-specific guidance."
            );
            wrap.appendChild(bubble);
            appendMsg(wrap);
            return;
        }

        const card = document.createElement('div');
        card.className = 'nigaa-card nigaa-guide-card';
        card.style.setProperty('--guide-color', guide.color);

        const title = document.createElement('div');
        title.className = 'nigaa-card-title nigaa-guide-title';
        title.textContent = guide.title;
        card.appendChild(title);

        guide.steps.forEach((step, i) => {
            const row = document.createElement('div');
            row.className = 'nigaa-guide-step';
            row.innerHTML = `
              <div class="nigaa-guide-step-num">${i + 1}</div>
              <div class="nigaa-guide-step-icon">${step.icon}</div>
              <div class="nigaa-guide-step-body">
                <div class="nigaa-guide-step-label">${escHtml(step.label)}</div>
                <div class="nigaa-guide-step-desc">${escHtml(step.desc)}</div>
                ${step.link ? `<a href="${step.link}" class="nigaa-guide-step-link">Go →</a>` : ''}
              </div>
            `;
            card.appendChild(row);
        });

        wrap.appendChild(card);
        appendMsg(wrap);
    }

    /* ─── Role info card ─────────────────────────── */
    function addRoleInfoCard(roleData, userName) {
        const wrap = makeBotWrap();
        const card = document.createElement('div');
        card.className = 'nigaa-card nigaa-role-card';
        card.style.setProperty('--role-color', roleData.color || '#f59e0b');

        card.innerHTML = `
          <div class="nigaa-role-header">
            <span class="nigaa-role-badge">${escHtml(roleData.badge || '👤')}</span>
            <div>
              <div class="nigaa-role-title">${escHtml(roleData.title)}</div>
              <div class="nigaa-role-name">${escHtml(userName || '')}</div>
            </div>
          </div>
          <div class="nigaa-role-summary">${escHtml(roleData.summary || '')}</div>
          <div class="nigaa-role-resp-label">Your Responsibilities</div>
          <ul class="nigaa-role-resp-list">
            ${(roleData.responsibilities || []).map(r => `<li>${escHtml(r)}</li>`).join('')}
          </ul>
          ${roleData.key_link ? `<a href="${escHtml(roleData.key_link)}" class="nigaa-view-all-link">Go to my work →</a>` : ''}
        `;
        wrap.appendChild(card);
        appendMsg(wrap);
    }

    /* ─── Download / Analysis Report card ───────── */
    function addDownloadCard(data) {
        const wrap = makeBotWrap();
        const card = document.createElement('div');
        card.className = 'nigaa-card nigaa-download-card';
        card.innerHTML = `
          <div class="nigaa-card-title">📈 Analysis Report</div>
          <div class="nigaa-download-desc">${escHtml(data.text || 'Access comprehensive petition analytics, charts, and export options.')}</div>
          <div class="nigaa-download-features">
            <span>📊 Charts &amp; Trends</span>
            <span>🗂️ Status Breakdown</span>
            <span>👥 CVO Performance</span>
            <span>⬇️ Excel / PDF Export</span>
          </div>
          <div class="nigaa-download-actions">
            <a href="/analysis-report" class="nigaa-download-btn" target="_blank">📈 Open Analysis Report</a>
          </div>
          <div class="nigaa-download-note">💡 Use the export buttons inside the report to download as PDF or Excel.</div>
        `;
        wrap.appendChild(card);
        appendMsg(wrap);
    }

    /* ─── Daily Summary card ─────────────────────── */
    function addSummaryCard(data) {
        const wrap = makeBotWrap();
        const card = document.createElement('div');
        card.className = 'nigaa-card nigaa-summary-card';
        const stats = data.stats || {};
        const pendingCount = data.pending_count || 0;
        const updatesCount = data.updates_count || 0;
        card.innerHTML = `
          <div class="nigaa-card-title">📅 Daily Summary</div>
          <div class="nigaa-summary-grid">
            <div class="nigaa-summary-item">
              <span class="nigaa-summary-num">${stats.total || 0}</span>
              <span class="nigaa-summary-lbl">Total</span>
            </div>
            <div class="nigaa-summary-item nigaa-summary-warn">
              <span class="nigaa-summary-num">${pendingCount}</span>
              <span class="nigaa-summary-lbl">Pending</span>
            </div>
            <div class="nigaa-summary-item nigaa-summary-info">
              <span class="nigaa-summary-num">${updatesCount}</span>
              <span class="nigaa-summary-lbl">Today's Updates</span>
            </div>
            <div class="nigaa-summary-item nigaa-summary-success">
              <span class="nigaa-summary-num">${stats.closed || 0}</span>
              <span class="nigaa-summary-lbl">Closed</span>
            </div>
          </div>
          <div class="nigaa-summary-message">${escHtml(data.message || '')}</div>
          <div class="nigaa-summary-links">
            <a href="/petitions" class="nigaa-view-all-link">View all petitions →</a>
            <a href="/analysis-report" class="nigaa-view-all-link">Full report →</a>
          </div>
        `;
        wrap.appendChild(card);
        appendMsg(wrap);
    }

    /* ─── Urgent / Overdue card ──────────────────── */
    function addUrgentCard(data) {
        const wrap = makeBotWrap();
        const card = document.createElement('div');
        card.className = 'nigaa-card nigaa-urgent-card';
        card.innerHTML = `
          <div class="nigaa-card-title">🚨 Urgent / SLA Breach</div>
          <div class="nigaa-urgent-msg">${escHtml(data.message || 'Review petitions beyond SLA threshold.')}</div>
          <div class="nigaa-urgent-actions">
            <a href="${escHtml(data.url || '/petitions?status=beyond_sla')}" class="nigaa-urgent-btn" target="_blank">⚠️ View Overdue Petitions</a>
            <a href="${escHtml(data.sla_url || '/sla_dashboard')}" class="nigaa-urgent-btn nigaa-urgent-btn-sec" target="_blank">📊 SLA Dashboard</a>
          </div>
        `;
        wrap.appendChild(card);
        appendMsg(wrap);
    }

    /* ─── What Next / Smart Suggestions card ─────── */
    function addSuggestionCard(data) {
        const wrap = makeBotWrap();
        const card = document.createElement('div');
        card.className = 'nigaa-card nigaa-suggest-card';
        const titleEl = document.createElement('div');
        titleEl.className = 'nigaa-card-title';
        titleEl.textContent = '💡 Recommended Next Actions';
        card.appendChild(titleEl);
        const sub = document.createElement('div');
        sub.className = 'nigaa-suggest-subtitle';
        sub.textContent = `Here's what you should focus on, ${escHtml(data.user_name || '')}:`;
        card.appendChild(sub);
        (data.actions || []).forEach(action => {
            const item = document.createElement('div');
            item.className = `nigaa-suggest-action nigaa-suggest-${action.priority || 'low'}`;
            const priorityColors = { high: '#ef4444', medium: '#f59e0b', low: '#22c55e' };
            const pColor = priorityColors[action.priority] || '#6b7280';
            item.innerHTML = `
              <div class="nigaa-suggest-icon">${action.icon || '📌'}</div>
              <div class="nigaa-suggest-body">
                <div class="nigaa-suggest-title">
                  ${escHtml(action.title)}
                  <span class="nigaa-suggest-badge" style="background:${pColor}20;color:${pColor};border-color:${pColor}40">${(action.priority || 'low').toUpperCase()}</span>
                </div>
                <div class="nigaa-suggest-desc">${escHtml(action.desc)}</div>
                ${action.link ? `<a href="${escHtml(action.link)}" class="nigaa-suggest-link">${escHtml(action.link_label || 'View →')}</a>` : ''}
              </div>
            `;
            card.appendChild(item);
        });
        wrap.appendChild(card);
        appendMsg(wrap);
    }

    /* ─── Contextual suggestion chips ───────────── */
    function addSuggestionsChips(suggestions) {
        if (!suggestions || !suggestions.length) return;
        const container = document.createElement('div');
        container.className = 'nigaa-contextual-chips';
        const label = document.createElement('span');
        label.className = 'nigaa-chips-label';
        label.textContent = 'Try:';
        container.appendChild(label);
        suggestions.forEach(({ label: lbl, msg }) => {
            const btn = document.createElement('button');
            btn.className = 'nigaa-chip nigaa-context-chip';
            btn.textContent = lbl;
            btn.addEventListener('click', () => {
                inputEl.value = msg;
                handleSend();
            });
            container.appendChild(btn);
        });
        messagesEl.appendChild(container);
        scrollToBottom();
        requestAnimationFrame(() => container.classList.add('visible'));
    }

    /* ─── Shared petition card builder ──────────── */
    function buildPetitionCard(p, showActionBtn = false) {
        const card = document.createElement('div');
        card.className = 'nigaa-petition-card';
        const color = STATUS_COLORS[p.status] || '#6b7280';
        card.innerHTML = `
          <div class="nigaa-petition-header">
            <span class="nigaa-petition-sno">${escHtml(p.sno)}</span>
            <span class="nigaa-petition-status" style="--sc:${color}">${escHtml(p.status_label)}</span>
          </div>
          <div class="nigaa-petition-name">${escHtml(p.petitioner_name)}</div>
          <div class="nigaa-petition-subject">${escHtml(p.subject)}</div>
          <div class="nigaa-petition-meta">
            ${p.efile_no !== '-'    ? `<span>📄 ${escHtml(p.efile_no)}</span>` : ''}
            ${p.ereceipt_no !== '-' ? `<span>🧾 ${escHtml(p.ereceipt_no)}</span>` : ''}
            ${p.place !== '-'       ? `<span>📍 ${escHtml(p.place)}</span>` : ''}
            <span>📅 ${escHtml(p.received_date)}</span>
          </div>
          <div class="nigaa-petition-actions">
            <a href="/petitions/${p.id}" class="nigaa-petition-link" target="_blank">View Details →</a>
            ${showActionBtn ? `<a href="/petitions/${p.id}" class="nigaa-action-btn" target="_blank">⚡ Take Action</a>` : ''}
          </div>
        `;
        return card;
    }

    /* ── Shared bot message wrapper ─────────────── */
    function makeBotWrap() {
        const wrap = document.createElement('div');
        wrap.className = 'nigaa-msg nigaa-msg-bot';
        const av = document.createElement('div');
        av.className = 'nigaa-msg-avatar';
        av.innerHTML = miniRobotSVG();
        wrap.appendChild(av);
        return wrap;
    }

    /* ═══════════════════════════════════════════════
       TYPING INDICATOR
    ══════════════════════════════════════════════ */
    function showTyping() {
        if (document.getElementById('nigaaTyping')) return;
        const wrap = document.createElement('div');
        wrap.className = 'nigaa-msg nigaa-msg-bot';
        wrap.id = 'nigaaTyping';
        const av = document.createElement('div');
        av.className = 'nigaa-msg-avatar';
        av.innerHTML = miniRobotSVG();
        wrap.appendChild(av);
        const bubble = document.createElement('div');
        bubble.className = 'nigaa-bubble nigaa-typing-bubble';
        bubble.innerHTML = '<span></span><span></span><span></span>';
        wrap.appendChild(bubble);
        messagesEl.appendChild(wrap);
        scrollToBottom();
    }
    function hideTyping() { document.getElementById('nigaaTyping')?.remove(); }

    /* ═══════════════════════════════════════════════
       UTILITIES
    ══════════════════════════════════════════════ */
    function appendMsg(el) {
        messagesEl.appendChild(el);
        scrollToBottom();
        requestAnimationFrame(() => el.classList.add('visible'));
    }

    function scrollToBottom() {
        requestAnimationFrame(() => { messagesEl.scrollTop = messagesEl.scrollHeight; });
    }

    function markdownLite(text) {
        return text
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/_(.+?)_/g, '<em>$1</em>')
            .replace(/`(.+?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
    }

    function escHtml(s) {
        return String(s || '')
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    /* ── Inline mini bear-bot SVG (matches mascot) ─ */
    function miniRobotSVG() {
        return `<svg width="28" height="28" viewBox="0 0 56 60" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="13" cy="13" r="9" fill="white"/>
          <circle cx="43" cy="13" r="9" fill="white"/>
          <circle cx="13" cy="13" r="5.5" fill="#eef0fa"/>
          <circle cx="43" cy="13" r="5.5" fill="#eef0fa"/>
          <circle cx="28" cy="28" r="20" fill="white"/>
          <rect x="11" y="19" width="34" height="19" rx="9.5" fill="#1e1b5e"/>
          <circle cx="21" cy="28" r="4.5" fill="#F59E0B"/>
          <circle cx="35" cy="28" r="4.5" fill="#F59E0B"/>
          <circle cx="22.5" cy="26.5" r="1.4" fill="white" opacity="0.5"/>
          <circle cx="36.5" cy="26.5" r="1.4" fill="white" opacity="0.5"/>
          <ellipse cx="28" cy="52" rx="14" ry="10" fill="white"/>
          <rect x="24" y="45" width="8" height="10" rx="4" fill="#1e1b5e" opacity="0.65"/>
        </svg>`;
    }

    /* ── Start ─────────────────────────────────── */
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
