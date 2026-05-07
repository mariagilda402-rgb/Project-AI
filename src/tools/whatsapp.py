import os
import csv
import time
import subprocess
from pathlib import Path
from .base import ToolResult

# Variaveis globais de estado para o Anti-Spam
_last_sent_time = {}
_last_sent_msg = {}

class WhatsAppTool:
    name = "whatsapp"
    description = "Envia mensagens invisiveis via Mudslide e resolve contatos via CSV."
    critical = True  # Pede confirmacao antes de enviar mensagens

    def _resolve_contact(self, name_or_phone: str) -> str:
        """Tenta achar o numero no data/contatos.csv se o target nao for um numero obvio."""
        cleaned = "".join(c for c in name_or_phone if c.isdigit() or c == "+")
        # Se ja parece um numero de telefone valido, retorna ele mesmo
        if len(cleaned) >= 8:
            return cleaned

        csv_path = Path("data/contatos.csv")
        if not csv_path.exists():
            return ""

        query = name_or_phone.strip().lower()
        try:
            with open(csv_path, mode="r", encoding="utf-8", errors="ignore") as f:
                reader = csv.reader(f)
                for row in reader:
                    # Verifica as primeiras 5 colunas para achar nome e telefone
                    row_text = " ".join(row[:5]).lower()
                    if query in row_text:
                        # Extrai algo que pareca um telefone da linha
                        nums = ["".join(c for c in cell if c.isdigit() or c == "+") for cell in row]
                        valid_nums = [n for n in nums if len(n) >= 8]
                        if valid_nums:
                            return valid_nums[0]
        except Exception:
            pass
        return ""

    def run(self, arg: str) -> ToolResult:
        parts = arg.split("|", 1)
        if len(parts) < 2:
            return ToolResult(
                False, "Formato invalido. Use: numero_ou_nome | mensagem"
            )

        target = parts[0].strip()
        msg = parts[1].strip()

        # Tenta resolver o nome para um telefone usando o contatos.csv
        phone = self._resolve_contact(target)
        
        if not phone:
            return ToolResult(
                False, 
                f"Nao consegui descobrir o numero para '{target}'. "
                "Forneca o numero exato ou coloque o arquivo data/contatos.csv com seus contatos."
            )

        # Garante codigo do pais Brasil (+55) se estiver faltando
        if len(phone) >= 10 and not phone.startswith("+"):
            phone = "+55" + phone

        # --- PROTECOES ANTI-SPAM E ANTI-LOOP ---
        now = time.time()
        if phone in _last_sent_time:
            time_diff = now - _last_sent_time[phone]
            # Bloqueio 1: Envio super rapido pro mesmo numero (menos de 10s)
            if time_diff < 10:
                return ToolResult(False, "BLOCKED BY ANTI-SPAM: Aguarde alguns segundos para mandar outra mensagem para este numero.")
            
            # Bloqueio 2: Exatamente a mesma mensagem em menos de 5 minutos
            if _last_sent_msg.get(phone) == msg and time_diff < 300:
                return ToolResult(False, "BLOCKED BY ANTI-LOOP: Voce ja enviou exatamente a mesma mensagem ha menos de 5 minutos.")

        # Executa invisivel via mudslide
        try:
            si = subprocess.STARTUPINFO()
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            # Se for Windows, o comando 'npx' é um arquivo .cmd e exige shell=True 
            # ou ser chamado explicitamente como 'npx.cmd'
            is_win = os.name == 'nt'
            cmd_list = ["npx", "mudslide", "send", phone, msg]
            
            result = subprocess.run(
                cmd_list,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=is_win,  # Fundamental no Windows para achar o npx
                creationflags=0x08000000 if is_win else 0
            )
            
            if result.returncode == 0:
                # Salva no registro de Anti-Spam somente em caso de sucesso
                _last_sent_time[phone] = now
                _last_sent_msg[phone] = msg
                return ToolResult(True, f"Mensagem enviada invisivelmente para {phone}.")
            else:
                if "login" in result.stdout.lower() or "login" in result.stderr.lower():
                    return ToolResult(
                        False, 
                        "WhatsApp desconectado. Por favor, rode 'npx mudslide login' no terminal para parear o QR Code."
                    )
                return ToolResult(False, f"Erro no mudslide: {result.stderr}")
                
        except Exception as e:
            return ToolResult(False, f"Erro ao executar mudslide: {e}")
