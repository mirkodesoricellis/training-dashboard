/**
 * Training Hub — backend Cloudflare Worker
 *
 * Tre funzioni:
 *  - POST /api/log-meal   → logga un pasto in linguaggio naturale (Nutritionix lo converte in macro, D1 lo salva)
 *  - GET  /api/day        → totali macro loggati per una data + target passato in query, con suggerimento AI per i pasti rimanenti
 *  - POST /api/chat       → risponde a domande libere sull'allenamento (Gemini, con contesto passato dal client)
 *
 * Bindings/secrets attesi (vedi wrangler.toml / `wrangler secret put`):
 *   DB                  — D1 database (binding "DB")
 *   NUTRITIONIX_APP_ID  — secret
 *   NUTRITIONIX_API_KEY — secret
 *   GEMINI_API_KEY      — secret
 *   CORS_ORIGIN         — var, es. "https://mirkodesoricellis.github.io"
 */

function corsHeaders(env) {
  return {
    "Access-Control-Allow-Origin": env.CORS_ORIGIN || "*",
    "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function json(data, env, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...corsHeaders(env) },
  });
}

async function callNutritionix(env, description) {
  const resp = await fetch("https://trackapi.nutritionix.com/v2/natural/nutrients", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-app-id": env.NUTRITIONIX_APP_ID,
      "x-app-key": env.NUTRITIONIX_API_KEY,
      "x-remote-user-id": "0",
    },
    body: JSON.stringify({ query: description }),
  });
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Nutritionix ${resp.status}: ${body.slice(0, 300)}`);
  }
  const data = await resp.json();
  const foods = data.foods || [];
  const totals = foods.reduce(
    (acc, f) => ({
      kcal: acc.kcal + (f.nf_calories || 0),
      protein_g: acc.protein_g + (f.nf_protein || 0),
      carbs_g: acc.carbs_g + (f.nf_total_carbohydrate || 0),
      fat_g: acc.fat_g + (f.nf_total_fat || 0),
    }),
    { kcal: 0, protein_g: 0, carbs_g: 0, fat_g: 0 }
  );
  return { totals, foods };
}

async function callGemini(env, systemInstruction, userText) {
  const model = env.GEMINI_MODEL || "gemini-2.5-flash";
  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${env.GEMINI_API_KEY}`;
  const resp = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      system_instruction: { parts: [{ text: systemInstruction }] },
      contents: [{ role: "user", parts: [{ text: userText }] }],
      generationConfig: { maxOutputTokens: 1024 },
    }),
  });
  if (!resp.ok) {
    const body = await resp.text();
    throw new Error(`Gemini ${resp.status}: ${body.slice(0, 300)}`);
  }
  const data = await resp.json();
  const parts = data?.candidates?.[0]?.content?.parts || [];
  return parts.map((p) => p.text || "").join("").trim();
}

async function handleLogMeal(request, env) {
  const body = await request.json();
  const date = body.date; // "YYYY-MM-DD"
  const description = body.description;
  if (!date || !description) {
    return json({ error: "date e description sono obbligatori" }, env, 400);
  }

  const { totals, foods } = await callNutritionix(env, description);

  await env.DB.prepare(
    `INSERT INTO meals (date, description, kcal, protein_g, carbs_g, fat_g, logged_at)
     VALUES (?, ?, ?, ?, ?, ?, datetime('now'))`
  )
    .bind(date, description, totals.kcal, totals.protein_g, totals.carbs_g, totals.fat_g)
    .run();

  return json({ logged: totals, foods_detected: foods.map((f) => f.food_name) }, env);
}

async function getDayTotals(env, date) {
  const { results } = await env.DB.prepare(
    `SELECT id, description, kcal, protein_g, carbs_g, fat_g, logged_at
     FROM meals WHERE date = ? ORDER BY logged_at ASC`
  )
    .bind(date)
    .all();

  const totals = results.reduce(
    (acc, m) => ({
      kcal: acc.kcal + (m.kcal || 0),
      protein_g: acc.protein_g + (m.protein_g || 0),
      carbs_g: acc.carbs_g + (m.carbs_g || 0),
      fat_g: acc.fat_g + (m.fat_g || 0),
    }),
    { kcal: 0, protein_g: 0, carbs_g: 0, fat_g: 0 }
  );

  return { meals: results, totals };
}

async function handleGetDay(request, env) {
  const url = new URL(request.url);
  const date = url.searchParams.get("date");
  if (!date) return json({ error: "parametro date obbligatorio (YYYY-MM-DD)" }, env, 400);

  const targetKcal = parseFloat(url.searchParams.get("target_kcal") || "0");
  const targetProtein = parseFloat(url.searchParams.get("target_protein_g") || "0");
  const targetCarbs = parseFloat(url.searchParams.get("target_carbs_g") || "0");
  const targetFat = parseFloat(url.searchParams.get("target_fat_g") || "0");

  const { meals, totals } = await getDayTotals(env, date);

  let suggestion = null;
  if (targetKcal > 0) {
    const remaining = {
      kcal: Math.max(0, targetKcal - totals.kcal),
      protein_g: Math.max(0, targetProtein - totals.protein_g),
      carbs_g: Math.max(0, targetCarbs - totals.carbs_g),
      fat_g: Math.max(0, targetFat - totals.fat_g),
    };
    const system = `Sei il nutrizionista di Mirko De Soricellis (Training Hub). Regole alimenti: colazione avena+latte soia+burro arachidi OPPURE latte soia+corn flakes+whey; pranzo riso/pasta a crudo + UNA fonte proteica tra tonno/ceci/lenticchie; spuntino libero pulito; cena UNA proteina tra albume/uova/pollo/burger vegetale Lidl/seitan/tofu/fiocchi latte + UN SOLO carboidrato tra pancarrè/gallette/fette biscottate + verdure. Mai combinare più proteine o più carboidrati nello stesso pasto. Niente miele (usa marmellata). Rispondi in italiano, 2-4 frasi concrete con grammi indicativi, niente markdown pesante.`;
    const userText = `Ha già mangiato oggi: ${totals.kcal.toFixed(0)} kcal, ${totals.protein_g.toFixed(0)}g proteine, ${totals.carbs_g.toFixed(0)}g carbo, ${totals.fat_g.toFixed(0)}g grassi. Gli restano da assumere nei pasti rimanenti della giornata: ${remaining.kcal.toFixed(0)} kcal, ${remaining.protein_g.toFixed(0)}g proteine, ${remaining.carbs_g.toFixed(0)}g carbo, ${remaining.fat_g.toFixed(0)}g grassi. Suggerisci concretamente cosa mangiare nei pasti rimanenti per avvicinarsi al target, rispettando le regole alimentari.`;
    try {
      suggestion = await callGemini(env, system, userText);
    } catch (e) {
      suggestion = null;
    }
  }

  return json({ date, meals, totals, suggestion }, env);
}

async function handleChat(request, env) {
  const body = await request.json();
  const question = body.question;
  const context = body.context || "";
  if (!question) return json({ error: "question obbligatoria" }, env, 400);

  const system = `Sei il coach di allenamento di Mirko De Soricellis (triathlon: corsa, bici, nuoto). Rispondi in italiano in modo diretto e concreto, basandoti SOLO sui dati di contesto forniti (attività, wellness, carico). Se il contesto non contiene abbastanza informazioni per rispondere con certezza, dillo esplicitamente invece di inventare numeri. Risposte brevi (max 5-6 frasi), niente markdown pesante.`;
  const userText = `Contesto (dati recenti allenamento/wellness):\n${context}\n\nDomanda: ${question}`;

  try {
    const answer = await callGemini(env, system, userText);
    return json({ answer }, env);
  } catch (e) {
    return json({ error: String(e) }, env, 502);
  }
}

export default {
  async fetch(request, env) {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders(env) });
    }

    const url = new URL(request.url);
    try {
      if (request.method === "POST" && url.pathname === "/api/log-meal") {
        return await handleLogMeal(request, env);
      }
      if (request.method === "GET" && url.pathname === "/api/day") {
        return await handleGetDay(request, env);
      }
      if (request.method === "POST" && url.pathname === "/api/chat") {
        return await handleChat(request, env);
      }
      return json({ error: "not found" }, env, 404);
    } catch (e) {
      return json({ error: String(e && e.message ? e.message : e) }, env, 500);
    }
  },
};
