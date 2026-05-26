from __future__ import annotations

from dataclasses import dataclass

from google.genai import types


def _str_prop(desc: str) -> types.Schema:
    return types.Schema(type=types.Type.STRING, description=desc)


@dataclass(frozen=True)
class _NexusModeProfile:
    description: str
    properties: frozenset[str]


_NEXUS_MODE_PROFILES: dict[str, _NexusModeProfile] = {
    "news": _NexusModeProfile(
        description=(
            "Comandos estruturados Nexus para o Modo Noticias. Use apenas: "
            "news_briefing (query opcional, limit), news_history (limit), "
            "news_save_note (item ou briefing + item_index, subject opcional), "
            "news_followup_task (item ou briefing + item_index, due_date opcional), "
            "news_flashcards_generate (item ou briefing + item_index, max_cards opcional), "
            "open_ui (tab: news). Nao use financas, loja, arquivos, ops ou acoes fora de noticias."
        ),
        properties=frozenset(
            {
                "action",
                "query",
                "limit",
                "item",
                "briefing",
                "item_index",
                "subject",
                "due_date",
                "max_cards",
                "tab",
            }
        ),
    ),
    "psych_coach": _NexusModeProfile(
        description=(
            "Comandos estruturados Nexus para Modo Psicologo/Coach. Use apenas apoio seguro: "
            "habit_add, habit_complete, task_add, task_list, goal_add, goal_update, "
            "note_list, note_get, note_save, note_append, open_ui (notes|habits|goals|progress). "
            "Nao use noticias, financas, loja, ops, arquivos ou mensagens externas neste modo."
        ),
        properties=frozenset(
            {
                "action",
                "habit_name",
                "name",
                "description",
                "xp_reward",
                "title",
                "due_date",
                "task_id",
                "target_date",
                "progress",
                "subject",
                "note_id",
                "content",
                "text",
                "tab",
            }
        ),
    ),
}


def _nexus_mode_profile(active_mode: str | None) -> _NexusModeProfile | None:
    return _NEXUS_MODE_PROFILES.get((active_mode or "").strip().lower())


def _apply_gemini_nexus_profile(
    declarations: list[types.FunctionDeclaration],
    active_mode: str | None,
) -> list[types.FunctionDeclaration]:
    profile = _nexus_mode_profile(active_mode)
    if not profile:
        return declarations

    updated: list[types.FunctionDeclaration] = []
    for declaration in declarations:
        if declaration.name != "nexus_command":
            updated.append(declaration)
            continue

        existing_props = declaration.parameters.properties if declaration.parameters else {}
        props = {
            name: schema
            for name, schema in dict(existing_props or {}).items()
            if name in profile.properties
        }
        updated.append(
            types.FunctionDeclaration(
                name="nexus_command",
                description=profile.description,
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties=props,
                    required=["action"],
                ),
            )
        )
    return updated


def _apply_openai_nexus_profile(funcs: list[dict], active_mode: str | None) -> list[dict]:
    profile = _nexus_mode_profile(active_mode)
    if not profile:
        return funcs

    updated: list[dict] = []
    for item in funcs:
        if item.get("function", {}).get("name") != "nexus_command":
            updated.append(item)
            continue

        function = dict(item["function"])
        params = dict(function.get("parameters") or {})
        existing_props = params.get("properties") or {}
        params["properties"] = {
            name: schema
            for name, schema in dict(existing_props).items()
            if name in profile.properties
        }
        params["required"] = ["action"]
        function["description"] = profile.description
        function["parameters"] = params
        updated.append({"type": item.get("type", "function"), "function": function})
    return updated


def build_agent_tool(
    dynamic_tools: list = None,
    allowed_tool_names: set[str] | frozenset[str] | None = None,
    active_mode: str | None = None,
) -> types.Tool:
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
                description=(
                    "Financas Nexus (Aether): gastos/receitas em SQLite. "
                    "Use texto natural (ex.: gastei 50 reais com comida, gasto de ontem 20 reais cafe, ganhei 100 reais)."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "command": _str_prop("Texto do pedido (gasto, receita, relatorio)."),
                    },
                    required=["command"],
                ),
            ),
            types.FunctionDeclaration(
                name="nexus_command",
                description=(
                    "Comandos estruturados Nexus Life OS. action: "
                    "finance_add (type expense|income, amount, category, description, occurred_at opcional ISO date, notes, is_debt), "
                    "finance_list (date_from, date_to opcional), finance_delete (transaction_id ou description/category/occurred_at/type/amount), "
                    "finance_update (transaction_id ou target_description/target_date; new_amount/new_category/new_description/new_notes/new_is_debt), "
                    "habit_complete (habit_name), habit_add (name, description, xp_reward, days_of_week opcional lista 0-6), "
                    "task_add (title, due_date opcional ISO), task_complete (task_id), task_delete (task_id), task_list (due_date, include_done), "
                    "goal_add (name, target_date), goal_update (name, progress), reward_redeem (reward_name), reward_status, "
                    "preset_apply_json (habits: lista de objetos), preset_from_goals (goals ou objectives), "
                    "preset_save (name), preset_apply (name), presets_list, "
                    "theme_list, theme_apply (module, preset_id), theme_generate (module, prompt, name opcional), "
                    "news_briefing (query opcional, limit), news_history (limit), "
                    "news_save_note (item ou briefing + item_index, subject opcional), "
                    "news_followup_task (item ou briefing + item_index, due_date opcional), "
                    "news_flashcards_generate (item ou briefing + item_index, max_cards opcional), "
                    "memory_graph (query opcional, limit, include_markdown), memory_graph_context (query/pergunta para contexto ranqueado), "
                    "memory_graph_export_obsidian (folder/path, query opcional), memory_graph_import_obsidian (folder/path, subject opcional), "
                    "ops_dashboard (open_window opcional), ops_metric_set (key, value, label, unit, target, period, trend), "
                    "open_ui (tab: dashboard|overview|habits|finance|notes|memory_graph|study|tasks|progress|goals|rewards|quiz|news), "
                    "nexus_batch (steps: JSON array ordenado com acoes Nexus; use para pedidos com mais de uma acao), "
                    "note_list (subject opcional), note_get (note_id), note_save (subject, title, content: USE MARKDOWN para formatar, ex: # Título, e ![img](url) para imagens da web), note_append (note_id, text), "
                    "note_summarize (note_id, append_summary opcional, max_sentences opcional), "
                    "note_teach (note_id, question opcional, max_points opcional), subject_teach (subject, question opcional, max_points opcional), "
                    "note_attach_media (note_id, media_url, caption opcional), "
                    "flashcards_generate (note_id ou subject, max_cards), flashcard_review (card_id, quality 0-5), "
                    "flashcards_due (limit), quiz_random (n, area opcional), quiz_attempt_review (attempt_id), "
                    "quiz_flashcards_generate (attempt_id, only_wrong opcional), study_recommendations."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "action": _str_prop("Nome da acao (ver descricao), incluindo memory_graph e memory_graph_context para grafo neural local."),
                        "steps": _str_prop("Para nexus_batch: JSON array ordenado de objetos de comando Nexus."),
                        "module": _str_prop("Modulo/janela Nexus para temas: overview, habits, finance, notes, study, tasks, progress, goals, quiz."),
                        "preset_id": _str_prop("ID do preset visual para theme_apply."),
                        "prompt": _str_prop("Descricao natural do estilo para theme_generate."),
                        "type": _str_prop("Para finance_add: expense ou income."),
                        "amount": _str_prop("Valor numerico como string."),
                        "category": _str_prop("Categoria financeira."),
                        "description": _str_prop("Descricao livre."),
                        "occurred_at": _str_prop("Data ISO YYYY-MM-DD (opcional)."),
                        "notes": _str_prop("Observacoes (opcional)."),
                        "is_debt": _str_prop("0 ou 1 para marcar divida (opcional)."),
                        "transaction_id": _str_prop("ID da transacao para finance_delete ou finance_update."),
                        "target_description": _str_prop("Texto para localizar transacao no finance_update."),
                        "target_category": _str_prop("Categoria para localizar transacao no finance_update."),
                        "target_date": _str_prop("Data para localizar transacao no finance_update ou data alvo ISO para goal_add."),
                        "target_amount": _str_prop("Valor para localizar transacao no finance_update."),
                        "new_amount": _str_prop("Novo valor no finance_update."),
                        "new_category": _str_prop("Nova categoria no finance_update."),
                        "new_description": _str_prop("Nova descricao no finance_update."),
                        "new_notes": _str_prop("Novas observacoes no finance_update."),
                        "new_is_debt": _str_prop("0 ou 1 para atualizar divida no finance_update."),
                        "reward_name": _str_prop("Nome da recompensa para reward_redeem."),
                        "progress": _str_prop("Progresso 0-100 para goal_update."),
                        "habit_name": _str_prop("Nome do habito para completar."),
                        "name": _str_prop("Nome (habito)."),
                        "xp_reward": _str_prop("XP do habito."),
                        "title": _str_prop("Titulo tarefa ou nota."),
                        "due_date": _str_prop("Data ISO tarefa."),
                        "task_id": _str_prop("ID numerico tarefa."),
                        "note_id": _str_prop("ID numerico nota."),
                        "content": _str_prop("Conteudo markdown nota."),
                        "subject": _str_prop("Materia / assunto."),
                        "text": _str_prop("Texto a acrescentar na nota."),
                        "question": _str_prop("Pergunta para note_teach ou subject_teach / modo professor."),
                        "media_url": _str_prop("URL, caminho local ou data URL de imagem para note_attach_media."),
                        "caption": _str_prop("Legenda/alt da imagem para note_attach_media."),
                        "key": _str_prop("Chave da metrica Business/Ops para ops_metric_set."),
                        "value": _str_prop("Valor da metrica Business/Ops para ops_metric_set."),
                        "target": _str_prop("Meta da metrica Business/Ops para ops_metric_set."),
                        "label": _str_prop("Rotulo legivel da metrica Business/Ops."),
                        "unit": _str_prop("Unidade da metrica: BRL, count, percent, ratio."),
                        "period": _str_prop("Periodo da metrica Business/Ops."),
                        "trend": _str_prop("Direcao desejada: up ou down."),
                        "open_window": _str_prop("true/false para abrir janela ao montar painel."),
                        "append_summary": _str_prop("true/false para anexar resumo IA na nota."),
                        "max_sentences": _str_prop("Quantidade maxima de frases no resumo."),
                        "max_points": _str_prop("Quantidade maxima de pontos para note_teach ou subject_teach."),
                        "card_id": _str_prop("ID flashcard."),
                        "quality": _str_prop("Qualidade revisao 0-5."),
                        "max_cards": _str_prop("Maximo de flashcards para flashcards_generate."),
                        "attempt_id": _str_prop("ID da tentativa para quiz_attempt_review ou quiz_flashcards_generate."),
                        "only_wrong": _str_prop("true/false para gerar flashcards apenas dos erros do simulado."),
                        "query": _str_prop("Tema de pesquisa para news_briefing."),
                        "limit": _str_prop("Limite lista."),
                        "include_markdown": _str_prop("true/false para incluir arquivos .md no memory_graph."),
                        "folder": _str_prop("Pasta local para import/export Obsidian Markdown."),
                        "path": _str_prop("Caminho local alternativo para import/export Obsidian Markdown."),
                        "item": _str_prop("Objeto JSON da noticia selecionada para news_save_note."),
                        "briefing": _str_prop("Objeto JSON do briefing para news_save_note."),
                        "item_index": _str_prop("Indice 1-based da noticia dentro do briefing para news_save_note."),
                        "n": _str_prop("Numero de questoes quiz."),
                        "area": _str_prop("Area ENEM / quiz."),
                        "habits": _str_prop("JSON array de habitos para preset_apply_json."),
                        "goals": _str_prop("Lista ou texto de objetivos para preset_from_goals."),
                        "objectives": _str_prop("Alias de goals para preset_from_goals."),
                        "preset_name": _str_prop("Nome opcional do preset gerado/aplicado."),
                        "tab": _str_prop("Aba UI Nexus."),
                        "include_done": _str_prop("true/false para task_list."),
                        "date_from": _str_prop("Inicio periodo finance_list."),
                        "date_to": _str_prop("Fim periodo finance_list."),
                    },
                    required=["action"],
                ),
            ),
            types.FunctionDeclaration(
                name="control_visualizer",
                description=(
                    "Controla o visualizador Jarvis: estado visual do particle core "
                    "(inativo, escutando, pensando, falando, executando, alerta), emocao, posicao, visibilidade e microfone."
                ),
                parameters=types.Schema(
                    type=types.Type.OBJECT,
                    properties={
                        "command": _str_prop(
                            "Comando para o visualizador. Exemplos: 'estado executando sincronizando comandos', "
                            "'estado alerta', 'emocao feliz', 'mover para superior direito', 'esconda', 'mutar microfone'."
                        ),
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
            "nexus_command",
            "control_visualizer", "whatsapp_send", "control_spotify"
        }
        for tool in dynamic_tools:
            if allowed_tool_names is not None and tool.name not in allowed_tool_names:
                continue
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
            
    declarations = _apply_gemini_nexus_profile(declarations, active_mode)

    if allowed_tool_names is not None:
        allowed = set(allowed_tool_names)
        declarations = [fd for fd in declarations if fd.name in allowed]

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


def build_openai_agent_tools(
    dynamic_tools: list = None,
    allowed_tool_names: set[str] | frozenset[str] | None = None,
    active_mode: str | None = None,
) -> list[dict]:
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
            "Financas Nexus Aether (SQLite): gastos e receitas em linguagem natural.",
            {"command": {"type": "string", "description": "Texto do pedido."}},
            ["command"],
        ),
        _openai_fn(
            "nexus_command",
            (
                "Nexus Life OS estruturado. action: finance_add, finance_list, finance_delete, habit_complete, habit_add, "
                "finance_update, "
                "task_add, task_complete, task_delete, task_list, goal_add, goal_update, reward_redeem, reward_status, preset_apply_json, open_ui, "
                "theme_list, theme_apply, theme_generate, "
                "news_briefing, news_history, news_save_note, news_followup_task, news_flashcards_generate, "
                "memory_graph, memory_graph_context, memory_graph_export_obsidian, memory_graph_import_obsidian, "
                "ops_dashboard, ops_metric_set, "
                "nexus_batch (steps em ordem para pedidos com varias acoes; open_ui aceita dashboard|overview|habits|finance|notes|memory_graph|study|tasks|progress|goals|rewards|quiz|news), "
                "note_list, note_get, note_save (content: USE MARKDOWN ex: # Titulo, ![img](url)), note_append, note_summarize, note_teach, subject_teach, note_attach_media, flashcards_generate, flashcard_review, "
                "flashcards_due, quiz_random, quiz_attempt_review, quiz_flashcards_generate, study_recommendations. "
                "Campos opcionais conforme a acao."
            ),
            {
                "action": {"type": "string", "description": "Acao principal."},
                "steps": {"type": "string", "description": "JSON array ordenado para nexus_batch."},
                "module": {"type": "string", "description": "Modulo Nexus para temas por janela."},
                "preset_id": {"type": "string", "description": "Preset visual para theme_apply."},
                "prompt": {"type": "string", "description": "Descricao de estilo para theme_generate."},
                "type": {"type": "string"},
                "amount": {"type": "string"},
                "category": {"type": "string"},
                "description": {"type": "string"},
                "occurred_at": {"type": "string"},
                "notes": {"type": "string"},
                "transaction_id": {"type": "string"},
                "target_description": {"type": "string"},
                "target_category": {"type": "string"},
                "target_amount": {"type": "string"},
                "new_amount": {"type": "string"},
                "new_category": {"type": "string"},
                "new_description": {"type": "string"},
                "new_notes": {"type": "string"},
                "new_is_debt": {"type": "string"},
                "reward_name": {"type": "string"},
                "progress": {"type": "string"},
                "target_date": {"type": "string"},
                "habit_name": {"type": "string"},
                "name": {"type": "string"},
                "title": {"type": "string"},
                "due_date": {"type": "string"},
                "task_id": {"type": "string"},
                "note_id": {"type": "string"},
                "content": {"type": "string"},
                "subject": {"type": "string"},
                "text": {"type": "string"},
                "question": {"type": "string"},
                "media_url": {"type": "string"},
                "caption": {"type": "string"},
                "key": {"type": "string"},
                "value": {"type": "string"},
                "target": {"type": "string"},
                "label": {"type": "string"},
                "unit": {"type": "string"},
                "period": {"type": "string"},
                "trend": {"type": "string"},
                "open_window": {"type": "string"},
                "append_summary": {"type": "string"},
                "max_sentences": {"type": "string"},
                "max_points": {"type": "string"},
                "card_id": {"type": "string"},
                "quality": {"type": "string"},
                "max_cards": {"type": "string"},
                "attempt_id": {"type": "string"},
                "only_wrong": {"type": "string"},
                "tab": {"type": "string"},
                "query": {"type": "string"},
                "limit": {"type": "string"},
                "include_markdown": {"type": "string"},
                "folder": {"type": "string"},
                "path": {"type": "string"},
                "item": {"type": "string"},
                "briefing": {"type": "string"},
                "item_index": {"type": "string"},
                "habits": {"type": "string"},
                "n": {"type": "string"},
                "area": {"type": "string"},
            },
            ["action"],
        ),
        _openai_fn(
            "control_visualizer",
            "Controla o visualizador Jarvis: estado visual do particle core, emocao, posicao, visibilidade e microfone.",
            {"command": {"type": "string", "description": "Exemplos: estado executando sincronizando comandos, estado alerta, emocao feliz, top_right, bottom_left, hide, mutar microfone."}},
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
            "open_windows_app",
            "Gerencia apps Windows: list_installed, list_running, open_app, open_batch (virgulas), close_app, focus_app, write_to_notepad.",
            {
                "action": {"type": "string", "description": "Acao."},
                "target": {"type": "string", "description": "Nome do app ou texto."},
                "argument": {"type": "string", "description": "Argumento extra."},
            },
            ["action"],
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
            if allowed_tool_names is not None and tool.name not in allowed_tool_names:
                continue
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
            
    funcs = _apply_openai_nexus_profile(funcs, active_mode)

    if allowed_tool_names is not None:
        allowed = set(allowed_tool_names)
        funcs = [item for item in funcs if item["function"]["name"] in allowed]

    return funcs
