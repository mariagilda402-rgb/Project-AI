import re

with open('mobile/index.html', 'r', encoding='utf-8') as f:
    c = f.read()

loja_ui = '''
            <div style="display: flex; gap: 15px; margin-bottom: 20px;">
                <div class="glass" style="flex: 1; padding: 15px; border-radius: 16px; text-align: center; border: 1px solid var(--accent-purple);">
                    <i class="fa-solid fa-star fa-2x" style="color: var(--accent-pink); margin-bottom: 10px;"></i>
                    <h3 style="margin: 0; font-size: 1.2rem;">500 XP</h3>
                    <p style="margin: 0; font-size: 0.8rem; color: var(--text-secondary);">1h Videogame</p>
                    <button style="margin-top: 10px; background: var(--accent-purple); color: white; border: none; padding: 5px 15px; border-radius: 8px;">Comprar</button>
                </div>
                <div class="glass" style="flex: 1; padding: 15px; border-radius: 16px; text-align: center; border: 1px solid var(--accent-blue);">
                    <i class="fa-solid fa-pizza-slice fa-2x" style="color: var(--accent-blue); margin-bottom: 10px;"></i>
                    <h3 style="margin: 0; font-size: 1.2rem;">1200 XP</h3>
                    <p style="margin: 0; font-size: 0.8rem; color: var(--text-secondary);">Comida Favorita</p>
                    <button style="margin-top: 10px; background: var(--accent-blue); color: white; border: none; padding: 5px 15px; border-radius: 8px;">Comprar</button>
                </div>
            </div>
'''

metas_ui = '''
            <div class="glass" style="padding: 15px; border-radius: 16px; margin-bottom: 15px; border-left: 4px solid var(--accent-green);">
                <h3 style="margin: 0; color: white;">Aprender Inglês (B2)</h3>
                <p style="margin: 5px 0; font-size: 0.9rem; color: var(--text-secondary);">Faltam 3 meses</p>
                <div style="background: rgba(0,0,0,0.5); height: 8px; border-radius: 4px; overflow: hidden;">
                    <div style="background: var(--accent-green); height: 100%; width: 65%;"></div>
                </div>
            </div>
'''

treino_ui = '''
            <div class="glass" style="padding: 15px; border-radius: 16px; text-align: center;">
                <i class="fa-solid fa-person-running fa-3x" style="color: var(--accent-pink); margin-bottom: 15px;"></i>
                <h3 style="color: white; margin: 0;">Treino de Hoje: Pernas</h3>
                <button style="margin-top: 15px; background: linear-gradient(135deg, var(--accent-pink), var(--accent-purple)); color: white; border: none; padding: 10px 20px; border-radius: 12px; font-weight: bold; width: 100%;">INICIAR TREINO</button>
            </div>
'''

iot_ui = '''
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
                <div class="glass" style="padding: 15px; border-radius: 16px; text-align: center; border: 1px solid var(--accent-blue);">
                    <i class="fa-solid fa-lightbulb fa-2x" style="color: var(--accent-blue); margin-bottom: 10px;"></i>
                    <p style="margin: 0; font-weight: bold; color: white;">Luz Quarto</p>
                    <p style="margin: 0; font-size: 0.8rem; color: var(--accent-green);">Ligada</p>
                </div>
                <div class="glass" style="padding: 15px; border-radius: 16px; text-align: center;">
                    <i class="fa-solid fa-fan fa-2x" style="color: var(--text-secondary); margin-bottom: 10px;"></i>
                    <p style="margin: 0; font-weight: bold; color: white;">Ar Condicionado</p>
                    <p style="margin: 0; font-size: 0.8rem; color: var(--text-secondary);">Desligado</p>
                </div>
            </div>
'''

c = re.sub(r'<div class="list-container" id="shop-list">.*?</div>', loja_ui, c, flags=re.DOTALL)
c = re.sub(r'<div class="list-container" id="goals-list">.*?</div>', metas_ui, c, flags=re.DOTALL)
c = re.sub(r'<div class="list-container" id="fitness-list">.*?</div>', treino_ui, c, flags=re.DOTALL)
c = re.sub(r'<div class="list-container" id="iot-list">.*?</div>', iot_ui, c, flags=re.DOTALL)

with open('mobile/index.html', 'w', encoding='utf-8') as f:
    f.write(c)
