from __future__ import annotations

from google.genai import types


def _str_prop(desc: str) -> types.Schema:
    return types.Schema(type=types.Type.STRING, description=desc)


def build_agent_tool(dynamic_tools: list = None) -> types.Tool:
    """Declaracoes Gemini (function calling) — funcoes consolidadas + skills dinamicas."""
    declarations = [
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
            types.FunctionDeclaration(
                name="control_spotify",
                description=(
                    "Controla o Spotify Desktop localmente. Acoes:\n"
                    "- play / pause: alterna play/pause\n"
                    "- next / skip: proxima musica\n"
                    "- previous: musica anterior\n"
                    "- current: mostra a musica tocando agora\n"
                    "- search_and_play: busca e tenta tocar uma musica/artista (argument = nome)\n"
                    "- open: abre o Spotify"
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "action": _str_prop("Acao: play, pause, next, previous, current, search_and_play, open"),
                        "argument": _str_prop("Nome da musica/artista para search_and_play."),
                    },
                    required=["action"],
                ),
            ),
            types.FunctionDeclaration(
                name="manage_files",
                description=(
                    "Gerencia arquivos e pastas do Windows do usuario. Acoes:\n"
                    "- list_dir: lista conteudo de uma pasta\n"
                    "- count_files: conta arquivos (argument = extensao opcional)\n"
                    "- file_info: info de um arquivo\n"
                    "- search_files: busca recursiva (argument = termo)\n"
                    "- create_dir: cria pasta\n"
                    "- move_file: move (argument = destino)\n"
                    "- copy_file: copia (argument = destino)\n"
                    "- delete_file: deleta\n"
                    "- rename_file: renomeia (argument = novo nome)\n"
                    "- disk_usage: espaco usado\n"
                    "- read_text_file: le conteudo de arquivo texto\n"
                    "- write_text_file: escreve/cria arquivo (argument = conteudo)\n"
                    "Pastas aceitas: downloads, documentos, desktop, imagens, musicas, videos."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "action": _str_prop("Acao a executar."),
                        "path": _str_prop("Caminho ou alias da pasta (ex: 'downloads', 'documentos', 'Downloads/subfolder')."),
                        "argument": _str_prop("Argumento extra: destino, novo nome, filtro, conteudo."),
                    },
                    required=["action", "path"],
                ),
            ),
            types.FunctionDeclaration(
                name="open_windows_app",
                description=(
                    "USE ESTA FERRAMENTA SEMPRE que o usuário pedir para abrir, fechar ou interagir com QUALQUER aplicativo ou janela (Bloco de Notas, Chrome, Spotify, etc). "
                    "Ações: open_app, close_app, list_installed, list_running, focus_app, write_to_notepad."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "action": _str_prop("Acao: open_app, close_app, list_installed, list_running, focus_app, write_to_notepad"),
                        "target": _str_prop("Nome do app (ex: 'notepad'), URL, ou texto."),
                        "argument": _str_prop("Extra."),
                    },
                    required=["action"],
                ),
            ),
            types.FunctionDeclaration(
                name="set_ai_volume",
                description="Ajusta o volume da voz da própria IA (TTS).",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "volume": _str_prop("Volume em porcentagem (ex: '100%', '50%', '+10%', '-20%')."),
                    },
                    required=["volume"],
                ),
            ),
            types.FunctionDeclaration(
                name="delegate_to_agent",
                description="Delega uma tarefa, dúvida, ou instrução para outro agente especializado do sistema (ex: JARVIS para programação ou Assistente para conversas). Use isso para debater ou pedir ajuda.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "target_agent": _str_prop("Nome exato do agente destino (ex: JARVIS)."),
                        "query": _str_prop("A pergunta, problema ou mensagem que você quer enviar a ele."),
                    },
                    required=["target_agent", "query"],
                ),
            ),
            types.FunctionDeclaration(
                name="generate_image",
                description=(
                    "Gera uma imagem usando IA a partir de um texto descritivo. "
                    "Salva automaticamente na pasta de imagens geradas com nome identificável. "
                    "Após gerar, use show_image para exibir se o usuário pedir."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "prompt": _str_prop("Descrição detalhada da imagem em inglês (ex: 'beautiful waterfall in a tropical forest, 4k')."),
                        "label": _str_prop("Nome curto em português para identificar a imagem depois (ex: 'cachoeira', 'gato fofo', 'pôr do sol')."),
                    },
                    required=["prompt"],
                ),
            ),
            types.FunctionDeclaration(
                name="show_image",
                description=(
                    "Exibe uma imagem gerada anteriormente em uma janela flutuante. "
                    "Pode receber o caminho completo OU o nome/label da imagem (ex: 'cachoeira'). "
                    "Busca automaticamente no histórico de imagens geradas."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "filepath": _str_prop("Caminho do arquivo OU nome/label da imagem (ex: 'cachoeira')."),
                    },
                    required=["filepath"],
                ),
            ),
            types.FunctionDeclaration(
                name="list_generated_images",
                description="Lista todas as imagens geradas pela IA com seus nomes e datas.",
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={},
                ),
            ),
            types.FunctionDeclaration(
                name="agent_task",
                description=(
                    "Executa tarefas COMPLEXAS que exigem múltiplos passos e ferramentas diferentes. "
                    "A IA cria um plano automático, executa cada passo com retry e replan. "
                    "Exemplos: 'pesquise X e salve em arquivo', 'organize meus downloads'. "
                    "NÃO use para comandos simples de 1 ação."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "goal": _str_prop("Descrição completa do objetivo a realizar."),
                        "priority": _str_prop("low | normal | high (default: normal)"),
                    },
                    required=["goal"],
                ),
            ),
            types.FunctionDeclaration(
                name="save_memory",
                description=(
                    "Salva um fato pessoal importante do usuário na memória de longo prazo. "
                    "Chame SILENCIOSAMENTE quando o usuário revelar: nome, idade, cidade, profissão, "
                    "preferências, hobbies, relacionamentos, projetos ou planos futuros. "
                    "NÃO chame para: clima, comandos, pesquisas. NÃO anuncie que está salvando."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "category": _str_prop(
                            "identity | preferences | projects | relationships | wishes | notes"
                        ),
                        "key": _str_prop("Chave snake_case (ex: name, favorite_food, best_friend)"),
                        "value": _str_prop("Valor conciso (ex: Jamil, pizza, João)"),
                    },
                    required=["category", "key", "value"],
                ),
            ),
    ]
    if dynamic_tools:
        # Ferramentas que já foram declaradas estaticamente acima
        manually_declared = {
            "manage_files", "open_windows_app", "set_ai_volume", "delegate_to_agent",
            "generate_image", "show_image", "list_generated_images", "run_finance_command",
            "control_visualizer", "whatsapp_send", "control_spotify"
        }
        for tool in dynamic_tools:
            if tool.name in manually_declared:
                continue

            # Converte a spec do Tool para Schema
            props = {}
            required = []
            if getattr(tool, "parameters", None) and "properties" in tool.parameters:
                for k, v in tool.parameters["properties"].items():
                    props[k] = _str_prop(v.get("description", ""))
                required = tool.parameters.get("required", [])
            
            declarations.append(
                types.FunctionDeclaration(
                    name=tool.name,
                    description=tool.description,
                    parameters=types.Schema(
                        type=types.Type.OBJECT,
                        properties=props,
                        required=required,
                    ) if props else None,
                )
            )
            
    return types.Tool(function_declarations=declarations)


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


def build_openai_agent_tools(dynamic_tools: list = None) -> list[dict]:
    """funcoes consolidadas no formato OpenAI (Groq / NVIDIA) + skills dinamicas."""
    funcs = [
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
            "Move a janela visualizadora (ex. top_right, hide).",
            {"command": {"type": "string", "description": "top_right, bottom_left, hide, etc."}},
            ["command"],
        ),
        _openai_fn(
            "set_ai_volume",
            "Ajusta volume do TTS.",
            {"volume": {"type": "string", "description": "ex: '100%'"}},
            ["volume"],
        ),
        _openai_fn(
            "delegate_to_agent",
            "Consulta ou passa o bastão para outro agente especializado do sistema (ex: JARVIS).",
            {
                "target_agent": {"type": "string", "description": "Nome do agente"},
                "query": {"type": "string", "description": "Mensagem para ele"}
            },
            ["target_agent", "query"],
        ),
        _openai_fn(
            "control_spotify",
            "Controla Spotify Desktop: play, pause, next, previous, current, search_and_play (argument=nome), open.",
            {
                "action": {"type": "string", "description": "play, pause, next, previous, current, search_and_play, open"},
                "argument": {"type": "string", "description": "Nome da musica/artista."},
            },
            ["action"],
        ),
        _openai_fn(
            "manage_files",
            "Gerencia arquivos/pastas: list_dir, count_files, file_info, search_files, create_dir, move_file, copy_file, delete_file, rename_file, disk_usage, read_text_file, write_text_file. Pastas: downloads, documentos, desktop, imagens, musicas, videos.",
            {
                "action": {"type": "string", "description": "Acao a executar."},
                "path": {"type": "string", "description": "Caminho ou alias (ex: downloads)."},
                "argument": {"type": "string", "description": "Argumento extra."},
            },
            ["action", "path"],
        ),
        _openai_fn(
            "manage_apps",
            "Gerencia apps Windows: list_installed, list_running, open_app, open_batch (virgulas), close_app, focus_app, write_to_notepad.",
            {
                "action": {"type": "string", "description": "Acao."},
                "target": {"type": "string", "description": "Nome do app ou texto."},
                "argument": {"type": "string", "description": "Argumento extra."},
            },
            ["action"],
        ),
        _openai_fn(
            "set_ai_volume",
            "Ajusta o volume da voz da própria IA (TTS).",
            {
                "volume": {"type": "string", "description": "Volume em % (ex: 100%, +10%, -20%)."},
            },
            ["volume"],
        ),
        _openai_fn(
            "agent_task",
            "Executa tarefas COMPLEXAS multi-step com planejamento automático, retry e replan. Ex: 'pesquise X e salve em arquivo'. NÃO use para comandos simples.",
            {
                "goal": {"type": "string", "description": "Descrição completa do objetivo."},
                "priority": {"type": "string", "description": "low | normal | high (default: normal)"},
            },
            ["goal"],
        ),
        _openai_fn(
            "save_memory",
            "Salva fato pessoal do usuário na memória de longo prazo (silenciosamente). Categorias: identity, preferences, projects, relationships, wishes, notes.",
            {
                "category": {"type": "string", "description": "identity | preferences | projects | relationships | wishes | notes"},
                "key": {"type": "string", "description": "Chave snake_case (ex: name, hobby)"},
                "value": {"type": "string", "description": "Valor conciso"},
            },
            ["category", "key", "value"],
        ),
    ]
    
    if dynamic_tools:
        for tool in dynamic_tools:
            props = {}
            required = []
            if getattr(tool, "parameters", None) and "properties" in tool.parameters:
                props = tool.parameters["properties"]
                required = tool.parameters.get("required", [])
            
            funcs.append(_openai_fn(
                tool.name,
                tool.description,
                props,
                required
            ))
            
    return funcs
