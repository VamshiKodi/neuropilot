/* ═══════════════════════════════════════════════════════════════════════════
   NeuroPilot — Jarvis HUD  |  app.js
   All backend API calls unchanged. Only UI elements updated.
   ═══════════════════════════════════════════════════════════════════════════ */

// ── DOM Refs ──────────────────────────────────────────────────────────────
const chatEl = document.getElementById('chat-messages');
const inputEl = document.getElementById('chat-input');
const sendBtn = document.getElementById('send-btn');
const statusEl = document.getElementById('status');
const hudStatusEl = document.getElementById('hud-status');
const sdotEl = document.getElementById('sdot');
const modalEl = document.getElementById('confirm-modal');
const pendingSummaryEl = document.getElementById('pending-summary');
const pendingStepsEl = document.getElementById('pending-steps');
const confirmBtn = document.getElementById('confirm-btn');
const cancelBtn = document.getElementById('cancel-btn');
const voiceBtn = document.getElementById('voice-btn');
const voiceToggleBtn = document.getElementById('voice-toggle');
const toastsEl = document.getElementById('np-toasts');
const thinkingBarEl = document.getElementById('thinking-bar');
const topbarClockEl = document.getElementById('topbar-clock');
// topbar mini metrics
const mmCpuBar = document.getElementById('mm-cpu-bar');
const mmRamBar = document.getElementById('mm-ram-bar');
const hudCpuEl = document.getElementById('hud-cpu');
const hudRamEl = document.getElementById('hud-ram');
// panel metrics
const pCpuBar = document.getElementById('p-cpu-bar');
const pRamBar = document.getElementById('p-ram-bar');
const pDiskBar = document.getElementById('p-disk-bar');
const npPanelCpuEl = document.getElementById('np-panel-cpu');
const npPanelRamEl = document.getElementById('np-panel-ram');
const npPanelDiskEl = document.getElementById('np-panel-disk');
const npPanelProcEl = document.getElementById('np-panel-proc');
const npPanelUptimeEl = document.getElementById('np-panel-uptime');
// AI + memory + agent
const npAiStateEl = document.getElementById('np-ai-state');
const npAiLogEl = document.getElementById('np-ai-log');
const npMemListEl = document.getElementById('np-mem-list');
const npAgentStatusEl = document.getElementById('np-agent-status');
const npAgentGoalEl = document.getElementById('np-agent-goal');
const npAgentTasksEl = document.getElementById('np-agent-tasks');
// boot
const bootOverlayEl = document.getElementById('boot-overlay');
const bootLinesEl = document.getElementById('boot-lines');
const bootBarFillEl = document.getElementById('boot-bar-fill');
const bootArcEl = document.getElementById('boot-arc');
const bootFooterEl = document.getElementById('boot-footer');
// New Agent Progress Panel Refs
const agentProgressPanel = document.getElementById('agent-progress');
const agentGoalText = document.getElementById('agent-goal-text');
const agentStepsContainer = document.getElementById('agent-steps');
const agentStatusText = document.getElementById('agent-status');

let isBusy = false;
let voiceEnabled = true;
let systemMonitorTimer = null;
let notificationsTimer = null;

// ── Live Clock ────────────────────────────────────────────────────────────
function tickClock() {
  if (!topbarClockEl) return;
  const n = new Date();
  topbarClockEl.textContent =
    String(n.getHours()).padStart(2, '0') + ':' +
    String(n.getMinutes()).padStart(2, '0') + ':' +
    String(n.getSeconds()).padStart(2, '0');
}
setInterval(tickClock, 1000);
tickClock();

// ── Robot state passthrough ───────────────────────────────────────────────
function setRobotStateSafe(s) {
  if (typeof window.setRobotState === 'function') window.setRobotState(s);
}

// ── Robot body class ──────────────────────────────────────────────────────
function setRobotReaction(state) {
  const b = document.body;
  const robotEl = document.getElementById('robot-bg');
  b.classList.remove('robot-idle', 'robot-listening', 'robot-thinking', 'robot-executing', 'robot-error');
  if (robotEl) robotEl.classList.remove('robot-thinking', 'robot-speaking', 'robot-error');

  const s = String(state || 'idle').toLowerCase();
  if (s === 'listening') {
    b.classList.add('robot-listening');
  } else if (s === 'thinking' || s === 'analyzing') {
    b.classList.add('robot-thinking');
    if (robotEl) robotEl.classList.add('robot-thinking');
  } else if (s === 'executing') {
    b.classList.add('robot-executing');
  } else if (s === 'speaking') {
    if (robotEl) robotEl.classList.add('robot-speaking');
  } else if (s === 'error') {
    b.classList.add('robot-error');
    if (robotEl) robotEl.classList.add('robot-error');
  } else {
    b.classList.add('robot-idle');
  }
}

// ── HUD status ────────────────────────────────────────────────────────────
const CORE_LABELS = { idle: 'AI CORE ONLINE', listening: 'VOICE INPUT ACTIVE', analyzing: 'ANALYZING...', executing: 'EXECUTING PLAN', error: 'SYSTEM ERROR' };

function setHudStatus(status) {
  if (!hudStatusEl) return;
  const s = String(status || 'idle').toLowerCase();
  const label = s.toUpperCase();
  hudStatusEl.textContent = label;
  hudStatusEl.className = 'stext ' + s;
  if (sdotEl) sdotEl.className = 'sdot ' + s;
  if (npAiStateEl) npAiStateEl.textContent = label;
  const coreEl = document.getElementById('core-status-text');
  if (coreEl) coreEl.textContent = CORE_LABELS[s] || 'STANDBY';
  setRobotReaction(s);
}

// ── Bar helper ────────────────────────────────────────────────────────────
function setBar(el, pct) {
  if (el) el.style.width = Math.min(100, Math.max(0, pct)) + '%';
}

// ── System Monitor ────────────────────────────────────────────────────────
async function refreshSystemMonitor() {
  try {
    const res = await fetch('/api/system_status');
    if (!res.ok) return;
    const data = await res.json();
    if (!data || data.error) return;

    const cpu = data.cpu && typeof data.cpu.percent === 'number' ? data.cpu.percent : null;
    const ram = data.ram && typeof data.ram.percent === 'number' ? data.ram.percent : null;
    const disk = data.disk && typeof data.disk.percent === 'number' ? data.disk.percent : null;
    const proc = data.processes != null ? data.processes : null;
    const boot = data.boot_time != null ? data.boot_time : null;

    if (cpu !== null) {
      const v = Math.round(cpu) + '%';
      if (hudCpuEl) hudCpuEl.textContent = v;
      if (npPanelCpuEl) npPanelCpuEl.textContent = v;
      setBar(mmCpuBar, cpu); setBar(pCpuBar, cpu);
    }
    if (ram !== null) {
      const v = Math.round(ram) + '%';
      if (hudRamEl) hudRamEl.textContent = v;
      if (npPanelRamEl) npPanelRamEl.textContent = v;
      setBar(mmRamBar, ram); setBar(pRamBar, ram);
    }
    if (disk !== null) {
      if (npPanelDiskEl) npPanelDiskEl.textContent = Math.round(disk) + '%';
      setBar(pDiskBar, disk);
    }
    if (proc !== null && npPanelProcEl) npPanelProcEl.textContent = proc;
    if (boot !== null && npPanelUptimeEl) {
      const s = Math.floor(Date.now() / 1000 - boot);
      npPanelUptimeEl.textContent = Math.floor(s / 3600) + 'h ' + Math.floor((s % 3600) / 60) + 'm';
    }
  } catch (e) { }
}

function startSystemMonitor() {
  if (systemMonitorTimer) return;
  refreshSystemMonitor();
  systemMonitorTimer = setInterval(refreshSystemMonitor, 3000);
}

// ── AI Activity log ───────────────────────────────────────────────────────
function addAiLog(text, type = '') {
  if (!npAiLogEl) return;
  const el = document.createElement('div');
  el.className = 'ai-entry' + (type ? ' ' + type : '');
  const icon = type === 'ok' ? '✓' : type === 'bad' ? '✗' : '›';
  el.innerHTML = `<span class="ae-icon">${icon}</span>${escapeHtml(text)}`;
  npAiLogEl.appendChild(el);
  while (npAiLogEl.children.length > 14) npAiLogEl.removeChild(npAiLogEl.firstChild);
  npAiLogEl.scrollTop = npAiLogEl.scrollHeight;
}

// ── Memory panel ──────────────────────────────────────────────────────────
function renderMemory(obj) {
  if (!npMemListEl) return;
  if (!obj || !Object.keys(obj).length) {
    npMemListEl.innerHTML = '<div class="mem-empty">No memory stored</div>';
    return;
  }
  npMemListEl.innerHTML = Object.entries(obj).slice(-7).map(([k, v]) =>
    `<div class="mem-entry"><span class="mem-key">${escapeHtml(k)}</span><span class="mem-val">${escapeHtml(String(v))}</span></div>`
  ).join('');
}

// ── Agent panel (Mission View) ────────────────────────────────────────────
function setAgentPanelVisible(visible) {
  if (!agentProgressPanel) return;
  agentProgressPanel.style.display = visible ? 'flex' : 'none';
}

function updateAgentMission(goal, steps, status = 'Thinking...') {
  setAgentPanelVisible(true);
  if (agentGoalText) agentGoalText.textContent = goal;
  if (agentStatusText) agentStatusText.textContent = status;

  if (agentStepsContainer) {
    agentStepsContainer.innerHTML = (steps || []).map((s, i) => {
      const isOk = s.status === 'success';
      const isErr = s.status === 'error';
      const cls = isOk ? 'agent-step completed' : isErr ? 'agent-step error' : 'agent-step pending';
      return `<div class="${cls}"><span>${escapeHtml(formatIntentLabel(s.intent))}</span></div>`;
    }).join('');
  }
}

// ── Agent panel (Legacy HUD Sidebar) ──────────────────────────────────────
function renderAgentPanel(goal, tasks, currentIdx) {
  if (!npAgentStatusEl || !npAgentGoalEl || !npAgentTasksEl) return;
  if (!goal) {
    npAgentStatusEl.textContent = 'STANDBY';
    npAgentStatusEl.className = 'agent-badge';
    npAgentGoalEl.textContent = '';
    npAgentTasksEl.innerHTML = '';
    return;
  }
  npAgentStatusEl.textContent = 'ACTIVE';
  npAgentStatusEl.className = 'agent-badge active';
  npAgentGoalEl.textContent = goal;
  npAgentTasksEl.innerHTML = (tasks || []).map((t, i) => {
    const isDone = i < currentIdx;
    const isCurrent = i === currentIdx;
    const cls = isDone ? 'agent-task done' : isCurrent ? 'agent-task current' : 'agent-task';
    const icon = isDone ? '✓' : isCurrent ? '▶' : (i + 1);
    return `<div class="${cls}"><span class="agent-task-n">${icon}</span><span>${escapeHtml(String(t))}</span></div>`;
  }).join('');
}

// ── Toasts ────────────────────────────────────────────────────────────────
function showToast(title, message) {
  if (!toastsEl) return;
  const t = document.createElement('div');
  t.className = 'np-toast';
  t.innerHTML = `<div class="np-toast-title">${escapeHtml(title || 'NOTE')}</div><div class="np-toast-msg">${escapeHtml(message || '')}</div>`;
  toastsEl.appendChild(t);
  setTimeout(() => { try { t.remove(); } catch (e) { } }, 9000);
}

// ── Notifications polling ─────────────────────────────────────────────────
async function pollNotifications() {
  try {
    const res = await fetch('/api/notifications?limit=10');
    if (!res.ok) return;
    const data = await res.json().catch(() => ({}));
    const items = Array.isArray(data.notifications) ? data.notifications : [];
    for (const n of items) {
      if (!n) continue;
      if (n.type === 'reminder') {
        showToast('⏰ REMINDER', n.message || '');
        addMessage({ side: 'left', role: 'NEUROPILOT', text: `REMINDER: ${n.message}` });
        speakText(cleanSpeechText(`Reminder: ${n.message}`));
      } else {
        showToast('NOTIFICATION', n.message || '');
      }
    }
  } catch (e) { }
}

function startNotificationsPolling() {
  if (notificationsTimer) return;
  pollNotifications();
  notificationsTimer = setInterval(pollNotifications, 2500);
}

// ── Speech ────────────────────────────────────────────────────────────────
function cleanSpeechText(text) {
  return String(text || '').replace(/\n/g, ' ').replace(/\s+/g, ' ').trim();
}

function speakText(text) {
  return new Promise((resolve) => {
    if (!voiceEnabled || !('speechSynthesis' in window)) {
      resolve();
      return;
    }
    const u = new SpeechSynthesisUtterance(text);
    u.rate = 1; u.pitch = 1; u.volume = 1;
    const voices = speechSynthesis.getVoices();
    const preferred = voices.find(v => v.name.toLowerCase().includes('google') || v.name.toLowerCase().includes('english'));
    if (preferred) u.voice = preferred;

    u.onend = () => resolve();
    u.onerror = () => resolve();

    speechSynthesis.speak(u);
  });
}

// ── Utility ───────────────────────────────────────────────────────────────
function escapeHtml(text) {
  const d = document.createElement('div');
  d.innerText = text;
  return d.innerHTML;
}
function scrollToBottom() { if (chatEl) { chatEl.scrollTop = chatEl.scrollHeight; } }

// ── Messages ──────────────────────────────────────────────────────────────
function addMessage({ side, role, text }) {
  const row = document.createElement('div');
  row.className = `message-row ${side}`;
  const wrap = document.createElement('div');
  wrap.className = 'msg-wrap';
  const roleEl = document.createElement('div');
  roleEl.className = 'msg-role';
  roleEl.textContent = role;
  const msg = document.createElement('div');
  msg.className = 'message';
  msg.innerHTML = escapeHtml(text);
  wrap.appendChild(roleEl);
  wrap.appendChild(msg);
  row.appendChild(wrap);
  chatEl.appendChild(row);
  scrollToBottom();
  return msg;
}

// ── Thinking bar ──────────────────────────────────────────────────────────
function setStatusLoading(on) {
  if (!thinkingBarEl) return;
  thinkingBarEl.classList.toggle('on', on);
  if (on && statusEl) statusEl.innerHTML = '';
}
function setStatusError(msg) {
  if (statusEl) statusEl.innerHTML = `<span class="serr">⚠ ${escapeHtml(msg)}</span>`;
  setStatusLoading(false);
}

// ── Typing caret ──────────────────────────────────────────────────────────
function setTypingCaret(el, on) { el.classList.toggle('np-typing', on); }

async function typeText(el, text, speedMs = 6) {
  el.innerHTML = '';
  for (let i = 0; i < text.length; i++) {
    el.innerHTML += escapeHtml(text[i]);
    scrollToBottom();
    await new Promise(r => setTimeout(r, speedMs));
  }
}

// ── Format helpers ────────────────────────────────────────────────────────
function formatIntentLabel(intent) {
  if (!intent) return 'Unknown';
  return String(intent).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function formatGoalBlockToHtml(goal, planSteps) {
  const safeGoal = escapeHtml(String(goal || '').trim());
  const steps = Array.isArray(planSteps) ? planSteps : [];
  const items = steps.map((s, i) => {
    const intent = s && s.intent ? s.intent : s;
    return `<div class="np-goal-step"><div class="np-goal-step-n">${i + 1}</div><div class="np-goal-step-t">${escapeHtml(formatIntentLabel(intent))}</div></div>`;
  }).join('');
  return `<div class="np-goal"><div class="np-goal-kicker">GOAL ANALYSIS</div><div class="np-goal-line"><span class="np-goal-label">Goal:</span>${safeGoal || '—'}</div><div class="np-goal-kicker">PLAN GENERATED</div><div class="np-goal-steps">${items}</div></div>`;
}

function formatExecutionToHtml(summary, steps) {
  const safeSummary = escapeHtml(summary || 'Execution completed.');
  const items = (Array.isArray(steps) ? steps : []).map((s, i) => {
    const intent = escapeHtml(formatIntentLabel(s && s.intent));
    const isOk = (s && s.status) === 'success';
    const icon = isOk ? '✓' : '✗';
    const err = !isOk && s && s.error ? `<div class="np-step-error">${escapeHtml(String(s.error))}</div>` : '';
    addAiLog(formatIntentLabel(s && s.intent), isOk ? 'ok' : 'bad');
    return `<div class="np-step ${isOk ? 'ok' : 'bad'}" style="animation-delay:${i * 140}ms"><div class="np-step-line"><span class="np-step-icon">[${icon}]</span><span class="np-step-intent">${intent}</span></div>${err}</div>`;
  }).join('');
  return `<div class="np-execution"><div class="np-execution-kicker">EXECUTION LOG</div><div class="np-execution-summary">${safeSummary}</div><div class="np-steps">${items}</div></div>`;
}

function formatMissionTextToHtml(text) {
  const headers = ['MISSION ANALYSIS:', 'OBJECTIVE BREAKDOWN:', 'EXECUTION STRATEGY:', 'RISK ASSESSMENT:', 'FINAL RECOMMENDATION:'];
  const lines = (text || '').replace(/\r\n/g, '\n').split('\n');
  const sections = [];
  let current = null, currentUl = null;
  const ensureSection = t => { current = { title: t, blocks: [] }; sections.push(current); currentUl = null; };
  const pushP = raw => { if (!current) ensureSection('NEUROPILOT'); currentUl = null; current.blocks.push({ type: 'p', text: raw }); };
  const pushLi = raw => { if (!current) ensureSection('NEUROPILOT'); if (!currentUl) { currentUl = { type: 'ul', items: [] }; current.blocks.push(currentUl); } currentUl.items.push(raw); };
  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    if (!line.trim()) { currentUl = null; continue; }
    const hdr = headers.find(h => line.trim().toUpperCase() === h);
    if (hdr) { ensureSection(hdr.slice(0, -1)); continue; }
    const bullet = line.trim().match(/^[-*•]\s+(.*)$/);
    if (bullet && bullet[1]) { pushLi(bullet[1].trim()); continue; }
    pushP(line.trim());
  }
  const html = sections.map(sec => {
    const blocksHtml = sec.blocks.map(b => {
      if (b.type === 'ul') return `<ul class="np-ul">${(b.items || []).map(it => `<li>${escapeHtml(it)}</li>`).join('')}</ul>`;
      const txt = b.text || '';
      if (txt.startsWith('SYSTEM HUD: Weather')) return `<div class="np-hud-weather">${escapeHtml(txt)}</div>`;
      return `<p class="np-p">${escapeHtml(txt)}</p>`;
    }).join('');
    return `<div class="np-section"><div class="np-section-title">${escapeHtml(sec.title)}</div><div class="np-section-body">${blocksHtml}</div></div>`;
  }).join('');
  return `<div class="np-structured">${html}</div>`;
}

function formatPendingSteps(steps) {
  return steps.map((step, i) => {
    const intent = formatIntentLabel(step.intent);
    return `<div class="p-step"><div class="p-step-i">${i + 1}</div><div class="p-step-t">${escapeHtml(intent)}</div></div>`;
  }).join('');
}

// ── Modal ─────────────────────────────────────────────────────────────────
function showModal() { if (modalEl) modalEl.setAttribute('aria-hidden', 'false'); }
function hideModal() { if (modalEl) modalEl.setAttribute('aria-hidden', 'true'); }

async function confirmExecution() {
  hideModal();
  setHudStatus('executing');
  addAiLog('Execution confirmed');
  const placeholder = addMessage({ side: 'left', role: 'NEUROPILOT', text: '' });
  placeholder.innerHTML = '<div class="loading"><span class="dots"><span class="dot"></span><span class="dot"></span><span class="dot"></span></span></div>';
  try {
    const res = await fetch('/api/confirm', { method: 'POST', headers: { 'Content-Type': 'application/json' } });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) { setHudStatus('error'); placeholder.innerHTML = escapeHtml(data.error || `Failed (${res.status})`); setTimeout(() => setHudStatus('idle'), 3000); return; }
    if (data.type === 'pending_execution') {
      setHudStatus('idle');
      pendingSummaryEl.textContent = data.summary || '';
      const goalHtml = data.goal ? formatGoalBlockToHtml(data.goal, data.plan || data.steps) : '';
      pendingStepsEl.innerHTML = goalHtml + formatPendingSteps(data.steps || []);
      showModal(); placeholder.remove(); setRobotStateSafe('idle'); return;
    }
    if (data.type === 'execution') {
      const goalHtml = data.goal ? formatGoalBlockToHtml(data.goal, data.plan || []) : '';
      placeholder.innerHTML = goalHtml + formatExecutionToHtml(data.summary || '', data.steps || []);
      setTimeout(() => setHudStatus('idle'), 2000);
    }
  } catch (e) {
    setHudStatus('error');
    placeholder.innerHTML = escapeHtml('Execution failed. Please try again.');
    setTimeout(() => setHudStatus('idle'), 3000);
  }
}

async function cancelExecution() {
  hideModal();
  try { await fetch('/api/cancel', { method: 'POST', headers: { 'Content-Type': 'application/json' } }); } catch (e) { }
  addMessage({ side: 'left', role: 'NEUROPILOT', text: 'Mission aborted by operator.' });
  addAiLog('Execution cancelled', 'bad');
  setHudStatus('idle');
}

// ── Send message ──────────────────────────────────────────────────────────
async function sendMessage() {
  const raw = inputEl.value;
  const message = raw.trim();
  if (!message || isBusy) return;

  const isAgent = /^agent\s*:\s*/i.test(message) || /^agent\s+mode\s*:\s*/i.test(message);
  const agentGoal = isAgent ? message.replace(/^agent\s*(mode)?\s*:\s*/i, '').trim() : '';

  isBusy = true;
  sendBtn.disabled = true;
  inputEl.disabled = true;

  addMessage({ side: 'right', role: 'YOU', text: message });
  inputEl.value = '';
  inputEl.style.height = '';
  setAgentPanelVisible(false);

  setStatusLoading(true);
  setHudStatus('analyzing');
  setRobotStateSafe('thinking');
  addAiLog('Command: ' + message.slice(0, 45));

  const placeholder = addMessage({ side: 'left', role: 'NEUROPILOT', text: '' });
  placeholder.innerHTML = '<div class="loading"><span class="dots"><span class="dot"></span><span class="dot"></span><span class="dot"></span></span></div>';

  if (isAgent) {
    updateAgentMission(agentGoal, [], 'Analyzing Mission...');
  }

  try {
    const res = await fetch(isAgent ? '/api/agent_goal' : '/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: isAgent ? JSON.stringify({ goal: agentGoal }) : JSON.stringify({ message })
    });
    const data = await res.json().catch(() => ({}));
    setStatusLoading(false);

    if (!res.ok) {
      const msg = data && data.error ? data.error : `Request failed (${res.status})`;
      setStatusError(msg);
      placeholder.innerHTML = escapeHtml(msg);
      addAiLog(msg, 'bad');
      return;
    }

    const type = data.type || 'chat';

    if (type === 'pending_execution') {
      setHudStatus('idle');
      pendingSummaryEl.textContent = data.summary || '';
      const goalHtml = data.goal ? formatGoalBlockToHtml(data.goal, data.plan || data.steps) : '';
      pendingStepsEl.innerHTML = goalHtml + formatPendingSteps(data.steps || []);
      showModal();
      placeholder.remove();
      setRobotStateSafe('idle');
      addAiLog('Awaiting confirmation');

    } else if (type === 'execution') {
      setHudStatus('executing');
      const goalHtml = data.goal ? formatGoalBlockToHtml(data.goal, data.plan || []) : '';
      placeholder.innerHTML = goalHtml + formatExecutionToHtml(data.summary || '', data.steps || []);
      setRobotStateSafe('speaking');
      speakText(cleanSpeechText(data.summary || ''));
      if (data.goal) {
        renderAgentPanel(data.goal, (data.plan || data.steps || []).map(s => formatIntentLabel(s && s.intent ? s.intent : s)), (data.steps || []).length);
        updateAgentMission(data.goal, data.steps || [], 'Mission Completed');
        setTimeout(() => setAgentPanelVisible(false), 5000);
      }
      setTimeout(() => setHudStatus('idle'), 2000);
      setTimeout(() => setRobotStateSafe('idle'), 2200);

    } else {
      const reply = data.reply || '';
      setTypingCaret(placeholder, true);
      await typeText(placeholder, reply, 6);
      setTypingCaret(placeholder, false);
      placeholder.innerHTML = formatMissionTextToHtml(reply);
      setRobotStateSafe('speaking');
      speakText(cleanSpeechText(reply));
      setTimeout(() => setRobotStateSafe('idle'), 2200);
      addAiLog('Response delivered', 'ok');
    }
  } catch (e) {
    setHudStatus('error');
    setStatusError('Network error. Check server and try again.');
    placeholder.innerHTML = escapeHtml('Network error. Check server and try again.');
    addAiLog('Network error', 'bad');
    setTimeout(() => setHudStatus('idle'), 3000);
  } finally {
    isBusy = false;
    sendBtn.disabled = false;
    inputEl.disabled = false;
    inputEl.focus();
    setStatusLoading(false);
    const cur = hudStatusEl ? hudStatusEl.textContent : '';
    if (cur !== 'EXECUTING' && cur !== 'ERROR') setHudStatus('idle');
  }
}

// ── Input auto-grow ───────────────────────────────────────────────────────
function autoGrow() {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 100) + 'px';
}

// ── Event listeners ───────────────────────────────────────────────────────
if (sendBtn) sendBtn.addEventListener('click', sendMessage);
if (inputEl) {
  inputEl.addEventListener('input', autoGrow);
  inputEl.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  });
}
if (confirmBtn) confirmBtn.addEventListener('click', confirmExecution);
if (cancelBtn) cancelBtn.addEventListener('click', cancelExecution);

// ── Wake Word & Voice Interaction ─────────────────────────────────────────
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let wakeRecognition = null;
let commandRecognition = null;
let isWakeActive = false;
let isAssistantBusy = false; // State lock to prevent redundant triggers

function startWakeListener() {
  if (!SpeechRecognition || isWakeActive) return;

  wakeRecognition = new SpeechRecognition();
  wakeRecognition.continuous = true;
  wakeRecognition.interimResults = false;
  wakeRecognition.lang = 'en-US';

  wakeRecognition.onresult = function (event) {
    const transcript = event.results[event.results.length - 1][0].transcript.toLowerCase();
    const wakePhrases = ["hey neuro", "neuro pilot", "wake up neuro", "hi neuro"];

    console.log("Wake heard:", transcript);

    if (wakePhrases.some(phrase => transcript.includes(phrase))) {
      console.log("Wake word detected");
      activateAssistant(true);
    }
  };

  wakeRecognition.onend = () => {
    if (isWakeActive) {
      try { wakeRecognition.start(); } catch (e) { }
    }
  };

  wakeRecognition.onerror = (e) => {
    console.error("Wake listener error:", e);
    if (isWakeActive) {
      try { wakeRecognition.stop(); } catch (e) { }
      setTimeout(startWakeListener, 500);
    }
  };

  isWakeActive = true;
  try {
    wakeRecognition.start();
    console.log("Wake listener activated.");
  } catch (e) {
    console.error("Wake listener failed to start:", e);
    isWakeActive = false;
  }
}

function stopWakeListener() {
  isWakeActive = false;
  if (wakeRecognition) {
    try { wakeRecognition.stop(); } catch (e) { }
  }
}

async function activateAssistant(verbalPrompt = true) {
  if (isBusy || isAssistantBusy || !SpeechRecognition) return;
  isAssistantBusy = true;

  // 1. Pause wake listener so command listener can use the mic
  stopWakeListener();

  if (verbalPrompt) {
    setRobotStateSafe('listening');
    await speakText("Hello. How can I assist you?");
  }

  // 2. Setup Command Recognition
  commandRecognition = new SpeechRecognition();
  commandRecognition.lang = 'en-US';
  commandRecognition.continuous = false;
  commandRecognition.interimResults = false;

  commandRecognition.onstart = () => {
    if (voiceBtn) voiceBtn.classList.add('listening');
    setHudStatus('listening');
    setRobotStateSafe('listening');
  };

  commandRecognition.onresult = e => {
    const transcript = e.results && e.results[0] && e.results[0][0] ? e.results[0][0].transcript : '';
    if (inputEl) {
      inputEl.value = transcript;
      autoGrow();
    }
    setRobotStateSafe('thinking');
    if (transcript.trim()) {
      sendMessage();
    }
  };

  commandRecognition.onerror = (e) => {
    console.error("Command recognition error:", e);
    if (voiceBtn) voiceBtn.classList.remove('listening');
    setHudStatus('idle');
    setRobotStateSafe('idle');
  };

  commandRecognition.onend = () => {
    if (voiceBtn) voiceBtn.classList.remove('listening');
    setRobotStateSafe('idle');
    // Cooldown/Reset
    setTimeout(() => {
      isAssistantBusy = false;
      startWakeListener();
    }, 1000);
  };

  try {
    commandRecognition.start();
  } catch (e) {
    console.error("Command listener failed:", e);
    isAssistantBusy = false;
    startWakeListener();
  }
}

if (voiceBtn) {
  if (!SpeechRecognition) {
    voiceBtn.style.display = 'none';
  } else {
    voiceBtn.addEventListener('click', () => activateAssistant(false));
  }
}

if (voiceToggleBtn) {
  voiceToggleBtn.addEventListener('click', () => {
    voiceEnabled = !voiceEnabled;
    const vi = document.getElementById('vol-icon');
    if (vi) vi.innerHTML = voiceEnabled
      ? '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07"/>'
      : '<polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/><line x1="23" y1="9" x2="17" y2="15"/><line x1="17" y1="9" x2="23" y2="15"/>';
    if (!voiceEnabled && 'speechSynthesis' in window) speechSynthesis.cancel();
    showToast('AUDIO', voiceEnabled ? 'Voice output enabled' : 'Voice output muted');
  });
}

// ── Boot Sequence ─────────────────────────────────────────────────────────
function runBootSequence() {
  if (!bootOverlayEl || !bootLinesEl || !bootBarFillEl || !bootFooterEl) return;
  const CIRCUM = 2 * Math.PI * 70; // boot-arc r=70

  const steps = [
    { text: 'Initializng NeuroPilot AI Core...', ok: false },
    { text: 'Loading Memory System...', ok: true },
    { text: 'Activating Voice Interface...', ok: true },
    { text: 'Starting Automation Engine...', ok: true },
    { text: 'Connecting to Neural Core...', ok: true },
    { text: 'System Online', ok: false },
  ];

  bootLinesEl.innerHTML = '';
  bootBarFillEl.style.width = '0%';
  if (bootArcEl) {
    bootArcEl.style.strokeDasharray = CIRCUM;
    bootArcEl.style.strokeDashoffset = CIRCUM;
  }
  bootFooterEl.textContent = 'LOADING MODULES...';

  let idx = 0;
  function step() {
    if (idx < steps.length) {
      const s = steps[idx];
      const div = document.createElement('div');
      div.className = 'boot-line' + (s.ok ? ' ok' : '');
      div.textContent = s.text;
      bootLinesEl.appendChild(div);
      const progress = (idx + 1) / steps.length;
      bootBarFillEl.style.width = (progress * 100) + '%';
      if (bootArcEl) bootArcEl.style.strokeDashoffset = CIRCUM * (1 - progress);
      idx++;
      setTimeout(step, idx === steps.length ? 1000 : 800);
      return;
    }
    bootFooterEl.textContent = 'SYSTEM READY';
    setTimeout(() => {
      bootOverlayEl.classList.add('boot-gone');
      bootOverlayEl.setAttribute('aria-hidden', 'true');
      setTimeout(() => { try { bootOverlayEl.remove(); } catch (e) { } }, 800);
    }, 750);
  }
  setTimeout(step, 500);
}

// ── Initialize ────────────────────────────────────────────────────────────
try { runBootSequence(); } catch (e) { console.error('Boot error:', e); }
try { startWakeListener(); } catch (e) { console.error('Wake engine error:', e); }
try { startSystemMonitor(); } catch (e) { console.error('Monitor error:', e); }
try { startNotificationsPolling(); } catch (e) { console.error('Poll error:', e); }

// Initial welcome message (shown after boot)
try {
  addMessage({
    side: 'left',
    role: 'NEUROPILOT',
    text: 'MISSION ANALYSIS:\nState your mission objective to initialize the console.\n\nTip: Prefix "agent:" to activate autonomous goal planning mode.'
  });
  scrollToBottom();
  if (inputEl) inputEl.focus();
} catch (e) { console.error('Init message error:', e); }
