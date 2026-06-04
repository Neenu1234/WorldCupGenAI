# WorldCupGenAI — 6 Minute Demo Script

Total runtime: **6:00** (360 seconds)

Three speakers. Assign roles before recording. Slide numbers refer to `WorldCupGenAI_Slides.pptx`.

| Speaker | Owns slides |
|---|---|
| Speaker 1 (intro) | 1, 2, 3 |
| Speaker 2 (technical) | 4, 5, 7 |
| Speaker 3 (demo + close) | 6, 8 |

---

## Slide 1 — Title  (0:00 to 0:15)

**Speaker 1:**

> Hi everyone, we are team Neenu Bonny and this is **WorldCupGPT**, our Track 1 submission. It is a conversational chatbot powered by LangChain that answers questions about World Cup history, looks up team stats, and predicts match outcomes. Let me walk you through what we built.

---

## Slide 2 — The Problem  (0:15 to 0:40)

**Speaker 1:**

> Track 1 asks us to build a chatbot that does three things: answer World Cup history questions, look up team stats, and predict match outcomes. Most teams will solve this with a single RAG chain. We went further. We built a single ReAct agent that can pick between four different tools, plus a memory layer and a polished UI on top.

---

## Slide 3 — Architecture  (0:40 to 1:20)

**Speaker 1:**

> Here is the pipeline. The user types a question. Our ReAct agent reads the tool descriptions and decides which one of four tools to call. The chosen tool returns an answer along with cited evidence and an explicit limitations note. That goes to the Streamlit chat UI, which also shows the agent's live reasoning trace and renders a chart automatically. There are two memory layers running in parallel: conversation history and user preferences. I will hand it over to my teammate to talk about the data.

---

## Slide 4 — Data and Reproducibility  (1:20 to 1:45)

**Speaker 2:**

> We chose the martj42 International Football Results dataset on Kaggle. It has over 49,000 international matches from 1872 to 2026 and is one of the most downloaded football datasets on Kaggle. We filter it down to 964 World Cup matches for the RAG store, and use the full dataset for head to head and recent form features. The dataset is cited in our README, cached locally in the repo so judges can re-run offline, schema-validated on load, and we cross-reference penalty shootouts so titles like Italy 2006 and Argentina 2022 are correctly counted.

---

## Slide 5 — The 4 Tools  (1:45 to 2:25)

**Speaker 2:**

> Our agent has four tools. **WorldCupRAG** does semantic search over the embedded match documents in Chroma. **MatchPredictor** pulls head to head history and recent form for two teams, then asks the LLM for a predicted score. **TeamStats** computes titles, win rate, and top scorers for one team. **MatchGoals** returns the goal by goal breakdown for any historical match. Every tool returns the same shape: an answer plus evidence plus limitations. That is how we cover the grounded reasoning rubric.

---

## Slide 6 — Live Demo  (2:25 to 4:50)  **longest section, 2 minutes 25 seconds**

**Speaker 3:**

> Now I will show it live. I am opening our Streamlit app at localhost 8501.

**[Switch to Streamlit browser tab. Have the chat empty.]**

> Watch two things as I demo: the sidebar on the left, and the agent reasoning panel on the right.

**[Click sidebar button: "Who won the 2014 World Cup final?"]**

> First, a history question. The agent picks the WorldCupRAG tool, retrieves the 12 closest match documents, and answers with the cited evidence right under the response. Germany 1, Argentina 0.

**[Wait for answer to render. Then type in chat input:]**

```
im a brazil and france fan, can i get their history
```

> Now I am declaring two favorite teams in one sentence. Look at the sidebar — both **Brazil and France** are saved as my favorite teams. The agent returns the World Cup history between them, and because I have two favorite teams, our smart chart logic shows a head to head bar chart of Brazil versus France.

**[Wait for response. Then click sidebar button: "How many World Cup titles does Brazil have?"]**

> Next, team stats. Five titles for Brazil, with the years cited, and the limitations note included.

**[Click sidebar button: "Show goals from Germany vs Brazil 2014"]**

> This is our fourth tool — MatchGoals. It looks up every goal scored in that famous 7-1 thrashing and renders a timeline chart with the scorer, the minute, and special markers for penalties and own goals.

**[Click the 🎲 Surprise me button]**

> And finally the Surprise me button, which fires a random query so judges or users can explore without typing anything. That is the full system in five clicks.

---

## Slide 7 — Innovation Beyond Base  (4:50 to 5:30)

**Speaker 2:**

> A quick look at what makes us different. The live agent reasoning panel on the right is an explainability overlay — judges can see exactly which tool the agent picked and why. We auto-render four chart types based on the question intent, with smart triggers so the chart matches the question. We track multiple favorite teams in memory, not just one. We handle penalty shootout finals correctly so titles like Italy 2006 are not missed. And we ship with a polished sidebar of suggested questions plus a Surprise me button.

---

## Slide 8 — Reflections and What's Next  (5:30 to 6:00)

**Speaker 3:**

> Quick reflections. The ReAct agent routed cleanly between four tools, and we learned that tool descriptions are by far the highest-leverage thing to tune. Streamlit plus sidebar buttons made the demo flow effortless. If we had another week, we would add StatsBomb event data for shot maps, multi-team comparisons across three or more teams, and a live API for 2026 fixtures. The biggest lesson: an agent's behavior depends more on what we write — the tool descriptions and the agent prompt — than on the LLM itself. The model is the engine, the prompts are the steering wheel. Our code is on GitHub at github.com/Neenu1234/WorldCupGenAI. Thank you for watching, happy to take questions.

---

## Recording tips

- **Tool:** QuickTime on Mac (Cmd+Shift+5 → Record Selected Portion). Hit record, run the demo, stop.
- **Order:** Slides 1 to 5 first (use slideshow mode), then Slide 6 is your screen recording of Streamlit, then Slides 7 to 8.
- **Practice once:** read the script aloud with a timer. Adjust if you are over 6 minutes.
- **Edit minimally:** if you flub one line, just restart that slide. Don't fix everything in post.
- **Audio:** record in a quiet room. Built-in MacBook mic is fine for a hackathon video.
- **Export:** save as .mov or .mp4. Most submission portals accept both.

## Backup plan if Streamlit crashes during recording

Have the **notebook outputs** as Plan B. Section 6 of the notebook shows the agent answering all 4 query types with the verbose reasoning trace. Worst case, screen-record the notebook in Jupyter instead of Streamlit.
