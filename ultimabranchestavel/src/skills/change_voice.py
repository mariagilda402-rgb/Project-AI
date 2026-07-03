import logging
from src.tools.base import BaseTool

class ChangeVoiceSkill(BaseTool):
    """
    Habilidade para trocar a voz da assistente (Edge TTS) em tempo real.
    """
    
    name = "change_voice"
    description = "Troca a voz da assistente para outro personagem. Útil quando o usuário pede para mudar a voz para homem, mulher, Jarvis, Sexta-Feira, Antonio, Thalita, Julio, etc."
    parameters = {
        "type": "object",
        "properties": {
            "nome_personagem": {
                "type": "string",
                "description": "O nome do personagem ou tipo de voz solicitada (ex: 'antonio', 'mulher', 'homem', 'jarvis', 'thalita')."
            }
        },
        "required": ["nome_personagem"]
    }

    # Mapeamento de personagens para as vozes oficiais do Edge TTS (Português - Brasil)
    VOICE_MAP = {
        "antonio": "pt-BR-AntonioNeural",
        "jarvis": "pt-BR-AntonioNeural",
        "julio": "pt-BR-JulioNeural",
        "donato": "pt-BR-DonatoNeural",
        "fabio": "pt-BR-FabioNeural",
        "thalita": "pt-BR-ThalitaNeural",
        "sexta-feira": "pt-BR-ThalitaNeural",
        "brenda": "pt-BR-BrendaNeural",
        "yara": "pt-BR-YaraNeural",
        "giovanna": "pt-BR-GiovannaNeural",
        "leila": "pt-BR-LeilaNeural",
        "leticia": "pt-BR-LeticiaNeural",
        "manuela": "pt-BR-ManuelaNeural",
        "nicolau": "pt-BR-NicolauNeural",
        "valerio": "pt-BR-ValerioNeural"
    }

    def __init__(self, tts_instance=None):
        self.tts = tts_instance
        self.logger = logging.getLogger(self.__class__.__name__)


    def execute(self, **kwargs) -> str:
        nome_personagem = kwargs.get("nome_personagem", "").lower()
        
        # Mapeamento dinâmico para pedidos genéricos
        if "mulher" in nome_personagem or "feminina" in nome_personagem:
            nova_voz = "pt-BR-ThalitaNeural"
            personagem = "Thalita"
        elif "homem" in nome_personagem or "masculino" in nome_personagem or "macho" in nome_personagem:
            nova_voz = "pt-BR-AntonioNeural"
            personagem = "Antonio (Masculino PT-BR)"
        else:
            # Tenta achar a voz no mapa
            nova_voz = None
            personagem = "Padrão"
            for chave, voz_edge in self.VOICE_MAP.items():
                if chave in nome_personagem:
                    nova_voz = voz_edge
                    personagem = chave.capitalize()
                    break
            
            if not nova_voz:
                return f"Desculpe, não encontrei a voz '{nome_personagem}'. As vozes masculinas PT-BR disponíveis são: Donato, Antonio, Fabio, Julio, Nicolau."

        # Troca a voz na instância TTS
        try:
            self.tts.voice = nova_voz
            self.tts.provider = "edge" # Garante que volte pro Edge
            self.logger.info(f"Voz alterada para: {nova_voz}")
            
            # Aqui no futuro você pode salvar no arquivo settings.json para persistir
            
            return f"Sucesso! A voz foi alterada para {personagem}. Pode me responder usando essa nova voz agora para o usuário perceber a diferença!"
        except Exception as e:
            self.logger.error(f"Erro ao trocar voz: {e}")
            return f"Ocorreu um erro ao tentar trocar a voz: {str(e)}"
