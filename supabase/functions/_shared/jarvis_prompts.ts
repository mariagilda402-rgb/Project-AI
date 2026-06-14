export type JarvisContext = {
  habits_today?: number;
  habits_total?: number;
  pending_tasks?: number;
  next_alarm?: string;
  goals?: { name: string; progress: number }[];
  user_name?: string;
};

export type ChatTurn = { role: "user" | "assistant"; content: string };

export function buildJarvisSystemPrompt(source?: string): string {
  return `Você é o Jarvis, assistente pessoal do app Nexus (hábitos, tarefas, metas, finanças, estudos, alarmes, rotinas).
Responda sempre em português brasileiro, de forma natural, direta e útil.
Origem: ${source || "mobile"}.

Regras:
- Use os dados de contexto quando fornecidos; não invente números ou nomes.
- Para criar hábito, tarefa ou registrar finança, responda PRIMEIRO com uma linha ACTION ACTION ACTION: ACTION: create_habit | name: NOME | time: HH:MM (opcional)
  ou ACTION: create_task | title: TITULO | priority: low|medium|high
  ou TOOL: log_finance | type: income|expense | amount: NUMERO | desc: TEXTO
  Depois uma frase curta confirmando a ação ao usuário.
- Para ajustar meta: TOOL: adjust_goal | name: NOME_PARCIAL | delta: +10 ou -10
- Se a pergunta for conversa geral, responda normalmente sem TOOL.
- Seja conciso em voz (2–4 frases); em texto pode ser um pouco mais detalhado.
- Nunca diga que é um bot programado ou liste capacidades genéricas.`;
}

export function formatContextBlock(ctx?: JarvisContext): string {
  if (!ctx) return "";
  const lines: string[] = [];
  if (ctx.user_name) lines.push(`Usuário: ${ctx.user_name}`);
  if (ctx.habits_total != null) lines.push(`Hábitos hoje: ${ctx.habits_today ?? 0}/${ctx.habits_total}`);
  if (ctx.pending_tasks != null) lines.push(`Tarefas pendentes: ${ctx.pending_tasks}`);
  if (ctx.next_alarm) lines.push(`Próximo alarme: ${ctx.next_alarm}`);
  if (ctx.goals?.length) {
    lines.push(
      "Metas: " + ctx.goals.map((g) => `${g.name} (${g.progress}%)`).join(", ")
    );
  }
  return lines.length ? `\nContexto Nexus:\n${lines.join("\n")}` : "";
}

export function formatHistoryBlock(history?: ChatTurn[]): string {
  if (!history?.length) return "";
  const tail = history.slice(-8);
  return (
    "\nHistórico recente:\n" +
    tail.map((t) => `${t.role === "user" ? "Usuário" : "Jarvis"}: ${t.content}`).join("\n")
  );
}

export function buildChatUserPrompt(
  message: string,
  source?: string,
  ctx?: JarvisContext,
  history?: ChatTurn[]
): string {
  return `${buildJarvisSystemPrompt(source)}${formatContextBlock(ctx)}${formatHistoryBlock(history)}\n\nMensagem atual do usuário:\n${message}`;
}

export const NOTE_ACTION_PROMPTS: Record<string, (content: string) => string> = {
  summarize_text: (c) =>
    `Resuma o texto abaixo em português brasileiro.
Formato: título em uma linha, depois bullet points objetivos, depois "Tempo de leitura: ~X min".
Texto:\n\n${c}`,
  expand_text: (c) =>
    `Expanda o texto mantendo o tom e estilo do autor. Adicione exemplos práticos e detalhes úteis em português:\n\n${c}`,
  translate: (c) =>
    `Traduza para português brasileiro preservando formatação markdown e listas:\n\n${c}`,
  deep_search: (c) =>
    `Explique de forma didática sobre "${c}" em português.
Use seções: Visão geral, Pontos-chave, Exemplos, Próximos passos.`,
  summarize_video: (c) =>
    `O usuário quer um resumo de estudo do vídeo YouTube: ${c}
Estruture: Título provável, Tópicos principais (bullets), Conceitos-chave, Perguntas de revisão, Timestamps sugeridos (estimados).`,
  generate_image: (c) =>
    `Descreva uma imagem educativa detalhada (para ilustrar estudo) sobre: ${c}
Inclua composição, cores e elementos visuais.`,
};

export type ParsedTool =
  | { type: "create_habit"; name: string; time?: string }
  | { type: "create_task"; title: string; priority: string }
  | { type: "log_finance"; financeType: string; amount: number; desc: string }
  | { type: "adjust_goal"; name: string; delta: number };

export function parseToolFromReply(text: string): ParsedTool | null {
  const line = text.split("\n").find((l) => /^TOOL:/i.test(l.trim()));
  if (!line) return null;
  const body = line.replace(/^TOOL:\s*/i, "").trim();
  const parts: Record<string, string> = {};
  body.split("|").forEach((segment) => {
    const idx = segment.indexOf(":");
    if (idx === -1) return;
    const key = segment.slice(0, idx).trim().toLowerCase();
    parts[key] = segment.slice(idx + 1).trim();
  });
  const action = (parts.create_habit ? "create_habit" : parts.create_task ? "create_task" : parts.log_finance ? "log_finance" : parts.adjust_goal ? "adjust_goal" : body.split("|")[0]?.trim().toLowerCase()) || "";
  if (action.includes("create_habit")) {
    return { type: "create_habit", name: parts.name || "Novo hábito", time: parts.time };
  }
  if (action.includes("create_task")) {
    return { type: "create_task", title: parts.title || "Nova tarefa", priority: parts.priority || "medium" };
  }
  if (action.includes("log_finance")) {
    return {
      type: "log_finance",
      financeType: parts.type || "expense",
      amount: parseFloat(parts.amount || "0") || 0,
      desc: parts.desc || "",
    };
  }
  if (action.includes("adjust_goal")) {
    return {
      type: "adjust_goal",
      name: parts.name || "",
      delta: parseInt(String(parts.delta || "0").replace("+", ""), 10) || 0,
    };
  }
  return null;
}

export function stripToolLine(text: string): string {
  return text
    .split("\n")
    .filter((l) => !/^TOOL:/i.test(l.trim()))
    .join("\n")
    .trim();
}
