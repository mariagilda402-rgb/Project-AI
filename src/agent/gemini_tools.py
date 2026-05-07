from __future__ import annotations

from google.genai import types


def _str_prop(desc: str) -> types.Schema:
    return types.Schema(type=types.Type.STRING, description=desc)


def build_agent_tool() -> types.Tool:
    """Declaracoes Gemini (function calling) — 7 funcoes consolidadas."""
    return types.Tool(
        function_declarations=[
            types.FunctionDeclaration(
                name="analyze_screen",
                description=(
                    "Captura a tela principal e envia ao modelo de visao. "
                    "Use quando precisar VER o monitor. Nao use em saudacoes."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "instruction": _str_prop("O que observar na tela."),
                    },
                    required=["instruction"],
                ),
            ),
            types.FunctionDeclaration(
                name="search_web",
                description=(
                    "Pesquisa na internet de forma invisível e te retorna os resultados em texto. "
                    "SEMPRE use para descobrir coisas, pesquisar, ver clima, noticias, fatos atuais, cotacoes."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "query": _str_prop("Texto da busca."),
                    },
                    required=["query"],
                ),
            ),
            types.FunctionDeclaration(
                name="open_or_run",
                description=(
                    "Abre app, URL específica, navegador ou executa comando desktop para o usuário ver na tela dele. "
                    "Exemplos de target: 'Spotify', 'notepad', 'chrome', "
                    "'https://youtube.com', 'https://google.com/search?q=gatos'. "
                    "USE SOMENTE quando o usuário PEDIR EXPLICITAMENTE para ABRIR uma página, janela ou navegador. "
                    "NUNCA use para VOCÊ pesquisar coisas (use search_web para isso)."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "target": _str_prop(
                            "Nome do app, URL completa, ou 'chrome'."
                        ),
                    },
                    required=["target"],
                ),
            ),
            types.FunctionDeclaration(
                name="run_utility",
                description=(
                    "Utilitarios do sistema. Acoes disponiveis:\n"
                    "- clipboard_read: le o clipboard\n"
                    "- clipboard_write: copia texto (argument = texto)\n"
                    "- timer_set: cria timer (argument = '5min' ou '22:00', detail = descricao)\n"
                    "- timer_list: lista timers ativos\n"
                    "- system_info: info do PC (CPU, RAM, disco)\n"
                    "- volume_up, volume_down, mute, play_pause, next, previous, stop: controle de midia\n"
                    "- note_save: salva nota (argument = titulo, detail = conteudo)\n"
                    "- note_list: lista notas\n"
                    "- note_search: busca notas (argument = termo)\n"
                    "- note_delete: deleta nota (argument = titulo)"
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "action": _str_prop(
                            "Acao: clipboard_read, clipboard_write, timer_set, timer_list, "
                            "system_info, volume_up, volume_down, mute, play_pause, next, "
                            "previous, stop, note_save, note_list, note_search, note_delete"
                        ),
                        "argument": _str_prop("Argumento principal (texto, duracao, titulo, termo de busca)."),
                        "detail": _str_prop("Detalhe extra (conteudo da nota, label do timer)."),
                    },
                    required=["action"],
                ),
            ),
            types.FunctionDeclaration(
                name="manage_memory",
                description=(
                    "Gerencia a memoria de longo prazo. Salva fatos importantes do usuario "
                    "(nome, preferencias, horarios, datas) ou busca/lista memorias anteriores.\n"
                    "Acoes: save, search, list, delete"
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "action": _str_prop("save | search | list | delete"),
                        "content": _str_prop(
                            "Conteudo: fato a salvar, termo de busca, ou ID a deletar."
                        ),
                        "category": _str_prop(
                            "Categoria: geral, pessoal, horario, preferencia, lembrete (default: geral)."
                        ),
                    },
                    required=["action"],
                ),
            ),
            types.FunctionDeclaration(
                name="run_productivity_command",
                description="Habitos e tarefas no conector de produtividade local.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "command": _str_prop("Texto do pedido (habito, tarefa)."),
                    },
                    required=["command"],
                ),
            ),
            types.FunctionDeclaration(
                name="run_finance_command",
                description="Gastos e relatorios no modulo financeiro local.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "command": _str_prop("Texto do pedido (gasto, relatorio)."),
                    },
                    required=["command"],
                ),
            ),
            types.FunctionDeclaration(
                name="control_visualizer",
                description="Controla o visualizador de midia ou modo de exibicao.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "command": _str_prop("Comando para o visualizador."),
                    },
                    required=["command"],
                ),
            ),
            types.FunctionDeclaration(
                name="whatsapp_send",
                description=(
                    "Envia uma mensagem de WhatsApp para alguem. "
                    "IMPORTANTE: Você deve pedir a confirmação explícita do número e da mensagem para o usuário ANTES de usar essa ferramenta. "
                    "Nunca envie sem ele ter concordado com o texto e o número."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "target": _str_prop("Numero de telefone ou nome da pessoa."),
                        "message": _str_prop("Texto da mensagem a enviar."),
                    },
                    required=["target", "message"],
                ),
            ),
        ]
    )


def _openai_fn(
    name: str,
    description: str,
    properties: dict[str, dict],
    required: list[str],
) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


def build_openai_agent_tools() -> list[dict]:
    """7 funcoes consolidadas no formato OpenAI (Groq / NVIDIA)."""
    return [
        _openai_fn(
            "analyze_screen",
            "Captura a tela e interpreta com modelo de visao. Nao use em saudacoes.",
            {"instruction": {"type": "string", "description": "O que observar na captura."}},
            ["instruction"],
        ),
        _openai_fn(
            "search_web",
            "Pesquisa invisível na internet e retorna para você ler. SEMPRE use para descobrir coisas, pesquisar clima, noticias, fatos.",
            {"query": {"type": "string", "description": "Texto da busca."}},
            ["query"],
        ),
        _openai_fn(
            "open_or_run",
            (
                "Abre app, URL, navegador ou comando PARA O USUÁRIO VER. "
                "Exemplos: 'Spotify', 'notepad', 'chrome', 'https://youtube.com'. "
                "NUNCA use para você pesquisar. USE SOMENTE se o usuário pedir para abrir algo."
            ),
            {"target": {"type": "string", "description": "App, URL, ou comando."}},
            ["target"],
        ),
        _openai_fn(
            "run_utility",
            (
                "Utilitarios: clipboard_read, clipboard_write, timer_set, timer_list, "
                "system_info, volume_up, volume_down, mute, play_pause, next, previous, "
                "stop, note_save, note_list, note_search, note_delete."
            ),
            {
                "action": {"type": "string", "description": "Nome da acao (ex: timer_set, volume_up, clipboard_read)."},
                "argument": {"type": "string", "description": "Argumento principal (texto, duracao, titulo)."},
                "detail": {"type": "string", "description": "Detalhe extra (conteudo, label)."},
            },
            ["action"],
        ),
        _openai_fn(
            "manage_memory",
            (
                "Gerencia memoria de longo prazo. Salva fatos do usuario "
                "(nome, preferencias, horarios), busca ou lista memorias. "
                "Acoes: save, search, list, delete."
            ),
            {
                "action": {"type": "string", "description": "save | search | list | delete"},
                "content": {"type": "string", "description": "Fato, termo de busca, ou ID."},
                "category": {"type": "string", "description": "geral | pessoal | horario | preferencia | lembrete"},
            },
            ["action"],
        ),
        _openai_fn(
            "run_productivity_command",
            "Produtividade local (habitos, tarefas).",
            {"command": {"type": "string", "description": "Texto do pedido."}},
            ["command"],
        ),
        _openai_fn(
            "run_finance_command",
            "Financas locais (gastos, relatorios).",
            {"command": {"type": "string", "description": "Texto do pedido."}},
            ["command"],
        ),
        _openai_fn(
            "control_visualizer",
            "Controla o visualizador de midia ou modo de exibicao.",
            {"command": {"type": "string", "description": "Comando para o visualizador."}},
            ["command"],
        ),
        _openai_fn(
            "whatsapp_send",
            "Envia mensagem de WhatsApp. IMPORTANTE: Confirme o número e a mensagem com o usuário ANTES de usar.",
            {
                "target": {"type": "string", "description": "Numero ou nome."},
                "message": {"type": "string", "description": "Mensagem."},
            },
            ["target", "message"],
        ),
    ]
