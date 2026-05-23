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

    let chart           = null;
    let chartType       = 'bar';
    let openDropId      = null;
    let openTrigger     = null;
    let lastAllLabels   = [];
    let lastGroupLabels = [];
    let lastWorldData   = [];
    let lastPlayerData  = [];
    let lastChartData   = null;

    // ── Bootstrap ─────────────────────────────────────────────────────────────
    function init() {
        setupDieToggles();
        setupSessionSelect();
        setupChartTypeBtns();
        setupDataBtns();
        setupExpandBtn();
        setupWorldTrigger();
        setupPlayerTrigger();
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

            rebuildWorldDropdown();
            rebuildPlayerDropdown();
            updateCascade();
            updateHeadline(data);
            renderChart(data);
        } catch (e) {
            console.error('[Stats] load failed:', e);
        }
    }

    // ── Die toggles ───────────────────────────────────────────────────────────
    function setupDieToggles() {
        document.querySelectorAll('.stats-die-toggle').forEach(btn => {
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
        const el = document.getElementById('filter-session');
        if (!el) return;
        el.addEventListener('change', () => {
            state.sessionScope = el.value;
            resetLabelFilters();
            load();
        });
    }

    // ── World dropdown ────────────────────────────────────────────────────────
    function setupWorldTrigger() {
        const trigger = document.querySelector('.stats-ms-trigger[data-ms="world"]');
        if (!trigger) return;
        trigger.addEventListener('click', e => { e.stopPropagation(); toggleDrop('dd-world', trigger); });
    }

    function rebuildWorldDropdown() {
        const dropdown = document.getElementById('dd-world');
        const trigger  = document.querySelector('.stats-ms-trigger[data-ms="world"]');
        if (!dropdown) return;
        dropdown.innerHTML = '';

        const isAllSelected = state.worldIds.has('all');
        const isPartial     = !isAllSelected && state.worldIds.size > 0;
        dropdown.appendChild(makeAllOption(
            'All Worlds', isAllSelected, isPartial,
            () => { state.worldIds = new Set(['all']); rebuildWorldDropdown(); syncTrigger(trigger, state.worldIds, 'Worlds'); resetLabelFilters(); load(); }
        ));
        lastWorldData.forEach(w => {
            const id = String(w.id);
            dropdown.appendChild(makeItemOption(
                w.title, state.worldIds.has(id),
                () => { toggleMulti(state.worldIds, id); rebuildWorldDropdown(); syncTrigger(trigger, state.worldIds, 'Worlds'); resetLabelFilters(); load(); }
            ));
        });

        syncTrigger(trigger, state.worldIds, 'Worlds');
    }

    // ── Player dropdown ───────────────────────────────────────────────────────
    function setupPlayerTrigger() {
        const trigger = document.querySelector('.stats-ms-trigger[data-ms="player"]');
        if (!trigger) return;
        trigger.addEventListener('click', e => { e.stopPropagation(); toggleDrop('dd-player', trigger); });
    }

    function rebuildPlayerDropdown() {
        const dropdown = document.getElementById('dd-player');
        const trigger  = document.querySelector('.stats-ms-trigger[data-ms="player"]');
        if (!dropdown) return;
        dropdown.innerHTML = '';

        const isAllSelected = state.playerNames.has('all');
        const isPartial     = !isAllSelected && state.playerNames.size > 0;
        dropdown.appendChild(makeAllOption(
            'All Players', isAllSelected, isPartial,
            () => { state.playerNames = new Set(['all']); rebuildPlayerDropdown(); syncTrigger(trigger, state.playerNames, 'Players'); resetLabelFilters(); load(); }
        ));
        lastPlayerData.forEach(name => {
            dropdown.appendChild(makeItemOption(
                name, state.playerNames.has(name),
                () => { toggleMulti(state.playerNames, name); rebuildPlayerDropdown(); syncTrigger(trigger, state.playerNames, 'Players'); resetLabelFilters(); load(); }
            ));
        });

        syncTrigger(trigger, state.playerNames, 'Players');
    }

    // ── Cascade ───────────────────────────────────────────────────────────────
    function resetLabelFilters() {
        state.groupPhrases = new Set(['all']);
        state.labelFilter  = new Set(['all']);
        lastGroupLabels    = [];
    }

    function updateCascade() {
        const container = document.getElementById('stats-cascade-group');
        if (!container) return;
        container.innerHTML = '';

        const groups = findGroups(lastAllLabels);

        // Group (Roll Type) dropdown — appears when groups are detected or one is selected
        if (groups.length > 0 || !state.groupPhrases.has('all')) {
            const wrap    = makeCascadeWrap('Roll Type', 'stats-auto-badge');
            const trigger = wrap.querySelector('.stats-ms-trigger');
            const ddId    = 'stats-dd-group';
            const dropdown = makeCascadeDropdown(ddId);

            const isAllSelected = state.groupPhrases.has('all');
            const isPartial     = !isAllSelected && state.groupPhrases.size > 0;
            dropdown.appendChild(makeAllOption(
                'All Roll Types', isAllSelected, isPartial,
                () => { state.groupPhrases = new Set(['all']); state.labelFilter = new Set(['all']); lastGroupLabels = []; updateCascade(); load(); }
            ));
            groups.forEach(phrase => {
                dropdown.appendChild(makeItemOption(
                    phrase, state.groupPhrases.has(phrase),
                    () => { toggleMulti(state.groupPhrases, phrase); state.labelFilter = new Set(['all']); syncTrigger(trigger, state.groupPhrases, 'Roll Types'); updateCascade(); load(); }
                ));
            });

            syncTrigger(trigger, state.groupPhrases, 'Roll Types');
            trigger.addEventListener('click', e => { e.stopPropagation(); toggleDrop(ddId, trigger); });
            wrap.appendChild(dropdown);
            container.appendChild(wrap);
        }

        // Label dropdown — shown when a group is selected, or when there are no groups
        const showIndividual = !state.groupPhrases.has('all') || groups.length === 0;
        const indivLabels    = state.groupPhrases.has('all') ? lastAllLabels : lastGroupLabels;

        if (showIndividual && indivLabels.length > 0) {
            const wrap    = makeCascadeWrap('Label', 'stats-auto-badge');
            const trigger = wrap.querySelector('.stats-ms-trigger');
            const ddId    = 'stats-dd-label';
            const dropdown = makeCascadeDropdown(ddId);

            const isAllSelected = state.labelFilter.has('all');
            const isPartial     = !isAllSelected && state.labelFilter.size > 0;
            dropdown.appendChild(makeAllOption(
                'All Labels', isAllSelected, isPartial,
                () => { state.labelFilter = new Set(['all']); syncTrigger(trigger, state.labelFilter, 'Labels'); load(); }
            ));
            indivLabels.forEach(lbl => {
                dropdown.appendChild(makeItemOption(
                    lbl, state.labelFilter.has(lbl),
                    () => { toggleMulti(state.labelFilter, lbl); syncTrigger(trigger, state.labelFilter, 'Labels'); load(); }
                ));
            });

            syncTrigger(trigger, state.labelFilter, 'Labels');
            trigger.addEventListener('click', e => { e.stopPropagation(); toggleDrop(ddId, trigger); });
            wrap.appendChild(dropdown);
            container.appendChild(wrap);
        }
    }

    function makeCascadeWrap(labelText, badgeClass) {
        const wrap = document.createElement('div');
        wrap.className = 'stats-ms-wrap stats-cascade';

        const label = document.createElement('span');
        label.className = 'stats-ms-label';
        label.innerHTML = `${labelText} <span class="${badgeClass}">auto</span>`;

        const trigger = document.createElement('div');
        trigger.className = 'stats-ms-trigger';
        trigger.innerHTML = `<span class="stats-ms-trigger-text">All ${labelText}s</span><span class="stats-ms-trigger-arrow">&#9660;</span>`;

        wrap.appendChild(label);
        wrap.appendChild(trigger);
        return wrap;
    }

    function makeCascadeDropdown(id) {
        const dd = document.createElement('div');
        dd.className = 'stats-ms-dropdown';
        dd.id = id;
        return dd;
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
        set('stat-total', data.total || '—');
        set('stat-avg',   data.total ? (Math.round(data.average * 10) / 10) : '—');
        set('stat-high',  data.total ? data.highest : '—');
        set('stat-low',   data.total ? data.lowest  : '—');
    }

    // ── Chart ─────────────────────────────────────────────────────────────────
    function setupChartTypeBtns() {
        document.querySelectorAll('.stats-chart-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                document.querySelectorAll('.stats-chart-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                chartType = btn.dataset.type;
                if (lastChartData) renderChart(lastChartData);
            });
        });
    }

    function renderChart(data) {
        if (data) lastChartData = data;
        if (!lastChartData) return;
        const canvas = document.getElementById('stats-chart');
        if (!canvas) return;

        const keys   = Object.keys(lastChartData.distribution).map(Number).sort((a, b) => a - b);
        const values = keys.map(k => lastChartData.distribution[String(k)]);

        if (chart) { chart.destroy(); chart = null; }

        if (keys.length === 0) {
            canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
            positionExpandBtn();
            return;
        }

        const palette    = genPalette(keys.length);
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
                    borderWidth:     1,
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
                    legend: { display: isDoughnut },
                    tooltip: {
                        callbacks: {
                            title: items => `Rolled ${items[0].label}`,
                            label: item  => ` ${item.raw} time${item.raw !== 1 ? 's' : ''}`,
                        },
                    },
                },
                scales: isDoughnut ? {} : {
                    x: { ticks: { color: '#8b949e', font: { size: 9 } }, grid: { color: 'rgba(255,255,255,0.05)' } },
                    y: { ticks: { color: '#8b949e', font: { size: 9 }, stepSize: 1 }, grid: { color: 'rgba(255,255,255,0.05)' }, beginAtZero: true },
                },
            },
        });

        positionExpandBtn();
    }

    function genPalette(n) {
        return Array.from({ length: n }, (_, i) => {
            const t = n === 1 ? 0.5 : i / (n - 1);
            return `hsl(272, ${Math.round(75 + t * 10)}%, ${Math.round(80 - t * 62)}%)`;
        });
    }

    // ── Expand button ─────────────────────────────────────────────────────────
    function setupExpandBtn() {
        document.getElementById('stats-chart-expand-btn')?.addEventListener('click', () => {
            // expand modal placeholder — not yet implemented
        });
    }

    function positionExpandBtn() {
        const btn = document.getElementById('stats-chart-expand-btn');
        if (!btn) return;
        if (chartType !== 'doughnut' || !chart) {
            btn.style.display = 'none';
            return;
        }
        const ca = chart.chartArea;
        if (!ca) { btn.style.display = 'none'; return; }
        btn.style.left    = ((ca.left + ca.right)  / 2) + 'px';
        btn.style.top     = ((ca.top  + ca.bottom) / 2) + 'px';
        btn.style.display = 'flex';
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
    function makeAllOption(label, isSelected, isPartial, onClick) {
        const el = document.createElement('div');
        el.className = 'stats-ms-option all-option' +
            (isSelected ? ' selected' : '') +
            (isPartial  ? ' partial'  : '');
        el.innerHTML = `<span class="stats-ms-check">${isSelected ? '<i class="fas fa-check"></i>' : ''}</span>${label}`;
        el.addEventListener('click', e => { e.stopPropagation(); onClick(); });
        return el;
    }

    function makeItemOption(label, isSelected, onClick) {
        const el = document.createElement('div');
        el.className = 'stats-ms-option' + (isSelected ? ' selected' : '');
        el.innerHTML = `<span class="stats-ms-check">${isSelected ? '<i class="fas fa-check"></i>' : ''}</span>${label}`;
        el.addEventListener('click', e => { e.stopPropagation(); onClick(); });
        return el;
    }

    function syncTrigger(trigger, set, noun) {
        if (!trigger) return;
        const textEl = trigger.querySelector('.stats-ms-trigger-text');
        if (!textEl) return;
        const isAll = set.has('all') || set.size === 0;
        textEl.textContent = isAll ? `All ${noun}` : `${set.size} ${noun}`;
        trigger.classList.toggle('has-value', !isAll);
    }

    function toggleMulti(set, value) {
        set.delete('all');
        if (set.has(value)) { set.delete(value); if (set.size === 0) set.add('all'); }
        else                { set.add(value); }
    }

    function toggleDrop(id, trigger) {
        const dropdown = document.getElementById(id);
        if (!dropdown) return;
        const isOpen = dropdown.classList.contains('open');

        // Close any currently open dropdown
        if (openDropId) {
            document.getElementById(openDropId)?.classList.remove('open');
            if (openTrigger) openTrigger.classList.remove('open');
        }

        if (!isOpen || openDropId !== id) {
            dropdown.classList.add('open');
            if (trigger) trigger.classList.add('open');
            openDropId  = id;
            openTrigger = trigger || null;
        } else {
            openDropId  = null;
            openTrigger = null;
        }
    }

    function onOutsideClick(e) {
        if (!openDropId) return;
        if (e.target.closest('.stats-ms-wrap') || e.target.closest('.stats-cascade-group')) return;
        document.getElementById(openDropId)?.classList.remove('open');
        if (openTrigger) openTrigger.classList.remove('open');
        openDropId  = null;
        openTrigger = null;
    }

    // ── Start ─────────────────────────────────────────────────────────────────
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
    else init();
})();
