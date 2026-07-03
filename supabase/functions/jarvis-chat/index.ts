import { serve } from "https://deno.land/std@0.168.0/http/server.ts";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2.39.0";
import {
  buildChatUserPrompt,
  parseToolFromReply,
  stripToolLine,
  type JarvisContext,
  type ChatTurn,
} from "../_shared/jarvis_prompts.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

async function callGemini(prompt: string, apiKey: string, model: string): Promise<string> {
  const geminiRes = await fetch(
    `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${apiKey}`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        contents: [{ role: "user", parts: [{ text: prompt }] }],
      }),
    }
  );
  const geminiData = await geminiRes.json();
  return (
    geminiData?.candidates?.[0]?.content?.parts?.[0]?.text ||
    "Não consegui gerar uma resposta agora."
  );
}

async function executeTool(
  supabase: ReturnType<typeof createClient>,
  userId: string,
  tool: NonNullable<ReturnType<typeof parseToolFromReply>>
): Promise<string | null> {
  const now = new Date().toISOString();
  const id = Date.now();

  if (tool.type === "create_habit") {
    const row = {
      id,
      name: tool.name,
      active: 1,
      current_streak: 0,
      period: "all",
      alarm_time: tool.time || null,
      target_time: tool.time || null,
      user_id: userId,
      updated_at: now,
      created_at: now,
      is_deleted: 0,
    };
    const { error } = await supabase.from("habits").upsert(row);
    return error ? null : `Hábito "${tool.name}" criado.`;
  }
  if (tool.type === "create_task") {
    const row = {
      id,
      title: tool.title,
      name: tool.title,
      priority: tool.priority,
      status: "todo",
      points_reward: 10,
      user_id: userId,
      updated_at: now,
      created_at: now,
      is_deleted: 0,
    };
    const { error } = await supabase.from("tasks").upsert(row);
    return error ? null : `Tarefa "${tool.title}" adicionada.`;
  }
  if (tool.type === "log_finance") {
    const row = {
      id,
      type: tool.financeType,
      amount: tool.amount,
      description: tool.desc,
      category: "jarvis",
      occurred_at: now,
      user_id: userId,
      updated_at: now,
      created_at: now,
      is_deleted: 0,
    };
    const { error } = await supabase.from("finance_transactions").upsert(row);
    return error ? null : `Finança registrada: R$ ${tool.amount}.`;
  }
  if (tool.type === "adjust_goal") {
    const { data: goals } = await supabase
      .from("nexus_goals")
      .select("id,name,progress")
      .eq("user_id", userId)
      .eq("is_deleted", 0);
    const goal = (goals || []).find((g: { name: string }) =>
      (g.name || "").toLowerCase().includes(tool.name.toLowerCase())
    );
    if (!goal) return null;
    const progress = Math.max(0, Math.min(100, (goal.progress || 0) + tool.delta));
    const { error } = await supabase
      .from("nexus_goals")
      .update({ progress, updated_at: now })
      .eq("id", goal.id);
    return error ? null : `Meta "${goal.name}" agora em ${progress}%.`;
  }
  return null;
}

serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const body = await req.json();
    const message = body.message;
    const source = body.source || "mobile";
    const context = body.context as JarvisContext | undefined;
    const history = body.history as ChatTurn[] | undefined;

    if (!message || typeof message !== "string") {
      return new Response(JSON.stringify({ error: "message required" }), {
        status: 400,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const apiKey = Deno.env.get("GEMINI_API_KEY");
    const model = Deno.env.get("GEMINI_MODEL") || "gemini-2.0-flash";
    if (!apiKey) {
      return new Response(JSON.stringify({ error: "GEMINI_API_KEY not configured" }), {
        status: 503,
        headers: { ...corsHeaders, "Content-Type": "application/json" },
      });
    }

    const authHeader = req.headers.get("Authorization");
    const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
    const supabaseAnon = Deno.env.get("SUPABASE_ANON_KEY") ?? "";
    let userId: string | null = null;
    let supabase: ReturnType<typeof createClient> | null = null;

    if (authHeader && supabaseUrl && supabaseAnon) {
      supabase = createClient(supabaseUrl, supabaseAnon, {
        global: { headers: { Authorization: authHeader } },
      });
      const { data: userData } = await supabase.auth.getUser();
      userId = userData?.user?.id ?? null;
    }

    const prompt = buildChatUserPrompt(message, source, context, history);
    let rawReply = await callGemini(prompt, apiKey, model);
    let actionResult: string | null = null;

    const tool = parseToolFromReply(rawReply);
    if (tool && supabase && userId) {
      actionResult = await executeTool(supabase, userId, tool);
    }

    const reply = stripToolLine(rawReply) + (actionResult ? `\n\n${actionResult}` : "");

    return new Response(JSON.stringify({ reply, action: tool?.type || null }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  } catch (e) {
    return new Response(JSON.stringify({ error: String(e) }), {
      status: 500,
      headers: { ...corsHeaders, "Content-Type": "application/json" },
    });
  }
});
