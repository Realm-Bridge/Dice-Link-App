'use strict';

(function () {

// ══════════════════════════════════════════════════════════════
// LIVE DATA STATE
// ══════════════════════════════════════════════════════════════
let currentData = { labels: [], values: [], total: 0, average: '—' };

let activeDie        = 20;
let currentChartType = 'bar';
let modalChart       = null;
let allLabels        = [];
const cascadeFilters = { rollType: new Set(), label: new Set(), variant: new Set() };

// ══════════════════════════════════════════════════════════════
// COMBAT TRACKER DATA
// ══════════════════════════════════════════════════════════════
const combatants = [
    { name:'Aelindra',      init:24, hp:45, maxHp:62,  ac:16, color:'#7048d8', isPlayer:true,  hpPublic:true,  acPublic:true,  conditions:[] },
    { name:'Orc Chieftain', init:21, hp:85, maxHp:120, ac:14, color:'#b91c1c', isPlayer:false, hpPublic:false, acPublic:false, conditions:['frightened'] },
    { name:'Tordek',        init:18, hp:28, maxHp:55,  ac:18, color:'#2563eb', isPlayer:true,  hpPublic:true,  acPublic:true,  conditions:['poisoned'] },
    { name:'Skeleton',      init:15, hp:0,  maxHp:13,  ac:13, color:'#64748b', isPlayer:false, hpPublic:false, acPublic:false, conditions:[] },
    { name:'Mira',          init:12, hp:38, maxHp:38,  ac:12, color:'#059669', isPlayer:true,  hpPublic:true,  acPublic:true,  conditions:[] },
    { name:'Orc Grunt',     init:8,  hp:15, maxHp:30,  ac:11, color:'#d97706', isPlayer:false, hpPublic:false, acPublic:false, conditions:['stunned'] },
    { name:'Zephyr',        init:5,  hp:52, maxHp:58,  ac:15, color:'#7c3aed', isPlayer:true,  hpPublic:true,  acPublic:true,  conditions:[] },
];

let ctTurn  = 0;
let ctRound = 3;
let ctIsGM  = true;

const ctPos = {
    '-3':{ x:-315, y:58, scale:0.37, opacity:0.18 },
    '-2':{ x:-222, y:36, scale:0.54, opacity:0.46 },
    '-1':{ x:-126, y:16, scale:0.73, opacity:0.74 },
     '0':{ x:0,   y:0,  scale:1.00, opacity:1.00 },
     '1':{ x:126,  y:16, scale:0.73, opacity:0.74 },
     '2':{ x:222,  y:36, scale:0.54, opacity:0.46 },
     '3':{ x:315,  y:58, scale:0.37, opacity:0.18 },
};

const ctCondIcons = {
    poisoned:'fa-skull-crossbones', stunned:'fa-bolt', frightened:'fa-ghost',
    prone:'fa-arrow-down', blinded:'fa-eye-slash', charmed:'fa-heart',
};

// ══════════════════════════════════════════════════════════════
// WINDOW-LEVEL HANDLERS (for onclick= attributes)
// ══════════════════════════════════════════════════════════════
window.statsFlipPanel = function () {
    const flipper = document.getElementById('stats-panel-flipper');
    const label   = document.getElementById('stats-ext-label');
    const flipped = flipper.classList.toggle('flipped');
    if (label) {
        label.innerHTML = flipped
            ? '<i class="fas fa-shield-alt"></i> Combat Tracker'
            : '<i class="fas fa-chart-bar"></i> Dice Roll Stats';
    }
};

window.ctNextTurn = function () {
    ctTurn = (ctTurn + 1) % combatants.length;
    if (ctTurn === 0) ctRound++;
    ctRenderAll();
};

window.ctPrevTurn = function () {
    const prev = ctTurn;
    ctTurn = (ctTurn - 1 + combatants.length) % combatants.length;
    if (prev === 0) ctRound = Math.max(1, ctRound - 1);
    ctRenderAll();
};

window.ctToggleView = function () {
    ctIsGM = !ctIsGM;
    document.getElementById('ct-view-btn').innerHTML =
        `<i class="fas fa-eye${ctIsGM ? '' : '-slash'}"></i> ${ctIsGM ? 'GM View' : 'Player View'}`;
    ctRenderAll();
};

// ══════════════════════════════════════════════════════════════
// INITIALISE (after DOM ready)
// ══════════════════════════════════════════════════════════════
function init() {

    // ── Chart setup ──────────────────────────────────────────
    const canvas = document.getElementById('statsChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    function makeBarGrad(context) {
        const g = context.createLinearGradient(0, 0, 0, 220);
        g.addColorStop(0, 'rgba(167,139,250,0.95)');
        g.addColorStop(1, 'rgba(111,46,154,0.5)');
        return g;
    }

    function generateDonutPalette(n) {
        const colors = [];
        for (let i = 0; i < n; i++) {
            const t = n === 1 ? 0.5 : i / (n - 1);
            const lightness  = Math.round(80 - t * 62);
            const saturation = Math.round(75 + t * 10);
            colors.push(`hsl(272, ${saturation}%, ${lightness}%)`);
        }
        return colors;
    }

    const axisDefaults = {
        x: { grid:{ color:'rgba(255,255,255,0.04)' }, ticks:{ color:'#6e7681', font:{ size:9 } }, border:{ color:'rgba(255,255,255,0.08)' } },
        y: { grid:{ color:'rgba(255,255,255,0.06)' }, ticks:{ color:'#6e7681', font:{ size:9 }, stepSize:1 }, border:{ color:'rgba(255,255,255,0.08)' }, beginAtZero:true }
    };

    const smallDonutLegend = { display: false };

    const largeDonutLegend = {
        display: true, position: 'right',
        labels: { color: '#e7f6ff', font:{ size: 14 }, boxWidth: 20, padding: 14 }
    };

    function buildDataset(type, context) {
        if (type === 'bar') return {
            label: `d${activeDie}`, data: currentData.values,
            backgroundColor: makeBarGrad(context),
            borderWidth: 0, borderRadius: 3, borderSkipped: false
        };
        if (type === 'line') return {
            label: `d${activeDie}`, data: currentData.values,
            backgroundColor: 'rgba(111,46,154,0.18)', borderColor: '#a78bfa',
            borderWidth: 2, fill: true, tension: 0.35,
            pointBackgroundColor: '#a78bfa', pointRadius: 3, pointHoverRadius: 5
        };
        return {
            label: `d${activeDie}`, data: currentData.values,
            backgroundColor: generateDonutPalette(currentData.values.length),
            borderColor: '#2a3547', borderWidth: 2, hoverOffset: 6
        };
    }

    const chart = new Chart(ctx, {
        type: 'bar',
        data: { labels: [], datasets: [] },
        options: {
            responsive: true, maintainAspectRatio: false, animation: { duration: 200 },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor:'#1a1f26', titleColor:'#a78bfa', bodyColor:'#f0f2f5',
                    borderColor:'#6f2e9a', borderWidth:1, padding:7,
                    callbacks: {
                        title: i => `Face value: ${i[0].label}`,
                        label: i => `  ${i.raw} roll${i.raw !== 1 ? 's' : ''}`
                    }
                }
            },
            scales: axisDefaults
        }
    });

    function positionExpandBtn() {
        const btn = document.getElementById('stats-chart-expand-btn');
        if (!btn) return;
        btn.classList.toggle('visible', currentChartType === 'doughnut');
    }

    function refreshDonutLegend() {
        const el = document.getElementById('stats-donut-legend');
        if (!el) return;
        if (currentChartType !== 'doughnut') { el.classList.remove('visible'); return; }

        const colors = generateDonutPalette(currentData.values.length);
        const n      = currentData.labels.length;
        const half   = Math.ceil(n / 2);
        const items  = currentData.labels.map((lbl, i) => ({ label: lbl, color: colors[i] }));

        function makeCol(slice) {
            const col = document.createElement('div');
            col.className = 'sdl-col';
            slice.forEach(({ label, color }) => {
                const row = document.createElement('div');
                row.className = 'sdl-item';
                row.innerHTML = `<span class="sdl-swatch" style="background:${color}"></span>${label}`;
                col.appendChild(row);
            });
            return col;
        }

        const wrap = document.createElement('div');
        wrap.className = 'sdl-cols';
        if (n <= 10) {
            wrap.appendChild(makeCol(items));
        } else {
            wrap.appendChild(makeCol(items.slice(0, half)));
            wrap.appendChild(makeCol(items.slice(half)));
        }

        el.innerHTML = '';
        el.appendChild(wrap);
        el.classList.add('visible');
    }

    function refreshChart(type) {
        chart.config.type    = type;
        chart.data.labels    = currentData.labels;
        chart.data.datasets  = currentData.labels.length ? [buildDataset(type, ctx)] : [];
        chart.options.scales = type === 'doughnut' ? {} : axisDefaults;
        chart.options.plugins.legend = smallDonutLegend;
        chart.update();

        document.getElementById('stat-total').textContent = currentData.total;
        document.getElementById('stat-avg').textContent   = currentData.average;

        refreshDonutLegend();
        positionExpandBtn();
    }

    function buildFilterParams() {
        const params = new URLSearchParams({ die_types: 'd' + activeDie });
        const sessionEl = document.getElementById('filter-session');
        if (sessionEl && sessionEl.value !== 'all') params.set('session_scope', sessionEl.value);
        if (msWorld.selected.size  > 0) params.set('world_ids',    [...msWorld.selected].join(','));
        if (msPlayer.selected.size > 0) params.set('player_names', [...msPlayer.selected].join(','));
        const labelSel = cascadeFilters.variant.size  > 0 ? cascadeFilters.variant
                       : cascadeFilters.label.size    > 0 ? cascadeFilters.label
                       : cascadeFilters.rollType.size > 0 ? cascadeFilters.rollType
                       : null;
        if (labelSel) params.set('label_filter', [...labelSel].join(','));
        return params;
    }

    async function fetchAndRender() {
        const params = buildFilterParams();

        try {
            const res  = await fetch(`/api/roll-stats?${params}`);
            const data = await res.json();

            const dist = data.distribution || {};
            const keys = Object.keys(dist).sort((a, b) => parseInt(a) - parseInt(b));
            currentData = {
                labels:  keys,
                values:  keys.map(k => dist[k]),
                total:   data.total   || 0,
                average: data.average != null ? String(data.average) : '—',
            };

            refreshChart(currentChartType);
            allLabels = data.labels || [];
            updateCascade();
            populateDropdown(msWorld,  data.worlds  || [], w => String(w.id), w => w.title);
            populateDropdown(msPlayer, data.players || [], p => p,            p => p);
        } catch (err) {
            console.error('[Stats] fetchAndRender failed:', err);
        }
    }

    function populateDropdown(ms, items, valueFn, labelFn) {
        ms.dropdown.querySelectorAll('.stats-ms-option:not(.all-option)').forEach(el => el.remove());
        const newValues = new Set(items.map(valueFn));
        for (const s of [...ms.selected]) {
            if (!newValues.has(s)) ms.selected.delete(s);
        }
        items.forEach(item => {
            const val = valueFn(item);
            const lbl = labelFn(item);
            const div = document.createElement('div');
            div.className    = 'stats-ms-option';
            div.dataset.value = val;
            div.innerHTML    = `<span class="stats-ms-check"></span>${lbl}`;
            div.addEventListener('click', e => {
                e.stopPropagation();
                ms.selected.has(val) ? ms.selected.delete(val) : ms.selected.add(val);
                ms._renderOnly();
                fetchAndRender();
            });
            ms.dropdown.appendChild(div);
        });
        ms._renderOnly();
    }

    // ── Cascade helpers ───────────────────────────────────────

    function findGroups(labels, excludedPhrases = []) {
        if (labels.length < 2) return [];
        const excluded    = new Set(excludedPhrases.map(p => p.toLowerCase()));
        const phraseCount = new Map();
        labels.forEach(label => {
            const words = label.trim().split(/\s+/);
            const seen  = new Set();
            for (let len = 2; len <= 3; len++) {
                for (let i = 0; i <= words.length - len; i++) {
                    const phrase = words.slice(i, i + len).join(' ');
                    if (!excluded.has(phrase.toLowerCase()) && !seen.has(phrase)) {
                        seen.add(phrase);
                        phraseCount.set(phrase, (phraseCount.get(phrase) || 0) + 1);
                    }
                }
            }
        });
        // Phrases that cover ALL labels are not differentiating — exclude them
        const candidates = [...phraseCount.entries()]
            .filter(([, count]) => count >= 2 && count < labels.length)
            .sort((a, b) => b[1] - a[1] || b[0].length - a[0].length)
            .map(([phrase]) => phrase);
        // Deduplication: discard phrase A if a longer phrase B covers the same label set
        const phraseLabels = new Map(candidates.map(p => [
            p, new Set(labels.filter(l => l.toLowerCase().includes(p.toLowerCase())))
        ]));
        return candidates.filter(pA => !candidates.some(pB => {
            if (pB === pA || pB.length <= pA.length) return false;
            if (!pB.toLowerCase().includes(pA.toLowerCase())) return false;
            const sA = phraseLabels.get(pA), sB = phraseLabels.get(pB);
            return sB.size === sA.size && [...sB].every(l => sA.has(l));
        }));
    }

    function stripLabel(fullLabel, phrases) {
        let text = fullLabel;
        for (const phrase of phrases) {
            text = text.replace(new RegExp(phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi'), '');
        }
        text = text.replace(/\s*\(\s*\)\s*/g, ' ')
                   .replace(/^\s*[\(\[\-\|]\s*/, '')
                   .replace(/\s*[\)\]\-\|]\s*$/, '')
                   .replace(/\s+/g, ' ')
                   .trim();
        return text || fullLabel;
    }

    function labelsMatchingPhrases(labels, phrases) {
        if (!phrases || phrases.size === 0) return labels;
        return labels.filter(l => [...phrases].some(p => l.includes(p)));
    }

    function setCascadeLevel(ms, items) {
        if (!ms || !ms.dropdown) return;
        ms.dropdown.querySelectorAll('.stats-ms-option:not(.all-option)').forEach(el => el.remove());
        const valueSet = new Set(items.map(i => typeof i === 'string' ? i : i.value));
        for (const s of [...ms.selected]) {
            if (!valueSet.has(s)) ms.selected.delete(s);
        }
        items.forEach(item => {
            const value = typeof item === 'string' ? item : item.value;
            const text  = typeof item === 'string' ? item : item.text;
            const div = document.createElement('div');
            div.className     = 'stats-ms-option';
            div.dataset.value = value;
            div.innerHTML     = `<span class="stats-ms-check"></span>${text}`;
            div.addEventListener('click', e => {
                e.stopPropagation();
                ms.selected.has(value) ? ms.selected.delete(value) : ms.selected.add(value);
                ms._renderOnly();
                onCascadeChange(ms);
            });
            ms.dropdown.appendChild(div);
        });
        ms._renderOnly();
    }

    function updateCascade() {
        // Level 1 — Roll Type: groups from all labels
        const l1Groups = findGroups(allLabels);
        setCascadeLevel(msRollType, l1Groups.length > 0 ? l1Groups : allLabels);

        // Level 2 — Label: sub-groups or stripped individual labels within Roll Type selection
        if (cascadeFilters.rollType.size > 0) {
            const l1Filtered = labelsMatchingPhrases(allLabels, cascadeFilters.rollType);
            const l2Groups   = findGroups(l1Filtered, [...cascadeFilters.rollType]);
            if (l2Groups.length > 0) {
                setCascadeLevel(msLabel, l2Groups);
            } else {
                setCascadeLevel(msLabel, l1Filtered.map(lbl => ({
                    value: lbl,
                    text:  stripLabel(lbl, [...cascadeFilters.rollType])
                })));
            }
        } else {
            setCascadeLevel(msLabel, allLabels);
        }

        // Level 3 — Variant: sub-groups or stripped individual labels within Label selection
        const variantWrap = document.getElementById('ms-variant');
        if (cascadeFilters.label.size > 0) {
            const l2Base      = cascadeFilters.rollType.size > 0
                ? labelsMatchingPhrases(allLabels, cascadeFilters.rollType)
                : allLabels;
            const l2Filtered  = labelsMatchingPhrases(l2Base, cascadeFilters.label);
            const usedPhrases = [...cascadeFilters.rollType, ...cascadeFilters.label];
            const l3Groups    = findGroups(l2Filtered, usedPhrases);
            if (l3Groups.length > 0) {
                setCascadeLevel(msVariant, l3Groups);
                if (variantWrap) variantWrap.style.display = '';
            } else {
                const stripped      = l2Filtered.map(lbl => ({ value: lbl, text: stripLabel(lbl, usedPhrases) }));
                const distinctTexts = new Set(stripped.map(s => s.text));
                if (distinctTexts.size > 1) {
                    setCascadeLevel(msVariant, stripped);
                    if (variantWrap) variantWrap.style.display = '';
                } else {
                    cascadeFilters.variant.clear();
                    setCascadeLevel(msVariant, []);
                    if (variantWrap) variantWrap.style.display = 'none';
                }
            }
        } else {
            cascadeFilters.variant.clear();
            setCascadeLevel(msVariant, []);
            if (variantWrap) variantWrap.style.display = 'none';
        }
    }

    function onCascadeChange(ms) {
        if (ms === msRollType) {
            cascadeFilters.rollType = new Set(ms.selected);
            cascadeFilters.label.clear();
            cascadeFilters.variant.clear();
            msLabel.selected.clear();
            msVariant.selected.clear();
        } else if (ms === msLabel) {
            cascadeFilters.label = new Set(ms.selected);
            cascadeFilters.variant.clear();
            msVariant.selected.clear();
        } else {
            cascadeFilters.variant = new Set(ms.selected);
        }
        updateCascade();
        fetchAndRender();
    }

    // ── Die picker ───────────────────────────────────────────
    const diePick = document.getElementById('die-pick');
    document.getElementById('die-pick-trigger')?.addEventListener('click', e => {
        e.stopPropagation();
        diePick.classList.toggle('open');
    });
    document.getElementById('die-pick-dd')?.querySelectorAll('.stats-die-pick-opt').forEach(opt => {
        opt.addEventListener('click', e => {
            e.stopPropagation();
            const val = parseInt(opt.dataset.die, 10);
            activeDie = val;
            document.getElementById('die-pick-icon').src = `/static/DLC Dice/D${val}/d${val}-blank.svg`;
            document.querySelectorAll('.stats-die-pick-opt').forEach(o => o.classList.remove('active'));
            opt.classList.add('active');
            diePick.classList.remove('open');
            fetchAndRender();
        });
    });

    // ── Chart type buttons ────────────────────────────────────
    document.querySelectorAll('.stats-chart-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.stats-chart-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentChartType = btn.dataset.type;
            refreshChart(currentChartType);
        });
    });

    // ── Chart modal ───────────────────────────────────────────
    function openModal() {
        const modal = document.getElementById('chart-modal');
        if (!modal) return;
        modal.classList.add('open');
        document.getElementById('modal-die-label').textContent = `d${activeDie}`;

        const mCtx = document.getElementById('statsChartModal').getContext('2d');

        if (modalChart) { modalChart.destroy(); modalChart = null; }

        modalChart = new Chart(mCtx, {
            type: 'doughnut',
            data: { labels: currentData.labels, datasets: [buildDataset('doughnut', mCtx)] },
            options: {
                responsive: true, maintainAspectRatio: false, animation: { duration: 300 },
                plugins: {
                    legend: largeDonutLegend,
                    tooltip: {
                        backgroundColor:'#1a1f26', titleColor:'#a78bfa', bodyColor:'#f0f2f5',
                        borderColor:'#6f2e9a', borderWidth:1, padding:10,
                        callbacks: {
                            title: i => `Face value: ${i[0].label}`,
                            label: i => `  ${i.raw} roll${i.raw !== 1 ? 's' : ''}`
                        }
                    }
                }
            }
        });
    }

    function closeModal() {
        document.getElementById('chart-modal')?.classList.remove('open');
        if (modalChart) { modalChart.destroy(); modalChart = null; }
    }

    document.getElementById('stats-chart-expand-btn')?.addEventListener('click', openModal);
    document.getElementById('chart-shrink-btn')?.addEventListener('click', closeModal);
    document.getElementById('chart-modal')?.addEventListener('click', function (e) {
        if (e.target === this) closeModal();
    });

    // ── MultiSelect dropdowns ────────────────────────────────
    const msWorld    = new MultiSelect('world',    'dd-world',    'All Worlds',      () => fetchAndRender());
    const msPlayer   = new MultiSelect('player',   'dd-player',   'All Players',     () => fetchAndRender());
    const msRollType = new MultiSelect('rolltype', 'dd-rolltype', 'All Roll Types',  ms => onCascadeChange(ms));
    const msLabel    = new MultiSelect('label',    'dd-label',    'All Labels',      ms => onCascadeChange(ms));
    const msVariant  = new MultiSelect('variant',  'dd-variant',  'All Variants',    ms => onCascadeChange(ms));

    document.getElementById('filter-session')?.addEventListener('change', fetchAndRender);

    document.addEventListener('click', () => {
        diePick?.classList.remove('open');
        [msWorld, msPlayer, msRollType, msLabel, msVariant].forEach(ms => ms.close());
    });

    // ── Clear / confirm ───────────────────────────────────────
    document.getElementById('stats-clear-btn')?.addEventListener('click', () => {
        document.getElementById('stats-clear-confirm')?.classList.remove('hidden');
    });
    document.getElementById('stats-clear-no')?.addEventListener('click', () => {
        document.getElementById('stats-clear-confirm')?.classList.add('hidden');
    });
    document.getElementById('stats-clear-yes')?.addEventListener('click', async () => {
        document.getElementById('stats-clear-confirm')?.classList.add('hidden');
        await fetch(`/api/roll-stats?${buildFilterParams()}`, { method: 'DELETE' });
        fetchAndRender();
    });

    // ── Export ────────────────────────────────────────────────
    document.getElementById('stats-export-btn')?.addEventListener('click', () => {
        const a = document.createElement('a');
        a.href = `/api/roll-stats/export?${buildFilterParams()}`;
        a.click();
    });

    // ── Import ────────────────────────────────────────────────
    const importInput = document.createElement('input');
    importInput.type   = 'file';
    importInput.accept = '.csv';
    importInput.style.display = 'none';
    document.body.appendChild(importInput);

    document.getElementById('stats-import-btn')?.addEventListener('click', () => {
        importInput.value = '';
        importInput.click();
    });

    importInput.addEventListener('change', async () => {
        const file = importInput.files[0];
        if (!file) return;
        const text = await file.text();
        const rows = parseCSV(text);
        if (!rows.length) return;
        await fetch('/api/roll-stats/import', {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify({ rows }),
        });
        fetchAndRender();
    });

    function parseCSV(text) {
        const lines = text.trim().split('\n');
        if (lines.length < 2) return [];
        const headers = splitCSVLine(lines[0]);
        return lines.slice(1).map(line => {
            const values = splitCSVLine(line);
            const obj = {};
            headers.forEach((h, i) => { obj[h.trim()] = (values[i] || '').trim(); });
            return obj;
        });
    }

    function splitCSVLine(line) {
        const result = [];
        let current = '', inQuotes = false;
        for (let i = 0; i < line.length; i++) {
            if (line[i] === '"') { inQuotes = !inQuotes; }
            else if (line[i] === ',' && !inQuotes) { result.push(current); current = ''; }
            else { current += line[i]; }
        }
        result.push(current);
        return result;
    }

    // ── Initial load ──────────────────────────────────────────
    fetchAndRender();

    // ── Combat tracker ────────────────────────────────────────
    ctBuildCarousel();
    ctRenderAll();
}

// ══════════════════════════════════════════════════════════════
// CUSTOM MULTI-SELECT
// ══════════════════════════════════════════════════════════════
class MultiSelect {
    constructor(msKey, dropdownId, allLabel, onChange = null) {
        this.trigger  = document.querySelector(`[data-ms="${msKey}"]`);
        this.dropdown = document.getElementById(dropdownId);
        this.allLabel = allLabel;
        this.selected = new Set();
        this.onChange = onChange;
        this._bind();
    }
    _bind() {
        if (!this.trigger || !this.dropdown) return;
        this.trigger.addEventListener('click', e => { e.stopPropagation(); this._toggleOpen(); });
        this.dropdown.querySelectorAll('.stats-ms-option').forEach(opt => {
            opt.addEventListener('click', e => {
                e.stopPropagation();
                const val = opt.dataset.value;
                if (val === 'all') { this.selected.clear(); }
                else { this.selected.has(val) ? this.selected.delete(val) : this.selected.add(val); }
                this._render();
                if (this.onChange) this.onChange(this);
            });
        });
    }
    _toggleOpen() {
        document.querySelectorAll('.stats-ms-dropdown.open').forEach(dd => {
            if (dd !== this.dropdown) {
                dd.classList.remove('open');
                dd.previousElementSibling?.classList.remove('open');
            }
        });
        const open = this.dropdown.classList.toggle('open');
        this.trigger.classList.toggle('open', open);
    }
    close() {
        this.dropdown?.classList.remove('open');
        this.trigger?.classList.remove('open');
    }
    _renderOnly() { this._render(); }
    _render() {
        const isAll  = this.selected.size === 0;
        const allOpt = this.dropdown.querySelector('.all-option');
        if (!allOpt) return;
        allOpt.classList.toggle('partial', !isAll);
        allOpt.querySelector('.stats-ms-check').innerHTML = isAll ? '<i class="fas fa-check"></i>' : '';
        this.dropdown.querySelectorAll('.stats-ms-option:not(.all-option)').forEach(opt => {
            const sel = this.selected.has(opt.dataset.value);
            opt.classList.toggle('selected', sel);
            opt.querySelector('.stats-ms-check').innerHTML = sel ? '<i class="fas fa-check"></i>' : '';
        });
        const textEl = this.trigger.querySelector('.stats-ms-trigger-text');
        if (!textEl) return;
        if (isAll) {
            textEl.textContent = this.allLabel;
            this.trigger.classList.remove('has-value');
        } else if (this.selected.size === 1) {
            const v = [...this.selected][0];
            textEl.textContent = this.dropdown.querySelector(`[data-value="${v}"]`).textContent.trim();
            this.trigger.classList.add('has-value');
        } else {
            textEl.textContent = `${this.selected.size} selected`;
            this.trigger.classList.add('has-value');
        }
    }
}

// ══════════════════════════════════════════════════════════════
// COMBAT TRACKER
// ══════════════════════════════════════════════════════════════
function ctHpColor(hp, maxHp) {
    if (!maxHp || hp === 0) return '#4a4a4a';
    const p = hp / maxHp;
    if (p > 0.75) return '#10b981';
    if (p > 0.50) return '#84cc16';
    if (p > 0.25) return '#f59e0b';
    return '#ef4444';
}

function ctCondBadge(cond) {
    const icon = ctCondIcons[cond] || 'fa-exclamation-circle';
    return `<span class="condition-badge"><i class="fas ${icon}"></i> ${cond}</span>`;
}

function ctBuildCarousel() {
    const track = document.getElementById('cc-track');
    if (!track) return;
    track.innerHTML = '';
    combatants.forEach((c, i) => {
        const el = document.createElement('div');
        el.className = 'cc-item' + (c.hp === 0 ? ' dead' : '');
        el.dataset.index = i;
        el.innerHTML = `
            <div class="cc-avatar" style="background:${c.color}">${c.name[0]}</div>
            <div class="cc-name-text">${c.name}</div>
            <div class="cc-hp-bar"><div class="cc-hp-fill"></div></div>`;
        track.appendChild(el);
    });
}

function ctRenderCarousel() {
    const n = combatants.length;
    document.querySelectorAll('.cc-item').forEach((el, i) => {
        const c   = combatants[i];
        let rel   = ((i - ctTurn) % n + n) % n;
        if (rel > Math.floor(n / 2)) rel -= n;
        const key  = Math.max(-3, Math.min(3, rel)).toString();
        const pos  = ctPos[key];
        const hide = Math.abs(rel) > 3;

        el.setAttribute('data-rel', rel);
        el.style.opacity   = hide ? '0' : String(pos.opacity);
        el.style.zIndex    = hide ? '0' : String(4 - Math.abs(rel));
        el.style.transform = hide
            ? `translateX(calc(-50% + ${rel > 0 ? 400 : -400}px)) translateY(-50%) scale(0.2)`
            : `translateX(calc(-50% + ${pos.x}px)) translateY(calc(-50% + ${pos.y}px)) scale(${pos.scale})`;

        const showHp = ctIsGM || c.hpPublic;
        const hpBar  = el.querySelector('.cc-hp-bar');
        const fill   = el.querySelector('.cc-hp-fill');
        hpBar.style.visibility = showHp ? 'visible' : 'hidden';
        if (showHp) {
            const pct = c.maxHp > 0 ? c.hp / c.maxHp * 100 : 0;
            fill.style.width      = pct + '%';
            fill.style.background = ctHpColor(c.hp, c.maxHp);
        }
    });
}

function ctRenderLeft() {
    const left = document.getElementById('ct-left');
    if (!left) return;
    const c      = combatants[ctTurn];
    const showHp = ctIsGM || c.hpPublic;
    const showAc = ctIsGM || c.acPublic;

    let html = `
        <div class="now-acting-label"><i class="fas fa-play"></i> Now Acting</div>
        <div class="ct-name">${c.name}</div>`;

    if (showHp) {
        const pct = c.maxHp > 0 ? c.hp / c.maxHp * 100 : 0;
        html += `
        <div class="ct-stat-row">
            <span class="ct-stat-label">HP</span>
            <span class="ct-stat-value">${c.hp} / ${c.maxHp}</span>
        </div>
        <div class="ct-hp-bar-wrap">
            <div class="ct-hp-bar-fill" style="width:${pct}%;background:${ctHpColor(c.hp,c.maxHp)}"></div>
        </div>`;
    } else {
        html += `<div class="ct-hidden-field"><i class="fas fa-lock"></i> HP not shown</div>`;
    }

    if (showAc) {
        html += `
        <div class="ct-ac-row">
            <div class="ct-ac-shield">${c.ac}</div>
            <span class="ct-stat-label">Armour Class</span>
        </div>`;
    } else {
        html += `<div class="ct-hidden-field"><i class="fas fa-lock"></i> AC not shown</div>`;
    }

    html += `<div class="ct-conditions">${
        c.conditions.length
            ? c.conditions.map(ctCondBadge).join('')
            : '<span class="no-conditions">No conditions</span>'
    }</div>`;

    left.innerHTML = html;
}

function ctRenderList() {
    const list = document.getElementById('ct-initiative-list');
    if (!list) return;
    list.innerHTML = combatants.map((c, i) => {
        const active = i === ctTurn ? 'ct-active' : '';
        const dead   = c.hp === 0   ? 'ct-dead'   : '';
        const showHp = ctIsGM || c.hpPublic;
        const pct    = c.maxHp > 0  ? c.hp / c.maxHp * 100 : 0;
        const hpEl   = showHp
            ? `<div class="init-hp-mini"><div class="init-hp-mini-fill" style="width:${pct}%;background:${ctHpColor(c.hp,c.maxHp)}"></div></div>`
            : `<span class="init-locked"><i class="fas fa-lock"></i></span>`;
        const dots = c.conditions.map(() => `<span class="init-cond-dot"></span>`).join('');
        return `<div class="init-row ${active} ${dead}">
            <span class="init-score">${c.init}</span>
            <span class="init-mini-avatar" style="background:${c.color}">${c.name[0]}</span>
            <span class="init-name">${c.name}</span>
            ${dots}${hpEl}
        </div>`;
    }).join('');
}

function ctRenderAll() {
    const roundEl = document.getElementById('ct-round');
    if (roundEl) roundEl.textContent = `Round ${ctRound}`;

    const prevArrow = document.getElementById('ct-arrow-prev');
    if (prevArrow) prevArrow.classList.toggle('arrow-hidden', !ctIsGM);

    const endBtn = document.getElementById('ct-end-turn-btn');
    if (endBtn) endBtn.disabled = ctIsGM || !combatants[ctTurn].isPlayer;

    ctRenderCarousel();
    ctRenderLeft();
    ctRenderList();
}

// ══════════════════════════════════════════════════════════════
// BOOT
// ══════════════════════════════════════════════════════════════
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
else init();

})();
