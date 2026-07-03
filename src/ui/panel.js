// DASHBOARD VIDA
    async function refreshDashboardVida() {
      try {
        const financeEl = document.getElementById('dashboard-finance-content');
        const habitsEl = document.getElementById('dashboard-habits-content');
        const tasksEl = document.getElementById('dashboard-tasks-content');

        financeEl.innerHTML = "<p>Atualizando...</p>";
        habitsEl.innerHTML = "<p>Atualizando...</p>";
        tasksEl.innerHTML = "<p>Atualizando...</p>";

        // Fetch via pywebview
        const data = await apiCall('nexus_get_dashboard_data');
        if (!data) return;

        financeEl.innerHTML = `<p>Transações hoje: ${data.finance?.today || 0}</p>
                               <p>Total do Mês: R$ ${data.finance?.month_total || '0.00'}</p>`;
        habitsEl.innerHTML = `<p>Hábitos Concluídos: ${data.habits?.completed || 0}/${data.habits?.total || 0}</p>
                              <p>Nível Atual: ${data.user?.level || 1} (${data.user?.xp || 0} XP)</p>`;
        tasksEl.innerHTML = `<p>Eventos hoje: ${data.calendar?.events_today || 0}</p>`;
      } catch (e) {
        console.error("Erro ao carregar Dashboard de Vida", e);
        financeEl.innerHTML = "<p style='color:var(--danger)'>Erro ao carregar dados</p>";
        habitsEl.innerHTML = "<p style='color:var(--danger)'>Erro ao carregar dados</p>";
        tasksEl.innerHTML = "<p style='color:var(--danger)'>Erro ao carregar dados</p>";
      }
    }

    async function loadMorningBriefing() {
      const card = document.getElementById('briefing-card');
      card.style.display = 'block';
      document.getElementById('briefing-summary').textContent = 'Gerando briefing...';
      try {
        const raw = await window.pywebview.api.nexus_command(JSON.stringify({ action: 'morning_briefing' }));
        const d = JSON.parse(raw);
        document.getElementById('briefing-summary').textContent = d.summary || '';

        const tasks = d.tasks_pending || [];
        document.getElementById('briefing-tasks').innerHTML = tasks.length
          ? tasks.slice(0,4).map(t => `<div style="margin-bottom:4px;">• ${t.title}</div>`).join('')
          : '<span style="color:var(--success)">✅ Nenhuma tarefa pendente</span>';

        const events = d.events_today || [];
        document.getElementById('briefing-events').innerHTML = events.length
          ? events.map(e => `<div style="margin-bottom:4px;">🗓 ${e.time ? e.time.substring(0,5) + ' — ' : ''}${e.title}</div>`).join('')
          : '<span style="color:var(--text-dim)">Sem eventos hoje</span>';

        const fin = d.finance_month || {};
        const balColor = (fin.balance || 0) >= 0 ? 'var(--success)' : 'var(--danger)';
        document.getElementById('briefing-finance').innerHTML =
          `<div>Receitas: <strong style="color:var(--success)">R$ ${(fin.income||0).toFixed(2)}</strong></div>
           <div>Despesas: <strong style="color:var(--danger)">R$ ${(fin.expense||0).toFixed(2)}</strong></div>
           <div>Balanço: <strong style="color:${balColor}">R$ ${(fin.balance||0).toFixed(2)}</strong></div>`;

        const habits = d.habits_active || [];
        document.getElementById('briefing-habits').innerHTML = habits.length
          ? habits.slice(0,4).map(h => `<div style="margin-bottom:4px;">🔥 ${h.name} (${h.streak} dias)</div>`).join('')
          : '<span style="color:var(--text-dim)">Nenhum hábito ativo</span>';
      } catch (e) {
        document.getElementById('briefing-summary').textContent = 'Erro ao gerar briefing: ' + e.message;
        console.error(e);
      }
    }

    async function loadProactiveSuggestions() {
      const card = document.getElementById('proactive-card');
      const list = document.getElementById('proactive-list');
      card.style.display = 'block';
      list.innerHTML = '<p style="color:var(--text-dim); font-size:13px;">Analisando padrões...</p>';
      try {
        const raw = await window.pywebview.api.nexus_command(JSON.stringify({ action: 'proactive_suggestions' }));
        const d = JSON.parse(raw);
        const suggestions = d.suggestions || [];
        if (!suggestions.length) {
          list.innerHTML = '<p style="color:var(--success); font-size:13px;">✅ Nenhum alerta proativo no momento. Está tudo em dia!</p>';
          return;
        }
        const priorityColor = { high: 'var(--danger)', medium: 'var(--warning)', low: 'var(--text-dim)' };
        list.innerHTML = suggestions.map(s => `
          <div style="background:var(--surface); border-radius:8px; padding:12px 14px; border-left:3px solid ${priorityColor[s.priority] || 'var(--border)'}; display:flex; flex-direction:column; gap:4px;">
            <div style="font-size:13px; color:var(--text);">${s.message}</div>
            <div style="font-size:11px; color:var(--text-dim);">&#128204; ${s.action}</div>
          </div>`).join('');
      } catch (e) {
        list.innerHTML = '<p style="color:var(--danger); font-size:13px;">Erro ao carregar sugestões.</p>';
        console.error(e);
      }
    }

    async function loadRoutines() {
      const container = document.getElementById('routines-list');
      container.innerHTML = '<p class="subtitle">Carregando...</p>';
      try {
        const raw = await window.pywebview.api.nexus_command(JSON.stringify({ action: 'get_routines' }));
        const routines = JSON.parse(raw);
        if (!routines || routines.length === 0) {
          container.innerHTML = '<p class="subtitle">Nenhuma rotina criada ainda. Crie uma nova!</p>';
          return;
        }
        container.innerHTML = routines.map(r => `
          <div class="glass-panel" style="padding: 16px; position: relative;">
            <button onclick="deleteRoutine(${r.id})" style="position:absolute; top:16px; right:16px; background:none; border:none; color:var(--danger); cursor:pointer;"><i class="fa-solid fa-trash"></i></button>
            <h3 style="margin: 0 0 4px; color: var(--accent);">${r.name} <span style="font-size:12px; color:var(--text-dim); font-weight:normal;">(${r.time})</span></h3>
            ${r.desc ? `<p style="margin:0 0 12px; font-size:13px; color:var(--text-dim);">${r.desc}</p>` : ''}
            <div style="display:flex; flex-direction:column; gap:8px; margin-top:12px;">
              ${r.steps.map((s, i) => `
                <div style="background:var(--surface); padding:8px 12px; border-radius:6px; font-size:13px; display:flex; justify-content:space-between;">
                  <span><strong style="color:var(--text-dim); margin-right:8px;">${i+1}.</strong> ${s.title}</span>
                  <span style="color:var(--accent);">${s.duration} min</span>
                </div>
              `).join('')}
            </div>
            <div style="margin-top:16px;">
              <button class="btn btn-secondary" onclick="startRoutine(${r.id})">▶ Iniciar Rotina</button>
            </div>
          </div>
        `).join('');
      } catch (e) {
        container.innerHTML = '<p class="subtitle" style="color:var(--danger);">Erro ao carregar rotinas.</p>';
        console.error(e);
      }
    }

    async function promptCreateRoutine() {
      const name = prompt("Nome da Rotina (ex: Rotina Matinal):");
      if (!name) return;
      const stepsRaw = prompt("Insira as tarefas separadas por vírgula (ex: Arrumar cama, 10min Leitura, Meditação):");
      if (!stepsRaw) return;

      const steps = stepsRaw.split(',').map(s => {
        const str = s.trim();
        return { title: str, duration: 5 }; // default 5 min
      });

      try {
        const raw = await window.pywebview.api.nexus_command(JSON.stringify({
          action: 'create_routine', name, time_of_day: 'Any', steps
        }));
        const res = JSON.parse(raw);
        if (res.ok) {
          showToast('Rotina criada!');
          loadRoutines();
        } else {
          showToast('Erro ao criar: ' + res.error, 'error');
        }
      } catch (e) {
        console.error(e);
      }
    }

    async function deleteRoutine(id) {
      if (!confirm("Excluir esta rotina?")) return;
      try {
        await window.pywebview.api.nexus_command(JSON.stringify({ action: 'delete_routine', id }));
        showToast('Rotina excluída.');
        loadRoutines();
      } catch (e) {
        console.error(e);
      }
    }

    function startRoutine(id) {
      showToast('Rotina iniciada! (Lógica de timer no próximo update)', 'info');
    }

    // TOAST NOTIFICATIONS
    function showToast(msg, type = 'info') {
      const c = document.getElementById('toastContainer');
      const t = document.createElement('div');
      t.className = 'toast ' + type;
      t.textContent = msg;
      c.appendChild(t);
      setTimeout(() => { if (t.parentNode) t.remove(); }, 3100);
    }

    // THEME LOGIC
    const savedTheme = localStorage.getItem('panelTheme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    const themeSelect = document.getElementById('themeSelect');
    if (themeSelect) themeSelect.value = savedTheme;

    if (themeSelect) {
      themeSelect.addEventListener('change', (e) => {
        document.documentElement.setAttribute('data-theme', e.target.value);
        localStorage.setItem('panelTheme', e.target.value);
      });
    }

    const neonToggle = document.getElementById('neonBorderToggle');
    const appWrapper = document.getElementById('app-wrapper');
    const savedNeon = localStorage.getItem('panelNeonBorder') === 'true';
    if (neonToggle && appWrapper) {
      neonToggle.checked = savedNeon;
      if (savedNeon) appWrapper.classList.add('neon-enabled');
      else appWrapper.classList.remove('neon-enabled');

      neonToggle.addEventListener('change', (e) => {
        const isEnabled = e.target.checked;
        localStorage.setItem('panelNeonBorder', isEnabled);
        if (isEnabled) appWrapper.classList.add('neon-enabled');
        else appWrapper.classList.remove('neon-enabled');
      });
    }

    const neonColorPicker = document.getElementById('neonColorPicker');
    const savedNeonColor = localStorage.getItem('panelNeonColor') || '#8b5cf6';
    if (neonColorPicker) {
      neonColorPicker.value = savedNeonColor;
      // Define a cor salva na raiz
      document.documentElement.style.setProperty('--accent', savedNeonColor);

      // Converte Hex para RGBA para o Glow
      function hexToRgba(hex, alpha) {
        let r = parseInt(hex.slice(1, 3), 16),
            g = parseInt(hex.slice(3, 5), 16),
            b = parseInt(hex.slice(5, 7), 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
      }
      document.documentElement.style.setProperty('--accent-glow', hexToRgba(savedNeonColor, 0.3));

      neonColorPicker.addEventListener('input', (e) => {
        const val = e.target.value;
        localStorage.setItem('panelNeonColor', val);
        document.documentElement.style.setProperty('--accent', val);
        document.documentElement.style.setProperty('--accent-glow', hexToRgba(val, 0.3));
      });
    }

    function applyUiPreferences(motion, density) {
      const safeMotion = ['reduced', 'balanced', 'expressive'].includes(motion) ? motion : 'balanced';
      const safeDensity = ['comfortable', 'compact'].includes(density) ? density : 'comfortable';
      document.body.dataset.motion = safeMotion;
      document.body.dataset.density = safeDensity;
      if (appWrapper) {
        appWrapper.dataset.motion = safeMotion;
        appWrapper.dataset.density = safeDensity;
      }
      const motionSelect = document.getElementById('cfgMotionLevel');
      const densitySelect = document.getElementById('cfgUiDensity');
      if (motionSelect) motionSelect.value = safeMotion;
      if (densitySelect) densitySelect.value = safeDensity;
      try {
        localStorage.setItem('panelMotionLevel', safeMotion);
        localStorage.setItem('panelUiDensity', safeDensity);
      } catch (_) {}
    }
    applyUiPreferences(
      localStorage.getItem('panelMotionLevel') || 'balanced',
      localStorage.getItem('panelUiDensity') || 'comfortable'
    );

    // SIDEBAR NAV
    document.querySelectorAll('.nav-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('page-' + btn.dataset.tab).classList.add('active');

        if (btn.dataset.tab === 'agents') loadAgentsGrid();
        if (btn.dataset.tab === 'dashboard') refreshDashboardVida();
        if (btn.dataset.tab === 'routines') loadRoutines();
        if (btn.dataset.tab === 'modes') loadModesTab();
        if (btn.dataset.tab === 'trash') { loadTrashAgents(); loadTrashMemories(); }
        if (btn.dataset.tab === 'memory') initMemoryPage();
        if (btn.dataset.tab === 'reference') loadReferenceTab();
        if (btn.dataset.tab === 'diagnostics') { loadStructMemView(); refreshTelemetry(); }
      });
    });

    // SIMULATED DASHBOARD STATS
    setInterval(() => {
      if (!document.getElementById('page-home').classList.contains('active')) return;
      const cpu = Math.floor(Math.random() * 20) + 5;
      document.getElementById('statCpuText').textContent = cpu + '%';
      document.getElementById('statCpuBar').style.width = cpu + '%';

      const ram = (Math.random() * 2 + 4).toFixed(1);
      document.getElementById('statRamText').textContent = ram + ' GB';
      document.getElementById('statRamBar').style.width = (ram / 16 * 100) + '%';

      const tk = Math.floor(Math.random() * 50) + 120;
      document.getElementById('statTokens').textContent = tk + ' t/m';
    }, 2000);

    // API WRAPPER
    async function apiCall(method, ...args) {
      if (!window.pywebview || !window.pywebview.api) return null;
      try { return await window.pywebview.api[method](...args); }
      catch (e) { console.error('API error:', method, e); return null; }
    }

    let nexusThemeState = { modules: [], presets: [], assignments: {} };

    function renderNexusThemeSwatches(preset) {
      const target = document.getElementById('nexusThemeSwatches');
      if (!target) return;
      const tokens = (preset && preset.tokens) || {};
      const colors = ['--accent', '--bg', '--bg-panel', '--surface', '--border-accent']
        .map(k => tokens[k])
        .filter(Boolean);
      target.innerHTML = colors.map(c => '<span class="nexus-theme-swatch" style="background:' + c + '"></span>').join('');
    }

    function syncNexusThemeStatus() {
      const modSelect = document.getElementById('nexusThemeModule');
      const presetSelect = document.getElementById('nexusThemePreset');
      const status = document.getElementById('nexusThemeStatus');
      if (!modSelect || !presetSelect || !status) return;
      const mod = nexusThemeState.modules.find(m => m.id === modSelect.value);
      const preset = nexusThemeState.presets.find(p => p.id === presetSelect.value);
      renderNexusThemeSwatches(preset);
      if (!mod || !preset) {
        status.textContent = 'Selecione uma janela e um preset para personalizar.';
        return;
      }
      status.textContent = mod.label + ' usa ' + preset.name + ' · ' + (preset.description || 'preset local');
    }

    async function loadNexusThemes() {
      const data = await apiCall('nexus_theme_list');
      const modSelect = document.getElementById('nexusThemeModule');
      const presetSelect = document.getElementById('nexusThemePreset');
      if (!data || !modSelect || !presetSelect) return;
      nexusThemeState = data;
      modSelect.innerHTML = (data.modules || []).map(m => '<option value="' + m.id + '">' + m.label + '</option>').join('');
      presetSelect.innerHTML = (data.presets || []).map(p => '<option value="' + p.id + '">' + p.name + (p.custom ? ' · custom' : '') + '</option>').join('');
      const activeModule = data.modules && data.modules[0];
      if (activeModule) {
        modSelect.value = activeModule.id;
        presetSelect.value = activeModule.preset_id;
      }
      syncNexusThemeStatus();
    }

    async function applyNexusWindowTheme() {
      const mod = document.getElementById('nexusThemeModule')?.value || 'overview';
      const preset = document.getElementById('nexusThemePreset')?.value || 'dark-neon';
      const result = await apiCall('nexus_theme_apply', mod, preset);
      if (result && result.ok) {
        showToast(result.message || 'Tema aplicado.', 'success');
        await loadNexusThemes();
      } else {
        showToast((result && result.error) || 'Nao foi possivel aplicar o tema.', 'error');
      }
    }

    async function generateNexusThemePreset() {
      const mod = document.getElementById('nexusThemeModule')?.value || 'overview';
      const prompt = (document.getElementById('nexusThemePrompt')?.value || '').trim();
      if (!prompt) return showToast('Descreva o estilo do preset.', 'error');
      const result = await apiCall('nexus_theme_generate', mod, prompt, '');
      if (result && result.ok) {
        showToast(result.message || 'Tema gerado.', 'success');
        await loadNexusThemes();
        const presetSelect = document.getElementById('nexusThemePreset');
        if (presetSelect && result.preset) presetSelect.value = result.preset.id;
        syncNexusThemeStatus();
      } else {
        showToast((result && result.error) || 'Nao foi possivel gerar o tema.', 'error');
      }
    }

    async function pollRuntimeStatus() {
      if (!window.pywebview || !window.pywebview.api) return;
      const st = await apiCall('get_status');
      if (!st) return;
      const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
      set('rtMic', st.mic_listening ? 'ligado' : 'desligado');
      set('rtProc', st.is_processing ? 'sim' : 'não');
      set('rtQueue', String(st.queue_approx));
      const llm = (st.llm_last_provider || '') + (st.llm_last_model ? ' / ' + st.llm_last_model : '');
      set('rtLlm', llm || '—');
      const err = (st.llm_last_error_time ? '[' + st.llm_last_error_time + '] ' : '') + (st.llm_last_error || '');
      set('rtErr', err);
      const status = document.getElementById('statusLabel');
      if (status) {
        status.classList.remove('is-idle', 'is-listening', 'is-processing');
        if (st.is_processing) {
          status.textContent = 'PROCESSANDO';
          status.classList.add('is-processing');
        } else if (st.mic_listening) {
          status.textContent = 'OUVINDO';
          status.classList.add('is-listening');
        } else {
          status.textContent = 'EM ESPERA';
          status.classList.add('is-idle');
        }
      }
      const startupEl = document.getElementById('startupPhases');
      if (startupEl && Array.isArray(st.startup_phases)) {
        const phases = st.startup_phases.slice(-6).reverse();
        startupEl.innerHTML = phases.length ? phases.map(p => '<div class="startup-phase"><strong>' + p.name + (p.detail ? ' - ' + p.detail : '') + '</strong><span>' + p.elapsed_ms + 'ms</span></div>').join('') : '<div class="startup-phase"><strong>Sem fases registradas</strong><span>0ms</span></div>';
      }
      const toolsEl = document.getElementById('rtTools');
      if (toolsEl && Array.isArray(st.recent_tools)) {
        toolsEl.textContent = st.recent_tools.length ? st.recent_tools.map(t => (t.tool + ' ' + (t.ok ? 'OK' : 'FALHOU') + ' ' + t.ms + 'ms')).join('\n') : '—';
      }
    }
    async function loadReferenceTab() {
      const sec = await apiCall('get_critical_actions_reference');
      const ref = await apiCall('get_tools_reference');
      const rs = document.getElementById('refSecurity');
      const rm = document.getElementById('refMarkers');
      const rf = document.getElementById('refFc');
      if (rs) rs.textContent = JSON.stringify(sec, null, 2);
      if (rm) rm.textContent = (ref && ref.markers_block) ? ref.markers_block : '—';
      if (rf) rf.textContent = (ref && ref.function_calling_intro) ? ref.function_calling_intro : '—';
    }

    async function refreshTelemetry() {
      const tail = await apiCall('get_telemetry_tail', 40);
      const el = document.getElementById('telemetryTail');
      if (el) el.textContent = tail ? JSON.stringify(tail, null, 2) : '—';
    }

    async function loadStructMemView() {
      const m = await apiCall('get_structured_memory');
      const el = document.getElementById('structMemView');
      if (el) el.textContent = m ? JSON.stringify(m, null, 2) : '—';
    }

    // CHAT
    const chatInput = document.getElementById('chatInput');
    function sendChat() {
      const text = chatInput.value.trim();
      if (!text) return;
      chatInput.value = '';
      if (window.pywebview && window.pywebview.api) {
        window.pywebview.api.send_chat_message(text).then(() => {
          showToast('Comando enviado!', 'success');
        });
      }
    }
    // CHAT - Os ouvintes estão no final do arquivo

    // UPLOAD DE ARQUIVO
    document.getElementById('btnUploadFile').addEventListener('click', async () => {
      const filePath = await apiCall('select_file');
      if (filePath) {
        await apiCall('process_file', filePath, "");
        showToast('Arquivo enviado para processamento!', 'success');
      }
    });

    // WS STATUS
    function connectWS() {
      try {
        const ws = new WebSocket('ws://127.0.0.1:5123/ws');
        ws.onmessage = (e) => {
          try {
            const d = JSON.parse(e.data);
            if (d.type === 'state' && d.status) {
              const lbl = document.getElementById('statusLabel');
              const statusMap = { idle: 'INATIVO', thinking: 'PENSANDO', speaking: 'FALANDO', listening: 'ESCUTANDO' };
              lbl.textContent = statusMap[d.status] || d.status.toUpperCase();
            }
          } catch (ex) { }
        };
        ws.onclose = () => setTimeout(connectWS, 3000);
        ws.onerror = () => { };
      } catch (e) { setTimeout(connectWS, 3000); }
    }
    connectWS();

    // AGENTS GRID
    async function loadAgentsGrid() {
      document.getElementById('agents-list-view').style.display = 'block';
      document.getElementById('agent-detail-view').style.display = 'none';

      const agents = await apiCall('list_agents');
      const activeId = await apiCall('get_active_agent_id');
      const grid = document.getElementById('agentGrid');

      if (!agents) { grid.innerHTML = '<p>Carregando...</p>'; return; }
      grid.innerHTML = '';
      document.getElementById('statAgents').textContent = agents.length;

      agents.forEach(a => {
        const isActive = a.id === activeId;
        const card = document.createElement('div');
        card.className = 'agent-card-grid' + (isActive ? ' active-agent' : '');
        card.onclick = () => openAgentDetail(a.id);

        card.innerHTML = `
          ${isActive ? '<div class="ac-badge" title="Agente Ativo"></div>' : ''}
          <div class="ac-header">
            <div class="ac-avatar">${a.name.charAt(0).toUpperCase()}</div>
            <div class="ac-name">${a.name}</div>
          </div>
          <div class="ac-body">${a.persona.length > 80 ? a.persona.substring(0, 80) + '...' : a.persona}</div>
          <div class="ac-footer">
            <span>${a.tts_provider.toUpperCase()}</span>
            <span>Velocidade: ${a.tts_speed}x</span>
          </div>
        `;
        grid.appendChild(card);
      });
    }

    // AGENT DETAIL & MEMORY
    const fSpeed = document.getElementById('fSpeed');
    const fSpeedVal = document.getElementById('fSpeedVal');
    fSpeed.addEventListener('input', () => fSpeedVal.textContent = parseFloat(fSpeed.value).toFixed(1) + 'x');

    let currentAgentCollection = '';

    async function openAgentDetail(id) {
      document.getElementById('agents-list-view').style.display = 'none';
      document.getElementById('agent-detail-view').style.display = 'block';

      if (!id) {
        document.getElementById('detailTitle').textContent = 'Novo Agente';
        document.getElementById('fId').value = '';
        document.getElementById('fName').value = '';
        document.getElementById('fPersona').value = '';
        document.getElementById('fTtsProvider').value = (document.getElementById('cfgTts') && document.getElementById('cfgTts').value) || 'edge';
        document.getElementById('fTtsVoice').value = 'pt-BR-FranciscaNeural';
        document.getElementById('fKokoroVoice').value = 'pf_dora';
        fSpeed.value = 1.0; fSpeedVal.textContent = '1.0x';
        document.getElementById('agentMemList').innerHTML = '<p style="color:var(--text-dim);font-size:13px">Salve o agente para gerenciar memórias.</p>';
        document.getElementById('btnDeleteAgent').style.display = 'none';
      } else {
        const agents = await apiCall('list_agents');
        const a = agents.find(x => x.id === id);
        if (!a) return;

        document.getElementById('detailTitle').textContent = 'Editar Agente: ' + a.name;
        document.getElementById('fId').value = a.id;
        document.getElementById('fName').value = a.name;
        document.getElementById('fPersona').value = a.persona;
        document.getElementById('fTtsProvider').value = a.tts_provider || 'xtts';
        document.getElementById('fTtsVoice').value = a.tts_voice || 'pt-BR-FranciscaNeural';
        document.getElementById('fKokoroVoice').value = a.kokoro_voice || 'pf_dora';
        fSpeed.value = a.tts_speed || 1.0;
        fSpeedVal.textContent = parseFloat(fSpeed.value).toFixed(1) + 'x';
        document.getElementById('btnDeleteAgent').style.display = 'block';

        currentAgentCollection = a.memory_collection;
        loadMemories();
      }
    }

    document.getElementById('btnCreateAgent').addEventListener('click', () => openAgentDetail(null));
    document.getElementById('btnBackAgents').addEventListener('click', () => loadAgentsGrid());

    document.getElementById('btnSaveAgent').addEventListener('click', async () => {
      const id = document.getElementById('fId').value;
      const data = {
        name: document.getElementById('fName').value.trim(),
        persona: document.getElementById('fPersona').value.trim(),
        tts_provider: document.getElementById('fTtsProvider').value,
        tts_voice: document.getElementById('fTtsVoice').value,
        tts_speed: parseFloat(document.getElementById('fSpeed').value) || 1.0,
        kokoro_voice: document.getElementById('fKokoroVoice').value.trim()
      };
      if (!data.name) return showToast('Nome é obrigatório', 'error');

      if (id) await apiCall('update_agent', id, data);
      else await apiCall('create_agent', data);

      showToast('Agente salvo com sucesso!', 'success');
      loadAgentsGrid();
    });

    document.getElementById('btnDeleteAgent').addEventListener('click', async () => {
      const id = document.getElementById('fId').value;
      if (!id || !confirm('Mover para lixeira?')) return;
      await apiCall('delete_agent', id);
      showToast('Agente movido para lixeira', 'warning');
      loadAgentsGrid();
    });

    // MEMORY
    async function loadMemories() {
      if (!currentAgentCollection) return;
      const query = document.getElementById('memSearch').value.trim();
      const result = await apiCall('list_memories', currentAgentCollection, query);
      const list = document.getElementById('agentMemList');

      if (!result || !result.memories || result.memories.length === 0) {
        list.innerHTML = '<p style="color:var(--text-dim);font-size:13px">Nenhuma memória encontrada.</p>';
        return;
      }

      list.innerHTML = '';
      result.memories.forEach(m => {
        const d = document.createElement('div');
        d.className = 'mem-item';
        d.innerHTML = `
          <div style="font-size:13px; line-height:1.4; flex:1;">${m.text}</div>
          <button class="btn-danger" style="padding:6px 12px;" onclick="deleteMem('${m.id}')">Excluir</button>
        `;
        list.appendChild(d);
      });
    }

    document.getElementById('btnMemSearch').addEventListener('click', loadMemories);

    async function deleteMem(id) {
      if (!confirm('Mover memória para lixeira?')) return;
      await apiCall('delete_memory', currentAgentCollection, id);
      loadMemories();
    }

    document.getElementById('btnMemExport').addEventListener('click', async () => {
      if (!currentAgentCollection) return;
      await apiCall('export_memories', currentAgentCollection);
    });
    document.getElementById('btnMemImport').addEventListener('click', async () => {
      if (!currentAgentCollection) return;
      await apiCall('trigger_import_memories', currentAgentCollection);
    });

    // MODES
    async function loadModesTab() {
      const agents = await apiCall('list_agents');
      const list = document.getElementById('modeAgentsList');
      list.innerHTML = '';
      if (agents) {
        agents.forEach(a => {
          const l = document.createElement('label');
          l.innerHTML = `<input type="checkbox" class="mode-agent-cb" value="${a.id}" checked> ${a.name}`;
          list.appendChild(l);
        });
      }
    }

    document.getElementById('modeSelect').addEventListener('change', e => {
      const isDebate = e.target.value === 'debate';
      document.getElementById('roundRobinOpts').style.display = isDebate ? 'none' : 'block';
      document.getElementById('debateOpts').style.display = isDebate ? 'block' : 'none';
      document.getElementById('modeInputLabel').textContent = isDebate ? 'Tema do Debate' : 'Pergunta';
    });

    document.getElementById('modePresetSelect').addEventListener('change', e => {
      const v = e.target.value;
      const m = document.getElementById('modeSelect');
      const i = document.getElementById('modeInput');
      const r = document.getElementById('modeRounds');
      if (v === 'interview') { m.value = 'roundrobin'; i.value = 'Aja como candidato em uma entrevista. Fale suas qualidades.'; }
      else if (v === 'debate') { m.value = 'debate'; r.value = 4; i.value = 'Discutam o impacto da IA no trabalho.'; }
      else if (v === 'brainstorm') { m.value = 'roundrobin'; i.value = 'Deem ideias para um app de produtividade.'; }
      m.dispatchEvent(new Event('change'));
    });

    document.getElementById('btnModesStart').addEventListener('click', async () => {
      const mode = document.getElementById('modeSelect').value;
      const text = document.getElementById('modeInput').value.trim();
      if (!text) return showToast('Digite o tema!', 'error');

      const cbs = document.querySelectorAll('.mode-agent-cb:checked');
      const ids = Array.from(cbs).map(c => c.value);
      if (ids.length < 2) return showToast('Selecione pelo menos 2 agentes.', 'error');

      if (mode === 'roundrobin') {
        const chained = document.getElementById('modeChained').checked;
        await apiCall('start_round_robin', text, ids, chained);
      } else {
        const r = parseInt(document.getElementById('modeRounds').value) || 3;
        await apiCall('start_debate', text, ids, r);
      }
      showToast('Sessão iniciada! Acompanhe no terminal.', 'success');
    });

    // TRASH
    async function loadTrashAgents() {
      const trash = await apiCall('list_trash');
      document.getElementById('trashAgentCount').textContent = trash ? trash.length : 0;
      const list = document.getElementById('trashAgentList');
      list.innerHTML = '';
      if (trash) {
        trash.forEach(a => {
          const d = document.createElement('div');
          d.className = 'trash-item';
          d.innerHTML = `
            <div class="trash-item-text"><strong>${a.name}</strong><br>Na Lixeira</div>
            <div style="display:flex; gap:8px;">
              <button class="btn-secondary" onclick="restoreAg('${a.id}')">Restaurar</button>
              <button class="btn-danger" onclick="permDelAg('${a.id}')">Apagar</button>
            </div>
          `;
          list.appendChild(d);
        });
      }
    }
    async function restoreAg(id) { await apiCall('restore_agent', id); loadTrashAgents(); }
    async function permDelAg(id) { if (confirm('Apagar permanentemente?')) { await apiCall('permanent_delete_agent', id); loadTrashAgents(); } }

    async function loadTrashMemories() {
      const trash = await apiCall('list_trash_memories');
      document.getElementById('trashMemCount').textContent = trash ? trash.length : 0;
      const list = document.getElementById('trashMemList');
      list.innerHTML = '';
      if (trash) {
        trash.forEach(m => {
          const d = document.createElement('div');
          d.className = 'trash-item';
          d.innerHTML = `
            <div class="trash-item-text">${m.text}<br><span style="color:var(--text-dim);font-size:11px">De: ${m.original_collection}</span></div>
            <div style="display:flex; gap:8px;">
              <button class="btn-secondary" onclick="restoreMe('${m.id}')">Restaurar</button>
              <button class="btn-danger" onclick="permDelMe('${m.id}')">Apagar</button>
            </div>
          `;
          list.appendChild(d);
        });
      }
    }
    async function restoreMe(id) { await apiCall('restore_memory', id); loadTrashMemories(); }
    async function permDelMe(id) { if (confirm('Apagar permanentemente?')) { await apiCall('permanent_delete_memory', id); loadTrashMemories(); } }

    // AGENT SELECTOR (HOME)
    async function loadAgentSelector() {
      const agents = await apiCall('list_agents');
      const activeId = await apiCall('get_active_agent_id');
      const sel = document.getElementById('agentSelect');
      if (!agents || !sel) return;
      sel.innerHTML = '';
      agents.forEach(a => {
        const opt = document.createElement('option');
        opt.value = a.id;
        opt.textContent = a.name;
        if (a.id === activeId) opt.selected = true;
        sel.appendChild(opt);
      });
    }
    document.getElementById('agentSelect').addEventListener('change', async (e) => {
      await apiCall('set_active_agent', e.target.value);
    });

    // ACTIVATE AGENT FROM DETAIL
    document.getElementById('btnActivateAgent').addEventListener('click', async () => {
      const id = document.getElementById('fId').value;
      if (!id) return showToast('Salve o agente antes de ativar.', 'error');
      await apiCall('set_active_agent', id);
      showToast('Agente ativado!', 'success');
      loadAgentSelector();
    });

    // PERSONA GENERATOR
    document.getElementById('btnGenPersona').addEventListener('click', async () => {
      const nameField = document.getElementById('fName');
      const name = nameField.value.trim();
      if (!name) return showToast('Digite o nome do personagem primeiro!', 'error');

      const btn = document.getElementById('btnGenPersona');
      btn.disabled = true;
      btn.textContent = '⏳ Gerando...';
      showToast('Gerando personalidade para "' + name + '"...', 'info');

      const result = await apiCall('generate_persona', name);

      btn.disabled = false;
      btn.textContent = '✨ Gerar Persona';

      if (result) {
        document.getElementById('fPersona').value = result;
        showToast('Persona gerada com sucesso!', 'success');
      } else {
        showToast('Falha ao gerar persona. Verifique a LLM.', 'error');
      }
    });

    // CHAT INPUT
    async function sendChat() {
      const input = document.getElementById('chatInput');
      const text = input.value.trim();
      if (!text) return;

      const success = await apiCall('send_chat_message', text);
      if (success) {
        input.value = '';
        const fb = document.getElementById('chatFeedback');
        fb.style.opacity = 1;
        setTimeout(() => fb.style.opacity = 0, 2000);
      } else {
        showToast('Erro ao enviar mensagem', 'error');
      }
    }

    async function sendQuickCommand(text) {
      if (!text) return;
      const success = await apiCall('send_chat_message', text);
      if (success) {
        showToast('Comando enviado!', 'success');
      } else {
        showToast('Erro ao enviar comando', 'error');
      }
    }

    document.getElementById('sendBtn').addEventListener('click', sendChat);
    const nexusBtn = document.getElementById('btnOpenNexus');
    if (nexusBtn) {
      nexusBtn.addEventListener('click', async () => {
        const ok = await apiCall('open_nexus_hud');
        if (ok) showToast('Abrindo Nexus (janelas desktop)…', 'success');
        else showToast('Não foi possível abrir o Nexus', 'error');
      });
    }
    document.querySelectorAll('[data-nexus-mod]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const mod = btn.getAttribute('data-nexus-mod');
        const ok = await apiCall('open_nexus_module', mod, '{}');
        if (ok) showToast('Abrindo ' + mod + '…', 'success');
        else showToast('Não foi possível abrir o módulo Nexus', 'error');
      });
    });
	    const nexusThemeModule = document.getElementById('nexusThemeModule');
	    const nexusThemePreset = document.getElementById('nexusThemePreset');
	    const btnApplyNexusTheme = document.getElementById('btnApplyNexusTheme');
	    const btnGenerateNexusTheme = document.getElementById('btnGenerateNexusTheme');
	    if (nexusThemeModule) {
	      nexusThemeModule.addEventListener('change', () => {
	        const mod = nexusThemeState.modules.find(m => m.id === nexusThemeModule.value);
	        if (mod && nexusThemePreset) nexusThemePreset.value = mod.preset_id;
	        syncNexusThemeStatus();
	      });
	    }
	    if (nexusThemePreset) nexusThemePreset.addEventListener('change', syncNexusThemeStatus);
	    if (btnApplyNexusTheme) btnApplyNexusTheme.addEventListener('click', applyNexusWindowTheme);
	    if (btnGenerateNexusTheme) btnGenerateNexusTheme.addEventListener('click', generateNexusThemePreset);
	    document.getElementById('chatInput').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') sendChat();
    });

	    window.addEventListener('pywebviewready', async () => {
	      loadAgentsGrid();
	      loadAgentSelector();
	      loadNexusThemes();

	      let ccShownId = null;
      const ccModal = document.getElementById('criticalConfirmModal');
      const ccDetail = document.getElementById('ccDetail');
      const ccTool = document.getElementById('ccTool');

      async function pollCriticalConfirm() {
        if (!window.pywebview || !window.pywebview.api || !ccModal) return;
        if (ccModal.style.display === 'flex' && ccShownId) return;
        const p = await apiCall('get_critical_confirm_pending');
        if (!(p && p.id)) {
          if (ccModal.style.display === 'flex') {
            ccModal.style.display = 'none';
            ccShownId = null;
          }
          return;
        }
        if (ccShownId === p.id) return;
        ccShownId = p.id;
        ccDetail.textContent = p.detail || 'Confirme esta ação na interface.';
        ccTool.textContent = 'Ferramenta: ' + (p.tool_name || '—');
        ccModal.style.display = 'flex';
      }

      function resolveCriticalConfirm(approved) {
        if (!ccShownId) return;
        const id = ccShownId;
        apiCall('resolve_critical_confirm', id, approved).then(() => {
          if (ccModal) ccModal.style.display = 'none';
          ccShownId = null;
        });
      }

      const ccBtnYes = document.getElementById('ccBtnYes');
      const ccBtnNo = document.getElementById('ccBtnNo');
      if (ccBtnYes) ccBtnYes.addEventListener('click', () => resolveCriticalConfirm(true));
      if (ccBtnNo) ccBtnNo.addEventListener('click', () => resolveCriticalConfirm(false));

      const criticalToggle = document.getElementById('criticalConfirmToggle');
      if (criticalToggle) {
        criticalToggle.addEventListener('change', async (e) => {
          const ok = await apiCall('set_critical_confirm_enabled', e.target.checked);
          if (ok) {
            showToast(e.target.checked ? 'Confirmação crítica ativada.' : 'Confirmação crítica desativada.', 'success');
          } else {
            showToast('Não foi possível salvar.', 'error');
            e.target.checked = !e.target.checked;
          }
        });
      }

      // Carregar configs reais
      try {
        const cfg = await apiCall('get_config');
        if (cfg) {
          document.getElementById('cfgProvider').value = (cfg.llm_provider || '').toUpperCase();
          document.getElementById('cfgGemini').value = cfg.gemini_model || '';
          document.getElementById('cfgGroq').value = cfg.groq_model || '';
          document.getElementById('cfgTts').value = cfg.tts_provider || '';
          const fo = document.getElementById('cfgTtsFallbackOrder');
          if (fo) fo.value = cfg.tts_provider_order || '';
          const installBtn = document.getElementById('btnInstallEdgeTts');
          if (installBtn) {
            const edgeAvailable = cfg.edge_tts_available === true;
            installBtn.disabled = edgeAvailable;
            installBtn.textContent = edgeAvailable ? 'Edge TTS instalado' : 'Instalar Edge TTS';
          }
          const tcp = document.getElementById('cfgTtsPrefetchChunks');
          if (tcp) tcp.checked = cfg.tts_prefetch_chunks !== false;
          const cct = document.getElementById('criticalConfirmToggle');
          if (cct && typeof cfg.critical_confirm_enabled === 'boolean') {
            cct.checked = cfg.critical_confirm_enabled;
          }
          const hk = document.getElementById('cfgHotkey');
          if (hk) hk.value = cfg.panel_hotkey || 'win+shift+a';
          const setChecked = (id, val) => { const el = document.getElementById(id); if (el) el.checked = !!val; };
          const setValue = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
          setChecked('cfgUseMic', cfg.use_mic !== false);
          setValue('cfgSttLanguage', cfg.stt_language || 'pt-BR');
          setValue('cfgSttEnergyThreshold', cfg.stt_energy_threshold || 1100);
          setValue('cfgSttPauseThreshold', cfg.stt_pause_threshold || 0.8);
          setValue('cfgSttNonSpeakingDuration', cfg.stt_non_speaking_duration || 0.35);
          setValue('cfgSttMinAudioSeconds', cfg.stt_min_audio_seconds || 0.35);
          setValue('cfgSttCalibrationSeconds', cfg.stt_calibration_seconds || 0.8);
          setChecked('cfgSttDynamicEnergy', cfg.stt_dynamic_energy !== false);
          setChecked('cfgStartVisionTracker', cfg.start_vision_tracker === true);
          setChecked('cfgStartHeartbeat', cfg.start_heartbeat !== false);
          setChecked('cfgStartProactiveAgent', cfg.start_proactive_agent === true);
          setChecked('cfgEnableClapTrigger', cfg.enable_clap_trigger !== false);
          setValue('cfgClapThreshold', cfg.clap_threshold || 0.15);
          setValue('cfgClapMaxGap', cfg.clap_max_gap || 1.2);
          applyUiPreferences(cfg.ui_motion_level || 'balanced', cfg.ui_density || 'comfortable');
          setChecked('cfgStudyProfessorMode', cfg.study_professor_mode === true);
        }
      } catch (e) {
        console.error("Erro ao carregar config:", e);
      }

      setInterval(pollRuntimeStatus, 1000);
      pollRuntimeStatus();

      const bda = document.getElementById('btnDiagAudio');
      if (bda) bda.addEventListener('click', async () => {
        const r = await apiCall('diagnostics_audio');
        const el = document.getElementById('diagResult');
        if (el) el.textContent = JSON.stringify(r, null, 2);
      });
      const bdt = document.getElementById('btnDiagTts');
      if (bdt) bdt.addEventListener('click', async () => {
        await apiCall('diagnostics_tts');
        setTimeout(async () => {
          const s = await apiCall('get_status');
          const el = document.getElementById('diagResult');
          if (el) el.textContent = JSON.stringify((s && s.diagnostics) ? s.diagnostics : {}, null, 2);
        }, 3500);
      });
      const bdl = document.getElementById('btnDiagLlm');
      if (bdl) bdl.addEventListener('click', async () => {
        await apiCall('diagnostics_llm');
        setTimeout(async () => {
          const s = await apiCall('get_status');
          const el = document.getElementById('diagResult');
          if (el) el.textContent = JSON.stringify((s && s.diagnostics) ? s.diagnostics : {}, null, 2);
        }, 8000);
      });
      const btr = document.getElementById('btnTelemetryRefresh');
      if (btr) btr.addEventListener('click', refreshTelemetry);
      const bsm = document.getElementById('btnStructMemRefresh');
      if (bsm) bsm.addEventListener('click', loadStructMemView);
      const bsd = document.getElementById('btnStructDel');
      if (bsd) bsd.addEventListener('click', async () => {
        const cat = (document.getElementById('structCat') || {}).value || 'notes';
        const key = (document.getElementById('structKey') || {}).value || '';
        if (!key) { showToast('Informe a chave', 'error'); return; }
        const r = await apiCall('delete_structured_memory_entry', cat, key);
        showToast(String(r), 'info');
        loadStructMemView();
      });
      const bpe = document.getElementById('btnPrefExport');
      if (bpe) bpe.addEventListener('click', async () => {
        const ok = await apiCall('export_preferences_bundle');
        showToast(ok ? 'Exportado.' : 'Cancelado ou falhou.', ok ? 'success' : 'error');
      });
      const bpi = document.getElementById('btnPrefImport');
      if (bpi) bpi.addEventListener('click', async () => {
        const ok = await apiCall('import_preferences_bundle');
        showToast(ok ? 'Importado. Reinicie se necessário.' : 'Cancelado ou falhou.', ok ? 'success' : 'error');
      });

      const bst = document.getElementById('btnSaveTtsConfig');
      if (bst) bst.addEventListener('click', async () => {
        const payload = {
          tts_provider: document.getElementById('cfgTts').value,
          tts_provider_order: document.getElementById('cfgTtsFallbackOrder').value.trim(),
          tts_prefetch_chunks: document.getElementById('cfgTtsPrefetchChunks').checked
        };
        const result = await apiCall('update_tts_config', payload);
        if (result && result.ok) showToast('TTS aplicado em tempo real.', 'success');
        else showToast((result && result.error) ? result.error : 'Falha ao aplicar TTS.', 'error');
      });

      const bit = document.getElementById('btnInstallEdgeTts');
      if (bit) bit.addEventListener('click', async () => {
        bit.disabled = true;
        const originalText = bit.textContent;
        bit.textContent = 'Instalando...';
        const result = await apiCall('install_edge_tts');
        if (result && result.ok) {
          showToast('Edge TTS instalado. Reinicie o app para usar.', 'success');
          bit.textContent = 'Edge TTS instalado';
        } else {
          showToast((result && result.error) ? result.error : 'Falha ao instalar Edge TTS.', 'error');
          bit.textContent = originalText || 'Instalar Edge TTS';
        }
        bit.disabled = false;
      });

      const bindRangeLabel = (inputId, labelId, format) => {
        const input = document.getElementById(inputId);
        const label = document.getElementById(labelId);
        if (!input || !label) return;
        const sync = () => { label.textContent = format ? format(input.value) : String(input.value); };
        input.addEventListener('input', sync);
        sync();
      };
      bindRangeLabel('cfgSttEnergyThreshold', 'cfgSttEnergyVal');
      bindRangeLabel('cfgSttPauseThreshold', 'cfgSttPauseVal', v => `${parseFloat(v).toFixed(2)}s`);
      bindRangeLabel('cfgSttNonSpeakingDuration', 'cfgSttNonSpeakingVal', v => `${parseFloat(v).toFixed(2)}s`);
      bindRangeLabel('cfgSttMinAudioSeconds', 'cfgSttMinAudioVal', v => `${parseFloat(v).toFixed(2)}s`);
      bindRangeLabel('cfgSttCalibrationSeconds', 'cfgSttCalibrationVal', v => `${parseFloat(v).toFixed(1)}s`);
      bindRangeLabel('cfgClapThreshold', 'cfgClapThresholdVal', v => parseFloat(v).toFixed(2));
      bindRangeLabel('cfgClapMaxGap', 'cfgClapMaxGapVal', v => `${parseFloat(v).toFixed(1)}s`);

      const bss = document.getElementById('btnSaveSttConfig');
      if (bss) bss.addEventListener('click', async () => {
        const payload = {
          use_mic: !!(document.getElementById('cfgUseMic') || {}).checked,
          stt_language: ((document.getElementById('cfgSttLanguage') || {}).value || 'pt-BR').trim(),
          stt_energy_threshold: parseInt((document.getElementById('cfgSttEnergyThreshold') || {}).value || '1100', 10),
          stt_dynamic_energy: !!(document.getElementById('cfgSttDynamicEnergy') || {}).checked,
          stt_pause_threshold: parseFloat((document.getElementById('cfgSttPauseThreshold') || {}).value || '0.8'),
          stt_non_speaking_duration: parseFloat((document.getElementById('cfgSttNonSpeakingDuration') || {}).value || '0.35'),
          stt_min_audio_seconds: parseFloat((document.getElementById('cfgSttMinAudioSeconds') || {}).value || '0.35'),
          stt_calibration_seconds: parseFloat((document.getElementById('cfgSttCalibrationSeconds') || {}).value || '0.8'),
          recalibrate: true
        };
        const result = await apiCall('update_stt_config', payload);
        if (result && result.ok) showToast('STT aplicado em tempo real.', 'success');
        else showToast((result && result.error) ? result.error : 'Falha ao aplicar STT.', 'error');
      });

      const bstartup = document.getElementById('btnSaveStartupConfig');
      if (bstartup) bstartup.addEventListener('click', async () => {
        const optionalChecked = (id, fallback) => {
          const el = document.getElementById(id);
          return el ? !!el.checked : fallback;
        };
        const optionalValue = (id, fallback) => {
          const el = document.getElementById(id);
          return el ? el.value : fallback;
        };
        const payload = {
          start_vision_tracker: optionalChecked('cfgStartVisionTracker', false),
          start_heartbeat: optionalChecked('cfgStartHeartbeat', true),
          start_proactive_agent: optionalChecked('cfgStartProactiveAgent', false),
          enable_clap_trigger: optionalChecked('cfgEnableClapTrigger', true),
          clap_threshold: parseFloat(optionalValue('cfgClapThreshold', '0.15')),
          clap_max_gap: parseFloat(optionalValue('cfgClapMaxGap', '1.2')),
        };
        const result = await apiCall('update_startup_config', payload);
        if (result && result.ok) showToast('Inicializacao salva. Reinicie para aplicar servicos de fundo.', 'success');
        else showToast((result && result.error) ? result.error : 'Falha ao salvar inicializacao.', 'error');
      });

      const bui = document.getElementById('btnSaveUiConfig');
      if (bui) bui.addEventListener('click', async () => {
        const motion = (document.getElementById('cfgMotionLevel') || {}).value || 'balanced';
        const density = (document.getElementById('cfgUiDensity') || {}).value || 'comfortable';
        const professor = !!((document.getElementById('cfgStudyProfessorMode') || {}).checked);
        applyUiPreferences(motion, density);
        const result = await apiCall('update_ui_config', {
          ui_motion_level: motion,
          ui_density: density,
          study_professor_mode: professor
        });
        if (result && result.ok) showToast('Aparencia aplicada.', 'success');
        else showToast((result && result.error) ? result.error : 'Falha ao salvar aparencia.', 'error');
      });

      // Setup polling para Chat e Logs
      setInterval(pollChatAndLogs, 1000);
      setInterval(pollCriticalConfirm, 400);
    });

    // Polling System
    let lastChatCount = 0;
    let lastLogCount = 0;
    let autoScrollChat = true;
    let autoScrollLogs = true;

    document.getElementById('chatContainer').addEventListener('scroll', (e) => {
      const c = e.target;
      autoScrollChat = (c.scrollHeight - c.scrollTop - c.clientHeight) < 10;
    });
    document.getElementById('logsContainer').addEventListener('scroll', (e) => {
      const c = e.target;
      autoScrollLogs = (c.scrollHeight - c.scrollTop - c.clientHeight) < 10;
    });

    async function pollChatAndLogs() {
      if (!window.pywebview || !window.pywebview.api) return;

      // Só faz polling se as abas estiverem abertas, pra economizar CPU do painel
      const isChatOpen = document.getElementById('page-chat').classList.contains('active');
      const isLogsOpen = document.getElementById('page-logs').classList.contains('active');

      if (isChatOpen) {
        try {
          const res = await apiCall('get_chat_history', lastChatCount);
          if (res && res.messages && res.messages.length > 0) {
            lastChatCount = res.total;
            const container = document.getElementById('chatContainer');

            res.messages.forEach(msg => {
              const div = document.createElement('div');
              div.className = 'chat-msg ' + (msg.role || 'system');

              let header = '';
              if (msg.role !== 'system') {
                header = `<div class="chat-header">${msg.name} • ${msg.time}</div>`;
              }

              div.innerHTML = `
                ${header}
                <div class="chat-bubble">${msg.text.replace(/\\n/g, '<br>')}</div>
              `;
              container.appendChild(div);
            });

            if (autoScrollChat) {
              container.scrollTop = container.scrollHeight;
            }
          }
        } catch (e) { }
      }

      if (isLogsOpen) {
        try {
          const res = await apiCall('get_system_logs', lastLogCount);
          if (res && res.logs && res.logs.length > 0) {
            lastLogCount = res.total;
            const container = document.getElementById('logsContainer');

            res.logs.forEach(log => {
              const div = document.createElement('div');
              let typeClass = '';
              const textLower = log.text.toLowerCase();
              if (textLower.includes('erro') || textLower.includes('falha') || textLower.includes('exception')) typeClass = 'error';
              else if (textLower.includes('warn') || textLower.includes('aviso')) typeClass = 'warn';

              div.className = 'log-line ' + typeClass;
              div.innerHTML = `<span class="log-time">[${log.time}]</span><span class="log-text">${log.text}</span>`;
              container.appendChild(div);
            });

            if (autoScrollLogs) {
              container.scrollTop = container.scrollHeight;
            }
          }
        } catch (e) { }
      }
    }

const nxFullscreenObserver = new ResizeObserver(() => {
      const isMaximized = window.innerWidth >= window.screen.availWidth - 10 && window.innerHeight >= window.screen.availHeight - 10;
      if (isMaximized) {
        document.documentElement.style.setProperty('background-color', 'var(--bg)', 'important');
        document.body.style.setProperty('padding', '0', 'important');
        document.body.style.setProperty('margin', '0', 'important');
        const wrapper = document.getElementById("app-wrapper");
        if (wrapper) {
          wrapper.style.setProperty('border-radius', '0', 'important');
          wrapper.style.setProperty('border', 'none', 'important');
          wrapper.style.setProperty('box-shadow', 'none', 'important');
          wrapper.style.setProperty('margin', '0', 'important');
        }
      } else {
        document.documentElement.style.setProperty('background-color', 'transparent', 'important');
        document.body.style.removeProperty('padding');
        document.body.style.removeProperty('margin');
        const wrapper = document.getElementById("app-wrapper");
        if (wrapper) {
          wrapper.style.removeProperty('border-radius');
          wrapper.style.removeProperty('border');
          wrapper.style.removeProperty('box-shadow');
          wrapper.style.removeProperty('margin');
        }
      }
    });
    nxFullscreenObserver.observe(document.body);

// ============================================================
    // MEMORY MANAGER — Senha + CRUD via pywebview API
    // ============================================================
    const MEMORY_PWD_KEY = 'nexus_panel_memory_pwd';

    function initMemoryPage() {
      const saved = localStorage.getItem(MEMORY_PWD_KEY);
      if (!saved) {
        document.getElementById('memory-setup-note').style.display = 'block';
        document.getElementById('memory-pwd-input').placeholder = 'Criar nova senha...';
      }
    }

    function unlockMemory() {
      const input = document.getElementById('memory-pwd-input').value.trim();
      if (!input) { showToast('Digite uma senha.', 'warning'); return; }

      const saved = localStorage.getItem(MEMORY_PWD_KEY);
      if (!saved) {
        // First-time setup
        if (input.length < 4) { showToast('Mínimo 4 caracteres.', 'warning'); return; }
        localStorage.setItem(MEMORY_PWD_KEY, input);
        showToast('Senha criada com sucesso!', 'success');
        showMemoryContent();
      } else if (input === saved) {
        showMemoryContent();
      } else {
        showToast('Senha incorreta!', 'error');
        document.getElementById('memory-pwd-input').value = '';
      }
    }

    async function showMemoryContent() {
      document.getElementById('memory-lock').style.display = 'none';
      document.getElementById('memory-content').style.display = 'block';
      document.getElementById('memory-pwd-input').value = '';
      await refreshMemory();
    }

    function lockMemory() {
      document.getElementById('memory-lock').style.display = 'flex';
      document.getElementById('memory-content').style.display = 'none';
      document.getElementById('memory-categories').innerHTML = '';
    }

    async function refreshMemory() {
      const container = document.getElementById('memory-categories');
      const emptyMsg = document.getElementById('memory-empty');
      container.innerHTML = '<p style="color:var(--text-dim); font-size:13px;">Carregando memórias...</p>';

      let data = {};
      try {
        if (window.pywebview && window.pywebview.api) {
          data = await window.pywebview.api.get_structured_memory();
        } else {
          // Dev fallback
          data = { notes: { exemplo: 'Dado de teste' }, preferencias: { tema: 'dark' } };
        }
      } catch(e) {
        container.innerHTML = '<p style="color:var(--danger);">Erro ao carregar memórias: ' + e + '</p>';
        return;
      }

      const categories = Object.keys(data).filter(k => Object.keys(data[k] || {}).length > 0);
      if (categories.length === 0) {
        container.innerHTML = '';
        emptyMsg.style.display = 'block';
        return;
      }
      emptyMsg.style.display = 'none';

      container.innerHTML = categories.map(cat => {
        const items = data[cat];
        const rows = Object.entries(items).map(([key, value]) => {
          const safeKey = encodeURIComponent(cat + '|' + key);
          const displayVal = typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value);
          return `
            <div class="mem-item" id="memrow-${safeKey}">
              <div style="flex:1; overflow:hidden;">
                <span style="font-size:10px; color:var(--text-dim); font-family:monospace; text-transform:uppercase;">${escapeHtml(key)}</span>
                <div id="memval-${safeKey}" style="font-size:13px; color:var(--text); margin-top:4px; word-break:break-word;">${escapeHtml(displayVal)}</div>
                <textarea id="memedit-${safeKey}" style="display:none; width:100%; margin-top:6px; font-size:12px; border-radius:6px; min-height:60px;" rows="3">${escapeHtml(displayVal)}</textarea>
              </div>
              <div style="display:flex; flex-direction:column; gap:6px; margin-left:10px;">
                <button class="btn-icon" title="Editar" onclick="toggleEditMemory('${safeKey}', '${escapeHtml(cat)}', '${escapeHtml(key)}')" style="font-size:12px;">✏️</button>
                <button class="btn-icon" title="Excluir" onclick="deleteMemoryEntry('${escapeHtml(cat)}', '${escapeHtml(key)}')" style="background:rgba(239,68,68,0.1); color:var(--danger); border-color:rgba(239,68,68,.3); font-size:12px;">🗑</button>
              </div>
            </div>`;
        }).join('');

        return `
          <div class="mode-card" style="padding:16px;">
            <h2 style="color:var(--accent); margin-bottom:14px; font-size:11px; text-transform:uppercase; letter-spacing:.8px;">${escapeHtml(cat)}</h2>
            <div class="mem-list">${rows}</div>
          </div>`;
      }).join('');
    }

    function toggleEditMemory(safeKey, cat, key) {
      const valDiv = document.getElementById('memval-' + safeKey);
      const editArea = document.getElementById('memedit-' + safeKey);
      if (editArea.style.display === 'none') {
        editArea.style.display = 'block';
        valDiv.style.display = 'none';
        editArea.focus();
        // Change button to Save
        const btn = editArea.closest('.mem-item').querySelector('.btn-icon[title="Editar"]');
        btn.textContent = '💾';
        btn.title = 'Salvar';
        btn.onclick = () => saveMemoryEntry(safeKey, cat, key);
      }
    }

    async function saveMemoryEntry(safeKey, cat, key) {
      const editArea = document.getElementById('memedit-' + safeKey);
      const newValue = editArea.value.trim();
      try {
        if (window.pywebview && window.pywebview.api) {
          await window.pywebview.api.update_structured_memory_entry(cat, key, newValue);
        }
        showToast('Memória atualizada!', 'success');
        await refreshMemory();
      } catch(e) {
        showToast('Erro ao salvar: ' + e, 'error');
      }
    }

    async function deleteMemoryEntry(cat, key) {
      if (!confirm(`Excluir "${key}" de "${cat}"?`)) return;
      try {
        if (window.pywebview && window.pywebview.api) {
          await window.pywebview.api.delete_structured_memory_entry(cat, key);
        }
        showToast('Entrada excluída.', 'success');
        await refreshMemory();
      } catch(e) {
        showToast('Erro ao excluir: ' + e, 'error');
      }
    }

    function escapeHtml(str) {
      return String(str)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    // Init memory page when tab is clicked
    document.addEventListener('DOMContentLoaded', () => {
      document.querySelectorAll('.nav-btn[data-tab="memory"]').forEach(btn => {
        btn.addEventListener('click', () => {
          setTimeout(initMemoryPage, 50);
        });
      });
    });