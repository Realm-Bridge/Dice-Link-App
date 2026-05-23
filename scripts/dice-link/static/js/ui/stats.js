'use strict';

(function () {
    const DIE_TYPES = ['d4', 'd6', 'd8', 'd10', 'd12', 'd20', 'd100'];

    // ── Filter state ──────────────────────────────────────────────────────────
    const state = {
        dieTypes:     new Set(DIE_TYPES),
        worldIds:     new Set(['all']),
        sessionScope: 'all',
        playerNames:  new Set(['all']),
        groupPhrases: new Set(['all']),
        labelFilter:  new Set(['all']),
    };

    let chart          = null;
    let chartType      = 'bar';
    let openDropId     = null;
    let lastAllLabels  = [];  // labels when no label/group filter active
    let lastGroupLabels = []; // labels when group filter active, no individual filter
    let lastWorldData  = [];  // worlds for group dropdown
    let lastPlayerData = [];  // players for player dropdown

    // ── Bootstrap ─────────────────────────────────────────────────────────────
    function init() {
        setupDieToggles();
        setupSessionSelect();
        setupChartTypeBtns();
        setupDataBtns();
        document.addEventListener('click', onOutsideClick);
        load();
    }

    // ── API ───────────────────────────────────────────────────────────────────
    function buildLabelParam() {
        if (!state.labelFilter.has('all')) return [...state.labelFilter].join(',');
        if (!state.groupPhrases.has('all')) return [...state.groupPhrases].join(',');
        return 'all';
    }

    async function load() {
        const p = new URLSearchParams({
            die_types:     state.dieTypes.size === DIE_TYPES.length ? 'all' : [...state.dieTypes].join(','),
            world_ids:     state.worldIds.has('all')    ? 'all' : [...state.worldIds].join(','),
            session_scope: state.sessionScope,
            player_names:  state.playerNames.has('all') ? 'all' : [...state.playerNames].join(','),
            label_filter:  buildLabelParam(),
        });
        try {
            const data = await fetch(`/api/roll-stats?${p}`).then(r => r.json());

            // Store label snapshots
            if (state.labelFilter.has('all')) {
                if (state.groupPhrases.has('all')) {
                    lastAllLabels   = data.labels;
                    lastGroupLabels = [];
                } else {
                    lastGroupLabels = data.labels;
                }
            }

            lastWorldData  = data.worlds;
            lastPlayerData = data.players;

            rebuildWorldPanel();
            rebuildPlayerPanel();
            updateCascade();
            updateHeadline(data);
            renderChart(data);
        } catch (e) {
            console.error('[Stats] load failed:', e);
        }
    }

    // ── Die toggles ───────────────────────────────────────────────────────────
    function setupDieToggles() {
        document.querySelectorAll('.stats-die-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const die = btn.dataset.die;
                if (state.dieTypes.has(die)) {
                    if (state.dieTypes.size > 1) state.dieTypes.delete(die);
                } else {
                    state.dieTypes.add(die);
                }
                btn.classList.toggle('active', state.dieTypes.has(die));
                resetLabelFilters();
                load();
            });
        });
    }

    // ── Session select ────────────────────────────────────────────────────────
    function setupSessionSelect() {
        const el = document.getElementById('stats-session-select');
        if (!el) return;
        el.addEventListener('change', () => {
            state.sessionScope = el.value;
            resetLabelFilters();
            load();
        });
    }

    // ── World dropdown ────────────────────────────────────────────────────────
    function rebuildWorldPanel() {
        const panel = document.getElementById('stats-world-panel');
        const btn   = document.getElementById('stats-world-btn');
        if (!panel) return;
        panel.innerHTML = '';
        panel.appendChild(makeCheckItem(
            state.worldIds.has('all'), 'All Campaigns',
            () => { state.worldIds = new Set(['all']); rebuildWorldPanel(); syncDropBtn(btn, state.worldIds, 'Campaigns'); resetLabelFilters(); load(); }
        ));
        lastWorldData.forEach(w => {
            const id = String(w.id);
            panel.appendChild(makeCheckItem(
                state.worldIds.has(id), w.title,
                () => { toggleMulti(state.worldIds, id); rebuildWorldPanel(); syncDropBtn(btn, state.worldIds, 'Campaigns'); resetLabelFilters(); load(); }
            ));
        });
        syncDropBtn(btn, state.worldIds, 'Campaigns');
    }

    // ── Player dropdown ───────────────────────────────────────────────────────
    function rebuildPlayerPanel() {
        const panel = document.getElementById('stats-player-panel');
        const btn   = document.getElementById('stats-player-btn');
        if (!panel) return;
        panel.innerHTML = '';
        panel.appendChild(makeCheckItem(
            state.playerNames.has('all'), 'All Players',
            () => { state.playerNames = new Set(['all']); rebuildPlayerPanel(); syncDropBtn(btn, state.playerNames, 'Players'); resetLabelFilters(); load(); }
        ));
        lastPlayerData.forEach(p => {
            panel.appendChild(makeCheckItem(
                state.playerNames.has(p), p,
                () => { toggleMulti(state.playerNames, p); rebuildPlayerPanel(); syncDropBtn(btn, state.playerNames, 'Players'); resetLabelFilters(); load(); }
            ));
        });
        syncDropBtn(btn, state.playerNames, 'Players');
    }

    // ── Cascade ───────────────────────────────────────────────────────────────
    function resetLabelFilters() {
        state.groupPhrases = new Set(['all']);
        state.labelFilter  = new Set(['all']);
        lastGroupLabels    = [];
    }

    function updateCascade() {
        const container = document.getElementById('stats-cascade');
        if (!container) return;
        container.innerHTML = '';

        // Group dropdown — built from labels with no label filtering
        const sourceLabels = lastAllLabels;
        const groups = findGroups(sourceLabels);

        if (groups.length > 0 || !state.groupPhrases.has('all')) {
            const groupWrap  = document.createElement('div');
            groupWrap.className = 'stats-drop-wrap';
            const groupBtn   = document.createElement('button');
            groupBtn.className = 'stats-filter-btn';
            groupBtn.id = 'stats-group-btn';
            syncDropBtn(groupBtn, state.groupPhrases, 'Groups');
            const groupPanel = document.createElement('div');
            groupPanel.className = 'stats-drop-panel hidden';
            groupPanel.id = 'stats-group-panel';

            groupPanel.appendChild(makeCheckItem(
                state.groupPhrases.has('all'), 'All Groups',
                () => { state.groupPhrases = new Set(['all']); state.labelFilter = new Set(['all']); lastGroupLabels = []; updateCascade(); load(); }
            ));
            groups.forEach(phrase => {
                groupPanel.appendChild(makeCheckItem(
                    state.groupPhrases.has(phrase), phrase,
                    () => {
                        toggleMulti(state.groupPhrases, phrase);
                        state.labelFilter = new Set(['all']);
                        syncDropBtn(groupBtn, state.groupPhrases, 'Groups');
                        updateCascade();
                        load();
                    }
                ));
            });

            groupBtn.addEventListener('click', e => { e.stopPropagation(); toggleDrop('stats-group-panel'); });
            groupWrap.appendChild(groupBtn);
            groupWrap.appendChild(groupPanel);
            container.appendChild(groupWrap);
        }

        // Individual label dropdown — shown when a group is selected (or no groups at all)
        const showIndividual = !state.groupPhrases.has('all') || groups.length === 0;
        const indivLabels = state.groupPhrases.has('all') ? lastAllLabels : lastGroupLabels;

        if (showIndividual && indivLabels.length > 0) {
            const labWrap  = document.createElement('div');
            labWrap.className = 'stats-drop-wrap';
            const labBtn   = document.createElement('button');
            labBtn.className = 'stats-filter-btn';
            labBtn.id = 'stats-label-btn';
            syncDropBtn(labBtn, state.labelFilter, 'Labels');
            const labPanel = document.createElement('div');
            labPanel.className = 'stats-drop-panel hidden';
            labPanel.id = 'stats-label-panel';

            labPanel.appendChild(makeCheckItem(
                state.labelFilter.has('all'), 'All Labels',
                () => { state.labelFilter = new Set(['all']); syncDropBtn(labBtn, state.labelFilter, 'Labels'); load(); }
            ));
            indivLabels.forEach(label => {
                labPanel.appendChild(makeCheckItem(
                    state.labelFilter.has(label), label,
                    () => { toggleMulti(state.labelFilter, label); syncDropBtn(labBtn, state.labelFilter, 'Labels'); load(); }
                ));
            });

            labBtn.addEventListener('click', e => { e.stopPropagation(); toggleDrop('stats-label-panel'); });
            labWrap.appendChild(labBtn);
            labWrap.appendChild(labPanel);
            container.appendChild(labWrap);
        }
    }

    function findGroups(labels) {
        if (!labels || labels.length < 2) return [];
        const counts = {};
        labels.forEach(label => {
            const words = label.split(/\s+/);
            for (let len = 2; len <= 4; len++) {
                for (let i = 0; i <= words.length - len; i++) {
                    const phrase = words.slice(i, i + len).join(' ');
                    counts[phrase] = (counts[phrase] || 0) + 1;
                }
            }
        });
        return Object.entries(counts)
            .filter(([, n]) => n >= 2)
            .sort((a, b) => b[1] - a[1])
            .map(([p]) => p);
    }

    // ── Headline numbers ──────────────────────────────────────────────────────
    function updateHeadline(data) {
        const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
        set('stats-total',   data.total || '—');
        set('stats-avg',     data.total ? (Math.round(data.average * 10) / 10) : '—');
        set('stats-highest', data.total ? data.highest : '—');
        set('stats-lowest',  data.total ? data.lowest  : '—');
    }

    // ── Chart ─────────────────────────────────────────────────────────────────
    function setupChartTypeBtns() {
        document.querySelectorAll('.stats-chart-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.stats-chart-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                chartType = btn.dataset.chart;
                if (lastChartData) renderChart(lastChartData);
            });
        });
    }

    let lastChartData = null;

    function renderChart(data) {
        if (data) lastChartData = data;
        if (!lastChartData) return;
        const canvas = document.getElementById('stats-chart');
        if (!canvas) return;

        const keys    = Object.keys(lastChartData.distribution).map(Number).sort((a, b) => a - b);
        const values  = keys.map(k => lastChartData.distribution[String(k)]);

        if (chart) { chart.destroy(); chart = null; }

        if (keys.length === 0) {
            canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
            return;
        }

        const palette = genPalette(keys.length);
        const isDoughnut = chartType === 'doughnut';
        const isLine     = chartType === 'line';

        chart = new Chart(canvas, {
            type: chartType,
            data: {
                labels: keys,
                datasets: [{
                    data:            values,
                    backgroundColor: isDoughnut ? palette : 'rgba(111,46,154,0.7)',
                    borderColor:     isDoughnut ? palette : 'rgba(111,46,154,1)',
                    borderWidth:     isDoughnut ? 1 : 1,
                    tension:         isLine ? 0.3 : undefined,
                    fill:            isLine,
                    pointRadius:     isLine ? 3 : undefined,
                }],
            },
            options: {
                responsive:          true,
                maintainAspectRatio: false,
                animation:           false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            title: items => `Rolled ${items[0].label}`,
                            label: item  => ` ${item.raw} time${item.raw !== 1 ? 's' : ''}`,
                        },
                    },
                },
                scales: isDoughnut ? {} : {
                    x: { ticks: { color: '#8b949e', font: { size: 12 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y: { ticks: { color: '#8b949e', font: { size: 12 }, stepSize: 1 }, grid: { color: 'rgba(255,255,255,0.05)' }, beginAtZero: true },
                },
            },
        });
    }

    function genPalette(n) {
        return Array.from({ length: n }, (_, i) => {
            const t = n === 1 ? 0.5 : i / (n - 1);
            return `hsl(272, ${Math.round(75 + t * 10)}%, ${Math.round(80 - t * 62)}%)`;
        });
    }

    // ── Data buttons ──────────────────────────────────────────────────────────
    function setupDataBtns() {
        document.getElementById('stats-clear-btn')?.addEventListener('click',  showClearConfirm);
        document.getElementById('stats-clear-yes')?.addEventListener('click',  executeClear);
        document.getElementById('stats-clear-no')?.addEventListener('click',   hideClearConfirm);
        document.getElementById('stats-export-btn')?.addEventListener('click', doExport);
        document.getElementById('stats-import-btn')?.addEventListener('click', () => document.getElementById('stats-import-input')?.click());
        document.getElementById('stats-import-input')?.addEventListener('change', doImport);
    }

    function showClearConfirm() { document.getElementById('stats-clear-confirm')?.classList.remove('hidden'); }
    function hideClearConfirm() { document.getElementById('stats-clear-confirm')?.classList.add('hidden'); }

    async function executeClear() {
        hideClearConfirm();
        const p = new URLSearchParams({
            die_types:     state.dieTypes.size === DIE_TYPES.length ? 'all' : [...state.dieTypes].join(','),
            world_ids:     state.worldIds.has('all')    ? 'all' : [...state.worldIds].join(','),
            session_scope: state.sessionScope,
            player_names:  state.playerNames.has('all') ? 'all' : [...state.playerNames].join(','),
            label_filter:  buildLabelParam(),
        });
        await fetch(`/api/roll-stats?${p}`, { method: 'DELETE' });
        resetLabelFilters();
        load();
    }

    async function doExport() {
        const p = new URLSearchParams({
            die_types:     state.dieTypes.size === DIE_TYPES.length ? 'all' : [...state.dieTypes].join(','),
            world_ids:     state.worldIds.has('all')    ? 'all' : [...state.worldIds].join(','),
            session_scope: state.sessionScope,
            player_names:  state.playerNames.has('all') ? 'all' : [...state.playerNames].join(','),
            label_filter:  buildLabelParam(),
        });
        const resp = await fetch(`/api/roll-stats/export?${p}`);
        const blob = await resp.blob();
        const cd   = resp.headers.get('Content-Disposition') || '';
        const name = cd.match(/filename=(.+)/)?.[1] || 'dice-stats.csv';
        const a    = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: name });
        a.click();
        URL.revokeObjectURL(a.href);
    }

    async function doImport(e) {
        const file = e.target.files[0];
        if (!file) return;
        const text    = await file.text();
        const lines   = text.trim().split('\n');
        const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
        const rows    = lines.slice(1).map(line => {
            const vals = line.split(',').map(v => v.trim().replace(/^"|"$/g, ''));
            return Object.fromEntries(headers.map((h, i) => [h, vals[i] ?? '']));
        });
        await fetch('/api/roll-stats/import', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rows }),
        });
        e.target.value = '';
        resetLabelFilters();
        load();
    }

    // ── Dropdown helpers ──────────────────────────────────────────────────────
    function makeCheckItem(checked, label, onChange) {
        const item = document.createElement('label');
        item.className = 'stats-drop-item';
        const cb = document.createElement('input');
        cb.type    = 'checkbox';
        cb.checked = checked;
        cb.addEventListener('change', onChange);
        item.appendChild(cb);
        item.appendChild(document.createTextNode(' ' + label));
        return item;
    }

    function syncDropBtn(btn, set, noun) {
        if (!btn) return;
        btn.textContent = (set.has('all') || set.size === 0) ? `All ${noun}` : `${set.size} ${noun}`;
    }

    function toggleMulti(set, value) {
        set.delete('all');
        if (set.has(value)) { set.delete(value); if (set.size === 0) set.add('all'); }
        else                { set.add(value); }
    }

    function toggleDrop(id) {
        const panel = document.getElementById(id);
        if (!panel) return;
        const isOpen = !panel.classList.contains('hidden');
        if (openDropId && openDropId !== id) document.getElementById(openDropId)?.classList.add('hidden');
        panel.classList.toggle('hidden', isOpen);
        openDropId = isOpen ? null : id;
    }

    function onOutsideClick(e) {
        if (openDropId && !e.target.closest('.stats-drop-wrap')) {
            document.getElementById(openDropId)?.classList.add('hidden');
            openDropId = null;
        }
    }

    // Expose toggleDrop for inline onclick on static dropdowns
    window.statsToggleDrop = toggleDrop;

    // ── Start ─────────────────────────────────────────────────────────────────
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();
