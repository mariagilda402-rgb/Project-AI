/** Nexus Mobile — nexus-fitness.js */
// ================================================================
// FITNESS MODULE — Enhanced
// ================================================================

window.switchFitnessTab = function(tab, btn) {
    ['treinos','dieta','medidas'].forEach(t => {
        const el = document.getElementById('fitness-tab-' + t);
        if (el) el.style.display = t === tab ? 'block' : 'none';
    });
    document.querySelectorAll('.fitness-tab').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    if (tab === 'dieta') loadDietToday();
    if (tab === 'medidas') loadMeasures();
    if (tab === 'treinos') loadFitness();
};

window.openWorkoutBuilder = function() {
    const name = prompt('Nome do treino (ex: Peito, Costas, Pernas):');
    if (!name || !name.trim()) return;
    const muscleGroup = prompt('Grupo muscular (ex: Peito e Ombro):') || '';
    
    const workout = {
        id: Date.now(),
        name: name.trim(),
        type: name.trim(),
        muscle_group: muscleGroup,
        exercises: [],
        date: new Date().toISOString().split('T')[0],
        created_at: new Date().toISOString()
    };
    LocalDB.upsert('fitness_workouts', workout);
    awardXP(25, 'Treino registrado: ' + name);
    loadFitness();
    showInAppNotification('Treino registrado! +25 XP', 'success');
    console.info('[Fitness] Workout added: ' + name);
};

window.openMealLogger = function() {
    const mealName = prompt('Nome da refeicao (ex: Alm0co, Proteina):');
    if (!mealName) return;
    const cal = parseInt(prompt('Calorias (kcal):') || '0');
    const protein = parseInt(prompt('Proteina (g):') || '0');
    const carb = parseInt(prompt('Carboidratos (g):') || '0');
    const fat = parseInt(prompt('Gorduras (g):') || '0');
    
    const meals = LocalDB.get('diet_meals') || [];
    meals.push({ id: Date.now().toString(), name: mealName, cal, protein, carb, fat, date: new Date().toISOString() });
    LocalDB.set('diet_meals', meals);
    loadDietToday();
    showInAppNotification('Refeicao registrada!', 'success');
};

function loadDietToday() {
    const todayStr = new Date().toISOString().split('T')[0];
    const meals = (LocalDB.get('diet_meals') || []).filter(m => m.date.startsWith(todayStr));
    
    const totalCal = meals.reduce((s, m) => s + (m.cal||0), 0);
    const totalProtein = meals.reduce((s, m) => s + (m.protein||0), 0);
    const totalCarb = meals.reduce((s, m) => s + (m.carb||0), 0);
    const totalFat = meals.reduce((s, m) => s + (m.fat||0), 0);
    const goal = 2000;
    
    const pct = Math.min(100, Math.round(totalCal / goal * 100));
    document.getElementById('diet-cal-text') && (document.getElementById('diet-cal-text').textContent = totalCal + ' / ' + goal + ' kcal');
    document.getElementById('diet-cal-bar') && (document.getElementById('diet-cal-bar').style.width = pct + '%');
    document.getElementById('diet-protein') && (document.getElementById('diet-protein').textContent = totalProtein + 'g');
    document.getElementById('diet-carb') && (document.getElementById('diet-carb').textContent = totalCarb + 'g');
    document.getElementById('diet-fat') && (document.getElementById('diet-fat').textContent = totalFat + 'g');
    
    const mealList = document.getElementById('diet-meals-list');
    if (mealList) {
        mealList.innerHTML = meals.length ? meals.map(m => `
            <div class="meal-card glass">
                <div class="meal-info">
                    <div class="meal-name">${escapeHtml(m.name)}</div>
                    <div class="meal-time">${new Date(m.date).toLocaleTimeString('pt-BR',{hour:'2-digit',minute:'2-digit'})}</div>
                </div>
                <div class="meal-cal">${m.cal} kcal</div>
            </div>`).join('') : '<div style="text-align:center;color:var(--text-secondary);padding:20px">Nenhuma refeicao registrada hoje.</div>';
    }
}

window.openBodyMeasurement = function() {
    const weight = prompt('Peso atual (kg):');
    if (!weight) return;
    const fatPct = prompt('% de gordura (opcional):') || '';
    
    const measures = LocalDB.get('body_measures') || [];
    measures.push({ id: Date.now().toString(), weight: parseFloat(weight)||0, fat_pct: parseFloat(fatPct)||0, date: new Date().toISOString() });
    LocalDB.set('body_measures', measures);
    loadMeasures();
    showInAppNotification('Medidas salvas!', 'success');
};

function loadMeasures() {
    const measures = (LocalDB.get('body_measures') || []).sort((a,b) => b.date.localeCompare(a.date));
    const latest = measures[0];
    
    if (latest) {
        document.getElementById('measure-weight-val') && (document.getElementById('measure-weight-val').textContent = latest.weight + ' kg');
        if (latest.fat_pct) document.getElementById('measure-fat-pct') && (document.getElementById('measure-fat-pct').textContent = latest.fat_pct + '%');
    }
    
    const list = document.getElementById('measures-list');
    if (list) {
        list.innerHTML = measures.slice(0,10).map(m => `
            <div class="list-item glass" style="gap:12px">
                <div class="item-main">
                    <div class="item-title">${m.weight} kg</div>
                    <div class="item-subtitle">${new Date(m.date).toLocaleDateString('pt-BR')}</div>
                </div>
                ${m.fat_pct ? '<div style="color:var(--accent-blue);font-weight:700">' + m.fat_pct + '% gord.</div>' : ''}
            </div>`).join('') || '<div style="text-align:center;color:var(--text-secondary);padding:20px">Sem medidas registradas.</div>';
    }
}
