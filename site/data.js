window.DESLOP_DATA = {
  "rules": [
    {
      "id": "ART-01",
      "tier": "artifact",
      "lang": "en",
      "flags": "im",
      "pattern": "^[ \\t>]*(?:[-*+][ \\t]+|\\d+[.)][ \\t]+)?(?:\\*\\*|__)?(?:(?:Certainly|Sure|Absolutely|Of course)(?:\\*\\*|__)?(?:!|[,.] (?:here(?:['’]s| is)|I['’](?:d|ll)|I can|let me)\\b)|(?:Great|Good) question(?:\\*\\*|__)?[!,.])",
      "note": "Chat reply opener left in the document",
      "doc": "English chat opener (`Certainly!`, `Sure, here's`, `Great question.`), also after a list marker or bold. `Of course, the cache…` in ordinary prose does not match. Delete the opener; start with the first sentence that carries content."
    },
    {
      "id": "ART-02",
      "tier": "artifact",
      "lang": "ja",
      "flags": "m",
      "pattern": "^\\s*(?:もちろんです|承知(?:しました|いたしました)|かしこまりました|素晴らしい(?:ご)?質問)",
      "note": "Chat reply opener left in the document",
      "doc": "Japanese chat opener (`もちろんです`, `承知しました`). Delete it."
    },
    {
      "id": "ART-03",
      "tier": "artifact",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:I hope (?:this|that) helps|happy (?:coding|writing|reading|editing)!|you['’]re absolutely right!|would you like me to\\b|is there anything else (?:I can|you would like))",
      "note": "Chat reply closer addressed to whoever asked",
      "doc": "English chat closer (`I hope this helps`, `Happy coding!`, `You're absolutely right!`, `Would you like me to`, `Is there anything else I can`). Delete. If the document needs a contact route, state the route (`Issues go to the tracker at …`). Follow-up invitations are `EN-20`."
    },
    {
      "id": "ART-04",
      "tier": "artifact",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:参考になれば幸いです|一助と?(?:な|に)れば幸いです|お役に立てれば(?:幸いです|嬉しいです)|いかがでしたか|いかがでしたでしょうか)",
      "note": "Chat reply closer addressed to whoever asked",
      "doc": "Japanese chat closer (`参考になれば幸いです`, `いかがでしたか`). Delete. A real contact route is stated plainly. Invitations to ask are `JA-21`."
    },
    {
      "id": "ART-05",
      "tier": "artifact",
      "lang": "any",
      "flags": "im",
      "pattern": "(?:\\bas an AI(?:(?: language model| model| assistant| chatbot| system)(?: [^.,\\n]{0,40})?| (?:developed|trained|created|built|made) by [^.,\\n]{0,40})?, (?-i:I)\\b|\\bas a large language model\\b|\\bmy (?:knowledge|training) cut-?off\\b|\\b(?:as of|up to) my last (?:knowledge |training )?update\\b|\\bas of my last training\\b|(?:^[ \\t>]*(?:[-*+][ \\t]+|\\d+[.)][ \\t]+)?(?:はい、)?|(?<=。)|私は)[ \\t　]*(?:AI|ＡＩ)(?:アシスタント|言語モデル)?として(?:、|は)|私の(?:知識|学習)の?(?:カットオフ|時点))",
      "note": "The model talking about itself",
      "doc": "The model referring to itself (`As an AI language model, I`, knowledge cutoff such as `as of my last knowledge update`, `AIとして、` opening a sentence). A document about AI products that says a tool runs `as an AI agent`, or an author who writes `As an AI researcher, I`, does not match. Delete the sentence; if it carried a real limit (data current to a date), state the limit as a fact with its date, if the document gives one."
    },
    {
      "id": "ART-06",
      "tier": "artifact",
      "lang": "any",
      "flags": "",
      "pattern": "(?:【\\d+(?:†|:)[^】]*】|\\bturn\\d+(?:search|news|view|fetch|file)\\d+\\b|:?contentReference\\[oaicite:\\d+\\]|\\{index=\\d+\\}|oai_citation|utm_source=(?:chatgpt\\.com|openai|copilot\\.com)|referrer=grok\\.com)",
      "note": "Citation or tracking token from a chat interface",
      "doc": "Citation and tracking tokens from chat interfaces (`【4†source】`, `turn0search1`, `contentReference[oaicite:2]`, `utm_source=chatgpt.com`, `utm_source=openai`, `utm_source=copilot.com`, `referrer=grok.com`). Remove the token; keep the real link without the tracking parameter. A claim whose only source was the token loses its citation: list it under `decisions`."
    },
    {
      "id": "ART-07",
      "tier": "artifact",
      "lang": "any",
      "flags": "i",
      "pattern": "(?:\\b20\\d\\d-[Xx]{2}-[Xx]{2}\\b|\\b(?:INSERT|PASTE)_[A-Z_]*(?:URL|SOURCE)[A-Z_#\\d]*|\\[(?:insert|your|company|name|date|product|author|link|owner|amount|timezone|(?-i:N(?=[\\]\\s])|HH:MM|YYYY-MM-DD))\\b[^\\]\\n]{0,40}\\](?![(\\[:])|(?<![一二三四五六七八九十百千万億〇○])[〇○]{2,}(?![一二三四五六七八九十百千万億])|(?<![一二三四五六七八九十百千万億〇○])[〇○](?=[名件円人個回日月年時分%％](?![時間程次本常]))|[\\[【［](?:ここに|会社名|取引先|担当者|自社名|氏名|お名前|日付|製品名|サービス名|システム名|リンク)[^\\]】］\\n]{0,30}[\\]】］](?![(\\[:]))",
      "note": "Unfilled template placeholder",
      "doc": "Unfilled placeholder (`[Insert company name]`, `【会社名】`, `[取引先会社名]`, `〇〇株式会社`, `〇名`, `○月○日`, `[リンク]`, template fields such as `[HH:MM]`, `[N]`, `[link]`, `[YYYY-MM-DD]`, a date such as `2025-XX-XX`, `INSERT_SOURCE_URL_30`, `PASTE_YOUTUBE_VIDEO_URL_HERE`); a Markdown link such as `[Your first project](tutorial.md)` or `[リンク](…)` does not match, nor does a `[label]` that a valid reference definition in the document resolves, `[N/A]`, the zero in a kanji numeral (`二〇二〇年`, `一〇〇円`) or a `○` used as a bullet (`○日時`). In a document meant to be filled in by its user (a postmortem template, a mail draft with `[担当者名]`), give it the `template` genre, which exempts this rule and no other artifact rule. Never fill it with an invented value: list it under `decisions` and leave a visible marker only if the requester wants the draft to keep it. Remove only the marker and the words that depend on it (`〇名規模のチームで` → `チームで`); the sentence and its claim stay. Examples inside code, front matter or HTML blocks do not define references. A valid definition may wrap onto the next line or sit in a list or quote. An escaped `\\[Your Name]` remains a literal placeholder rather than a link."
    },
    {
      "id": "ART-08",
      "tier": "artifact",
      "lang": "en",
      "flags": "im",
      "pattern": "(?:^|(?<=[.!?] ))[ \\t]*(?:Here(?:['’]s| is) (?:a|an|the|your) (?:revised|improved|updated|rewritten|polished|draft|summary|breakdown|overview)\\b|Below is (?:a|an|the) (?:revised|improved|updated|rewritten|draft|summary)\\b)",
      "note": "Framing of a chat response rather than the document itself",
      "doc": "English response framing (`Here's a revised version`, `Below is the summary`). Delete; the document is the content, not a reply about it."
    },
    {
      "id": "ART-09",
      "tier": "artifact",
      "lang": "ja",
      "flags": "m",
      "pattern": "^\\s*(?:以下(?:は|に)、?[^。\\n]{0,20}(?:まとめ(?:ました|ます|たもの)|(?:作成|提案|修正|改善|改訂)(?:しました|します|したもの))|こちらが[^。\\n]{0,15}(?:です|になります)。)",
      "note": "Framing of a chat response rather than the document itself",
      "doc": "Japanese response framing (`以下に〜をまとめました`, `こちらが〜です。`). Delete."
    },
    {
      "id": "EN-01",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:delv(?:e|es|ed|ing)|showcas(?:e|es|ed|ing)|garner(?:s|ed|ing)?|bolster(?:s|ed|ing)?|boasts)\\b",
      "note": "Verb with a large excess frequency in LLM-era text",
      "doc": "Verbs whose frequency jumped after chat models arrived: `delve`, `showcase`, `garner`, `bolster`, `boasts` (for \"has\"). Use the verb for what actually happens (`covers`, `shows`, `gets`, `has`), or cut the sentence that announces the topic."
    },
    {
      "id": "EN-02",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:tapestry|a testament to|in the realm of|interplay|intricacies|cornerstone|beacon of|the (?:ever-(?:evolving|changing) )?landscape of)\\b",
      "note": "Ornamental metaphor standing in for a concrete subject",
      "doc": "Ornamental nouns: `tapestry`, `a testament to`, `in the realm of`, `the landscape of`, `interplay`, `intricacies`, `cornerstone`, `beacon of`. Name the subject directly (`in databases`, not `in the realm of databases`)."
    },
    {
      "id": "EN-03",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:leverag(?:e|es|ed|ing)|harness(?:es|ed|ing)? the|unlock(?:s|ed|ing)? (?:the |your |its )?(?:full )?(?:power|potential)|empower(?:s|ed|ing)?|elevat(?:e|es|ed|ing)|streamlin(?:e|es|ed|ing)|foster(?:s|ed|ing)?|supercharg(?:e|es|ed|ing))\\b",
      "note": "Inflated verb where a plain one says the same",
      "doc": "Inflated verbs: `leverage`, `harness`, `unlock the power`, `empower`, `elevate`, `streamline`, `foster`, `supercharge`. Say `use`, `let`, `make faster`, or what concretely changes; often the sentence can go."
    },
    {
      "id": "EN-04",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:seamless(?:ly)?|robust|cutting-edge|state-of-the-art|game[- ]chang(?:er|ing)|groundbreaking|revolutioni[sz](?:e|es|ed|ing)|transformative|innovative|holistic|synerg(?:y|ies|istic)|paradigm shift)\\b",
      "note": "Promotional adjective with no measurable content",
      "doc": "Promotional adjectives: `seamless`, `robust`, `cutting-edge`, `innovative`, `holistic`, `game-changing`. Replace with the property and its evidence from the document (`retries three times`, `no restart needed`) or delete. Exempt established terms (`robust statistics`, `robust regression`)."
    },
    {
      "id": "EN-05",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:plays? (?:a|an) (?:crucial|pivotal|vital|key|significant|important) role|(?:is|are) (?:crucial|pivotal|paramount|vital)\\b|of paramount importance|\\ba pivotal role\\b)",
      "note": "Importance asserted instead of shown",
      "doc": "Importance asserted: `plays a crucial role`, `is pivotal`, `of paramount importance`. Show why it matters, with the document's own consequence, or state the fact without the rating."
    },
    {
      "id": "EN-06",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "(?:\\bit(?:['’]s| is) (?:important|worth|crucial|essential) (?:to note|noting|to remember|to mention|to understand)|\\bit should be noted\\b|\\bnotably,|\\bimportantly,)",
      "note": "Throat-clearing before the actual point",
      "doc": "Throat-clearing: `It's important to note`, `It's worth noting`, `Notably,`. Delete the frame; keep the note."
    },
    {
      "id": "EN-07",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:in today['’]s (?:[\\w-]+ ){0,2}(?:world|age|landscape|era|environment)|in the (?:digital|modern) age|in an era (?:of|where))\\b",
      "note": "Generic scene-setting opener",
      "doc": "Scene-setting openers: `In today's fast-paced world`, `in the digital age`. Delete; begin with the document's subject."
    },
    {
      "id": "EN-08",
      "tier": "lexical",
      "lang": "en",
      "flags": "im",
      "pattern": "(?:^[ \\t>]*(?:[-*+][ \\t]+|\\d+[.)][ \\t]+)?(?:\\*\\*|__)?|(?<=[.!?] )(?<!\\be\\.g\\. )(?<!\\bi\\.e\\. ))(?:In conclusion|In summary|To sum up|To summarize|Overall|Ultimately|All in all)(?:\\*\\*|__)?[,.]",
      "note": "Formulaic wrap-up that restates the body",
      "doc": "Formulaic wrap-up: `In conclusion`, `In summary`, `Overall`, `Ultimately` at the start of a sentence. Delete the paragraph if it restates the body; keep only a new consequence or next step."
    },
    {
      "id": "EN-09",
      "tier": "lexical",
      "lang": "en",
      "flags": "im",
      "pattern": "(?:^[ \\t>]*(?:[-*+][ \\t]+|\\d+[.)][ \\t]+)?(?:\\*\\*|__)?|(?<=[.!?] ))(?:Moreover|Furthermore|Additionally)(?:\\*\\*|__)?[,]",
      "note": "Essay connective stacking paragraphs mechanically",
      "doc": "Connective stacking: `Moreover,`, `Furthermore,`, `Additionally,`. Usually delete; the order of sentences already says \"and\". Use `but`, `so`, `because` when the relation is real."
    },
    {
      "id": "EN-10",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "(?:\\b(?:is|are)(?: not|n['’]t) (?:just|merely)\\b|\\b(?:it|this|that)['’]s not (?:just|merely)\\b|\\b(?:is|are)(?: not|n['’]t) only (?:a|an|about)\\b|\\bnot only\\b[^.\\n]{1,80}\\bbut also\\b|\\bit['’]s not (?:about )?[^.;:—\\n]{1,40}(?:—|--|;|,|\\.) it['’]s\\b|\\bmore than just\\b)",
      "note": "Reflexive 'not X but Y' contrast",
      "doc": "Reflexive contrast: `isn't just X, it's Y`, `It's not X — it's Y`, `It's not about X; it's about Y`, `more than just`, `is not merely`, `not only … but also`. State Y. Keep a contrast only when someone actually believes X."
    },
    {
      "id": "EN-11",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:embark(?:s|ed|ing)? on|(?:a|your|the|this) journey (?:of|to|through|into)|navigat(?:e|es|ed|ing) the (?:complexities|challenges|intricacies|world|landscape))\\b",
      "note": "Journey metaphor for an ordinary task",
      "doc": "Journey metaphors: `embark on`, `a journey of`, `navigate the complexities`. Name the task (`set up`, `migrate`, `handle`)."
    },
    {
      "id": "EN-12",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:let['’]s (?:dive|delve|explore|unpack|break (?:this|it) down|take a (?:closer|deep) look)|dive (?:deep(?:er)? )?into|deep dive)\\b",
      "note": "Signposted dive instead of starting",
      "doc": "Signposted dives: `Let's dive into`, `deep dive`, `Let's explore`, `Let's break this down`. Delete and start the explanation."
    },
    {
      "id": "EN-13",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:underscor(?:e|es|ed|ing)|highlight(?:s|ed|ing)? the importance|serves as a (?:reminder|testament)|stands as a)\\b",
      "note": "Significance verb that adds no information",
      "doc": "Significance verbs: `underscores`, `highlights the importance`, `serves as a reminder`, `stands as`. State the fact the significance rested on."
    },
    {
      "id": "EN-14",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:intricate|meticulous(?:ly)?|nuanced|multifaceted|comprehensive|(?<!is )(?<!are )pivotal(?! role)|myriad|plethora|a wide (?:range|array|variety) of|vibrant|bustling|ever-evolving)\\b",
      "note": "Intensifier adjective standing in for detail",
      "doc": "Intensifiers standing in for detail: `intricate`, `meticulous`, `nuanced`, `comprehensive`, `a wide range of`, `myriad`, `vibrant`, `pivotal` before a noun (`a pivotal moment`; `is pivotal` and `a pivotal role` are `EN-05`). Give the detail or the count, or delete the adjective."
    },
    {
      "id": "EN-15",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\bwhether you(?:['’]re| are) (?:a|an|new|just|looking)\\b[^.\\n]{0,60}\\bor\\b",
      "note": "Audience-widening 'whether you're X or Y'",
      "doc": "Audience widening: `whether you're a beginner or an expert`. Name the actual reader once, near the top, or delete."
    },
    {
      "id": "EN-16",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:can potentially|could potentially|may potentially|might possibly|generally speaking|in many ways|to some extent|arguably)\\b",
      "note": "Stacked hedge",
      "doc": "Stacked hedges: `can potentially`, `might possibly`, `arguably`, `to some extent`. One hedge where uncertainty is real, with its condition; none where the document knows."
    },
    {
      "id": "EN-17",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:we['’]re (?:excited|thrilled)|thrilled to|look no further|take (?:your|it) to the next level|next level)\\b",
      "note": "Marketing enthusiasm",
      "doc": "Marketing enthusiasm: `we're excited`, `look no further`, `next level`. Delete; describe the change."
    },
    {
      "id": "EN-18",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "(?:\\bhere['’]s the (?:thing|kicker|catch)\\b|\\bthe (?:result|answer|catch|kicker|best part)\\?|\\blet that sink in\\b|\\bimagine a world where\\b)",
      "note": "Staged reveal",
      "doc": "Staged reveal: `Here's the thing`, `The result?`, `Let that sink in`, `Imagine a world where`. Write the statement directly."
    },
    {
      "id": "EN-19",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:key takeaways?|final thoughts|wrapping up)\\b",
      "note": "Template section name",
      "doc": "Template section names: `Key takeaways`, `Final thoughts`, `Wrapping up`. Remove the section if it repeats the body; otherwise give it a heading that names its content."
    },
    {
      "id": "EN-20",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:let me know if you (?:have any|need|want|would like)|feel free to (?:ask|reach out))",
      "note": "Invitation to follow up, legitimate only in a message to a person",
      "doc": "Follow-up invitation (`Let me know if you have any questions`, `Feel free to reach out`). Delete it from documents. In an email or message to a person it is the genre's convention, and the `message` genre exempts it."
    },
    {
      "id": "EN-21",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": ",\\s+(?:highlighting|emphasizing|reflecting|symbolizing|showcasing|cementing|solidifying|contributing to) (?:its|their|the|a|an|his|her|this)\\b",
      "note": "Trailing -ing clause that assigns significance",
      "doc": "A trailing `-ing` clause that assigns significance (`, highlighting its importance`, `, reflecting the broader trend`, `, contributing to the`). It claims a meaning the sentence has not shown. Cut the clause; if the consequence is real and in the document, state it as its own sentence."
    },
    {
      "id": "EN-22",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:serv(?:es|ed|ing)|stand(?:s|ing)) as (?:a|an|the)\\b(?! (?:reminder|testament)\\b)",
      "note": "'serves as' where 'is' says the same",
      "doc": "`serves as a`, `stands as the` where `is` says the same (`The file serves as the entry point` → `The file is the entry point`). Keep it when the thing really does stand in for something else (`a stub serves as the server in tests`), and exempt that occurrence."
    },
    {
      "id": "EN-23",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:key turning point|watershed moment|indelible mark|deeply rooted|enduring legacy|lasting (?:impact|legacy)|setting the stage for|evolving landscape|focal point|rich (?:cultural )?heritage|nestled (?:in|among|within)|in the heart of|breathtaking|must-visit)\\b",
      "note": "Legacy and travel-brochure puffery",
      "doc": "Legacy and brochure puffery: `key turning point`, `watershed moment`, `indelible mark`, `deeply rooted`, `lasting impact`, `setting the stage for`, `evolving landscape`, `rich cultural heritage`, `nestled in`, `in the heart of`, `breathtaking`. Replace with the fact behind it (a date, a number, what changed) or cut it."
    },
    {
      "id": "EN-24",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:experts (?:agree|argue|say|believe|suggest)|industry reports (?:suggest|show|indicate)|observers have (?:noted|cited)|some critics (?:argue|say)|(?:studies|research) (?:shows?|has shown|have shown|suggests?|indicates?) that)\\b",
      "note": "Attribution to unnamed experts or studies",
      "doc": "Unnamed authority: `experts agree`, `industry reports suggest`, `observers have noted`, `some critics argue`, `studies show that`. Name the source the document cites; if it cites none, cut the attribution and keep the claim only if the document supports it, listing the missing source under `decisions`."
    },
    {
      "id": "EN-25",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:while (?:specific )?details (?:are|remain) (?:limited|scarce)|(?:is|are)(?: not|n['’]t) (?:widely|extensively) (?:available|documented|disclosed)|based on (?:the )?available information|in the (?:provided|available) (?:sources|search results)|maintains a low profile)\\b",
      "note": "Disclaimer about the model's own sources",
      "doc": "Disclaimers about the model's own sources: `while specific details are limited`, `is not widely documented`, `based on available information`, `in the provided sources`. They describe the chat session, not the subject. Delete; a real gap in the record is stated plainly (`the release date is not published`). A disclaimer that the document's own specifics were not verified or were invented (`the options below are assumed`) is such a gap: never delete it alone, or invented values read as fact. Restate it as a plain sentence in the document and list it under `decisions` (CON-03). A statement of what kind of document it is (`this page is an example spec`) is part of that limit and stays."
    },
    {
      "id": "EN-26",
      "tier": "lexical",
      "lang": "en",
      "flags": "im",
      "pattern": "(?:\\bdespite (?:these|its|their|the|such) challenges\\b|^#{1,6}\\s*(?:challenges and (?:legacy|future (?:prospects|directions|outlook))|future (?:outlook|prospects))\\s*$)",
      "note": "'Despite challenges' and 'future outlook' closing formula",
      "doc": "The closing formula `Despite these challenges, …` and headings such as `Challenges and Future Prospects` or `Future Outlook`. Keep a limitation or a plan the document actually has, under a heading named for it; cut the optimistic wrap-up."
    },
    {
      "id": "EN-27",
      "tier": "lexical",
      "lang": "en",
      "flags": "i",
      "pattern": "\\b(?:imagine (?:you(?:['’]re| are)\\b|that you\\b|a (?:scenario|developer|team|company|user)\\b)|picture this\\b|let['’]s say you\\b|consider (?:a|the following) (?:scenario|hypothetical)\\b)",
      "note": "Invented scenario standing in for a real example",
      "doc": "Invented scenario in place of a real example: `Imagine you're a developer who…`, `Picture this`, `Let's say you`, `Consider the following scenario`. Use an example the document actually has, or drop the scenario and state the point (CON-04)."
    },
    {
      "id": "JA-01",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:と言える(?:でしょう|かもしれません)|ではないでしょうか|と言えるのではない)",
      "note": "結論をぼかす文末",
      "doc": "結論をぼかす文末（`〜と言えるでしょう`、`〜ではないでしょうか`）。根拠がある なら言い切る。根拠がないなら条件を書くか、その文を削る。"
    },
    {
      "id": "JA-02",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "と言っても過言では(?:ありません|ない)",
      "note": "誇張の定型句",
      "doc": "`〜と言っても過言ではありません`。誇張を外して事実だけを書く。多くは削除で足りる。"
    },
    {
      "id": "JA-03",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:が(?:重要|不可欠|鍵|カギ|肝要)(?:です|となります|になります|と言えます)|重要なポイント|重要な役割を果たし|鍵を握)",
      "note": "重要さを示さずに宣言する",
      "doc": "重要さの宣言（`〜が重要です`、`重要な役割を果たします`、`鍵となります`）。 なぜ重要かを文書内の帰結で示すか、評価語を外して事実だけ残す。"
    },
    {
      "id": "JA-04",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "することが(?:でき(?:ます|る|ません|ない)|可能(?:です|だ|で|と|に|な))",
      "note": "「〜できる」で足りる冗長形",
      "doc": "`〜することができます`。`〜できます` にする。主語と動詞がはっきりするなら `〜します` で足りることも多い。"
    },
    {
      "id": "JA-05",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:という点において|という観点(?:から|において)|の観点から見ると)",
      "note": "翻訳調の前置き",
      "doc": "翻訳調の前置き（`〜という点において`、`〜という観点から`）。前置きを外し、 何についての文かを主語で示す。"
    },
    {
      "id": "JA-06",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:シームレス(?:に|な)|包括的(?:に|な)|革新的(?:な|に)|画期的(?:な|に)|ゲームチェンジャー|パラダイムシフト|新たな可能性|可能性を(?:広げ|最大限)|最大限に(?:活用|引き出)|次のレベル|飛躍的(?:に|な)|多岐にわたる|強力な|直感的(?:に|な)|堅牢な)",
      "note": "中身のない宣伝語",
      "doc": "中身のない宣伝語（`シームレス`、`包括的`、`革新的`、`新たな可能性`、 `最大限に引き出す`、`飛躍的に`、`強力な`、`直感的な`、`堅牢な`）。測れる性質と文書内の根拠に置き換えるか削る。"
    },
    {
      "id": "JA-07",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "ことで、?[^。\\n]{0,40}(?:が可能(?:に|と)な(?:り|る)|を実現(?:し|する|でき)|が実現(?:し|され|でき))",
      "note": "「〜することで〜が可能になります」型の抽象的な効能文",
      "doc": "`〜することで、〜が可能になります` 型の効能文。何をすると何が起きるかを具体的に 書く（`ヒットした要求はディスクを読まない`）。"
    },
    {
      "id": "JA-08",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:本記事では|この記事では|本稿では|本ドキュメントでは|このドキュメントでは)[^。\\n]{0,60}(?:解説|紹介|説明|まとめ)(?:します|していきます|しています)",
      "note": "これから書く内容の予告",
      "doc": "内容の予告（`本記事では〜を解説します`）。削除して本題から始める。"
    },
    {
      "id": "JA-09",
      "tier": "lexical",
      "lang": "ja",
      "flags": "m",
      "pattern": "(?:^#{1,6}\\s*(?:まとめ|結論|おわりに|終わりに)\\s*$|^[ \\t　]*以上、[^。\\n]{0,60}(?:解説|紹介|説明|まとめ)(?:しました|してきました)|(?:まとめると|結論として|要約すると|総じて)、)",
      "note": "本文を繰り返すだけの締め",
      "doc": "本文の繰り返しで終わる締め（`## まとめ`、`まとめると、`、`総じて、`、 `以上、〜について解説しました`）。本文を 繰り返すだけなら節ごと削る。新しい結論や次の手順だけを残す。"
    },
    {
      "id": "JA-10",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:してみてはいかがでしょうか|してみましょう|ぜひ[^。\\n]{0,20}(?:ください|てみて|お試し))",
      "note": "読者への勧誘",
      "doc": "読者への勧誘（`〜してみてはいかがでしょうか`、`ぜひ〜ください`）。手順なら命令形や `〜します` で書き、勧誘は削る。勧誘の形でも、記事が何に着目するかを伝えている文 （`〜に注目してみましょう`）は削らず、着眼点を平叙文で書く。"
    },
    {
      "id": "JA-11",
      "tier": "lexical",
      "lang": "ja",
      "flags": "m",
      "pattern": "(?:^|(?<=。))[ \\t　]*(?:つまり|言い換えれば|言い換えると|すなわち)、",
      "note": "直前の文の言い直し",
      "doc": "言い直し（`つまり、`、`言い換えると、`）。前の文が分かりにくいならそちらを直し、 言い直しの文を削る。"
    },
    {
      "id": "JA-12",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:単なる[^。\\n]{1,20}ではなく|だけでなく[^。\\n]{1,30}も|のみならず)",
      "note": "反射的な「AではなくB」対比",
      "doc": "反射的な対比（`単なる〜ではなく`、`〜だけでなく〜も`）。主張したい側だけを書く。"
    },
    {
      "id": "JA-13",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:が挙げられます|として挙げられ|などが挙げられ|[0-9０-９一二三四五]つの(?:理由|ポイント|メリット|方法|コツ|ステップ)があります|まず(?:1|１|一)つ目は)",
      "note": "列挙の定型句",
      "doc": "列挙の定型句（`〜が挙げられます`、`〜には3つの理由があります`、`まず1つ目は`）。`〜は次の2つです` のように数と中身を直接書くか、 文に溶かす。"
    },
    {
      "id": "JA-14",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:深掘り|紐解(?:く|い|き)|探求(?:し|する)|旅に出|への旅|世界へようこそ|魅力に迫|徹底解説|完全ガイド)",
      "note": "冒険・探求の比喩",
      "doc": "探求・冒険の比喩（`深掘り`、`紐解く`、`〜への旅`、`徹底解説`、`完全ガイド`）。 何をするのかをそのまま書く。"
    },
    {
      "id": "JA-15",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:寄り添(?:う|い)|心を込め|一人ひとりに合わせ|あなたの[^。\\n]{0,10}(?:可能性|未来|ビジネス))",
      "note": "情緒的な宣伝語",
      "doc": "情緒的な宣伝語（`寄り添う`、`一人ひとりに合わせた`、`あなたの未来`）。具体的な 機能や条件に置き換えるか削る。"
    },
    {
      "id": "JA-16",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:ことが期待されます|と期待されています|注目を集めています|注目されています|今後ますます)",
      "note": "出典のない動向の断定",
      "doc": "出典のない動向（`〜が期待されます`、`注目を集めています`、`今後ますます`）。 出典があればそれを示し、なければ削る。"
    },
    {
      "id": "JA-17",
      "tier": "lexical",
      "lang": "ja",
      "flags": "m",
      "pattern": "^#{1,6}\\s*[^\\n]{0,40}(?:とは[？?]|のメリット|のポイント|のコツ)[^\\n]*$",
      "note": "SEO記事型の見出し",
      "doc": "SEO記事型の見出し（`〜とは？`、`〜のメリット`、`〜のポイント`）。節の中身を 名詞句で名付ける（`## 設定項目`）。中身が薄ければ見出しごと前後の節に統合する。"
    },
    {
      "id": "JA-18",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:(?:様々な|さまざまな|多様な|幅広い)[^。、\\n]{0,10}(?:ニーズ|場面|分野|課題|用途|シーン))",
      "note": "具体例の代わりの「さまざまな〜」",
      "doc": "具体例の代わりの「さまざまな〜」（`さまざまな用途`、`幅広いニーズ`）。文書にある 用途を挙げるか削る。"
    },
    {
      "id": "JA-19",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:となっております|(?<!お世話)になっております)",
      "note": "過剰な丁寧表現",
      "doc": "過剰な丁寧表現（`〜となっております`）。`〜です` にする。ビジネスメールの 挨拶 `お世話になっております` は定型句なので当たらない。"
    },
    {
      "id": "JA-20",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:——|―{2,}|—{1,2}(?=[\\u3040-\\u30ff\\u4e00-\\u9fff]))",
      "note": "和文中のダッシュ挿入",
      "doc": "和文中のダッシュ（`——`）。読点、括弧、または文を分けて書く。"
    },
    {
      "id": "JA-21",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:ご不明な点(?:が|や[^。\\n]{0,12}が)(?:あれば|ございましたら)|お気軽に(?:お尋ね|ご質問|お問い合わせ|ご相談|お申し付け|ご連絡))",
      "note": "問い合わせへの誘い。人宛てのメールやメッセージでのみ正当",
      "doc": "問い合わせへの誘い（`ご不明な点があれば`、`ご不明な点がございましたら`、 `お気軽にご質問ください`、`お気軽にお申し付けください`）。文書からは削除し、 窓口が必要なら窓口そのものを書く。人宛てのメールやメッセージでは慣習なので、 `message` ジャンルが除外する。メールの下書きを `template` で扱うときは、 `message` の慣習として手で除外する。"
    },
    {
      "id": "JA-22",
      "tier": "lexical",
      "lang": "ja",
      "flags": "m",
      "pattern": "(?:^[ \\t>]*(?:[-*+][ \\t]+|\\d+[.)][ \\t]+)?(?:\\*\\*|__)?|(?<=。))[ \\t　]*(?:さらに|加えて|このように)(?:\\*\\*|__)?、",
      "note": "段落を機械的につなぐ接続詞",
      "doc": "文頭の `さらに、`、`加えて、`、`このように、`。段落を順に積むだけの接続詞は削る。 `このように、` で始まる文が前の段落の言い直しなら文ごと削る（STR-03）。前の文と 本当に論理関係があるなら、その関係（理由、条件、対比）が分かる書き方にする。"
    },
    {
      "id": "JA-23",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:見ていきましょう|見ていきます|(?:詳しく|わかりやすく|分かりやすく|徹底的に)(?:解説|説明|紹介)(?:します|していきます)|それでは、?(?:さっそく|早速))",
      "note": "本題の前の道案内",
      "doc": "本題の前の道案内（`見ていきましょう`、`詳しく解説します`、`それでは早速`）。 削除して本題から始める。手順の導入なら何をするかだけを書く。"
    },
    {
      "id": "JA-24",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "を可能に(?:する|し(?:ます|ました|ています|た|て))",
      "note": "「XはYを可能にする」型の翻訳調",
      "doc": "`XはYを可能にします`。英語の \"X enables Y\" の直訳。`Xを使うとYできます`、 `XでYします` のように、誰が何をするかを動詞で書く。"
    },
    {
      "id": "JA-25",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:(?:可能性が|場合が|場合も|ことも)あるかもしれ|と(?:考えられる|思われる)かもしれ|かもしれない可能性)",
      "note": "重ねたぼかし",
      "doc": "重ねたぼかし（`可能性があるかもしれません`、`場合もあるかもしれません`）。 ぼかしは一つで足りる。条件が分かっているなら条件を書いて言い切る。"
    },
    {
      "id": "JA-26",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:(?:と|って)(?:思った|感じた|悩んだ|困った)こと(?:は|が)ありませんか|(?:お悩み|お困り)ではありませんか|(?:お悩み|お困り)の方(?:も)?(?:多い|いる)(?:の)?では)",
      "note": "読者の悩みを想定する問いかけ",
      "doc": "読者の悩みを想定する問いかけ（`〜と思ったことはありませんか`、 `〜でお困りではありませんか`）。記事冒頭の定型なので削り、対象読者が必要なら `〜する人向けです` と一文で書く。"
    },
    {
      "id": "JA-27",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "[^、。！？\\s]{1,15}、[^、。！？\\s]{1,15}、そして[^、。！？\\s]{1,15}",
      "note": "英語の \"A, B, and C\" を写した列挙",
      "doc": "`A、B、そしてC`。英語の \"A, B, and C\" を写した列挙で、日本語では最後の項目の前に `そして` を置かない。`A、B、C` か `AとBとC` にする。動作を順に並べる文 （`起動し、設定を読み、そして待機する`）は対象外なので、そう書いて除外する。"
    },
    {
      "id": "JA-28",
      "tier": "lexical",
      "lang": "ja",
      "flags": "m",
      "pattern": "(?:(?:^|(?<=。))[ \\t　]*(?:大切|大事|重要|肝心)なのは、?|への(?:鍵|近道|第一歩)(?:です|となります|になります|だ))",
      "note": "名言風の締め",
      "doc": "名言風の締め（`大切なのは〜です`、`〜が成功への鍵です`、`〜への第一歩`）。 中身のない教訓なら削る。具体的な行動を指しているなら、その行動を手順として書く。"
    },
    {
      "id": "JA-29",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:一概に(?:は)?言え(?:ません|ない)|メリットもデメリットも|メリットとデメリットの両方|(?:自分|ご自身)に合った[^。\\n]{0,10}を選(?:び|ぶ|んで))",
      "note": "結論を避ける両論併記",
      "doc": "結論を避ける両論併記（`一概には言えません`、`メリットもデメリットもあります`、 `自分に合った方法を選びましょう`）。文書が判断の材料を持っているなら、どの条件で どちらを選ぶかを書く。持っていないなら削る。"
    },
    {
      "id": "JA-30",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:(?<=[\\u3040-\\u30ff\\u4e00-\\u9fff])[“”]|[“”](?=[\\u3040-\\u30ff\\u4e00-\\u9fff]))",
      "note": "和文中の欧文引用符",
      "doc": "和文中の欧文引用符（`“設定”`）。和文では `「」` を使う。英文の引用や UI の文言を そのまま示す場合は除外する。"
    },
    {
      "id": "JA-31",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:と言われています|と言われている|とされています|(?:専門家|研究|調査|データ)によると|多くの(?:企業|人|方|ユーザー|開発者|専門家)が)",
      "note": "出典を示さない伝聞や多数派への言及",
      "doc": "出典を示さない伝聞と多数派への言及（`〜と言われています`、`〜とされています`、 `調査によると`、`多くの企業が`）。文書が出典を挙げているならそれを名指しする。 挙げていないなら伝聞の枠を外し、文書が裏づける部分だけを残す（CON-08）。"
    },
    {
      "id": "JA-32",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:想像してみてください|想像してみましょう|例えば、?あなたが|[A-ZＡ-Ｚ]さん(?:（仮名）|\\(仮名\\))|とある(?:企業|会社|ユーザー|開発者))",
      "note": "実例の代わりの架空の場面",
      "doc": "実例の代わりの架空の場面（`想像してみてください`、`例えば、あなたが`、 `Aさん（仮名）`、`とある企業`）。文書に実例があればそれを使い、なければ場面を削って 言いたいことを直接書く（CON-04）。"
    },
    {
      "id": "JA-33",
      "tier": "lexical",
      "lang": "ja",
      "flags": "",
      "pattern": "(?:(?:仕様|実装|ソース|ドキュメント)(?:は|を|が)?[^。\\n]{0,8}(?:確認できて(?:いない|いません|おらず)|未提示)|(?:フィールド|動作|仕様|値|内容)(?:と[^。\\n]{0,10})?を仮定して|仮の(?:内容|値|仕様)|仕様例です|一般的な[^。\\n]{0,20}を参考に(?:した|しています|して))",
      "note": "生成モデル自身の断り書き（未確認・仮定・参考にした一般例）",
      "doc": "生成モデル自身の断り書き（`実際の仕様は確認できていません`、`以下のフィールドと 動作を仮定しています`、`一般的な〜を参考にした仮の内容です`、`仕様例です`）。 依頼者に向けた口調は消すが、断り書きそのものは消さない。`本ページは仕様例です。` のように文書の種類を述べる一文も、その限界の一部なので残す。内容が未確認・仮定で あることは文書の本当の限界で、消すと作られた値が確定した仕様に読める。 `以下のオプションと終了コードは未確認の仮案です。` のように平叙文で本文に残し、 `decisions` に挙げる（CON-03）。平叙文がなおこのルールに当たるときは、その理由で 除外する。"
    },
    {
      "id": "EMO-01",
      "tier": "lexical",
      "lang": "any",
      "flags": "",
      "pattern": "[\\U0001F300-\\U0001FAFF\\u2705\\u274C\\u274E\\u2728\\u2B50\\u26A1\\u2757\\u2753\\u231A\\u231B\\u23E9-\\u23FA]",
      "note": "Decorative emoji in prose or headings",
      "doc": "飾りの絵文字（見出しや箇条書きの頭の 🚀 ✅ ✨ ⏱）。削除する。UI の文言を そのまま引用している場合、比較表のセルで対応の有無を示す ✅ / ❌、状況欄で 進捗を示す信号色 🟢 🟡 🔴 だけ除外できる（`text` にその記号を指定する）。 信号色を外すなら、同じ欄の文字の状態表記（On track など）を必ず残す。表の勝ち負けを飾る 🏆 😱 は 削除する。"
    },
    {
      "id": "CNT-01",
      "tier": "content",
      "lang": "any",
      "check": "unsourced_stat",
      "note": "Figure stated as a claim with nothing cited in its paragraph",
      "doc": "A percentage or multiplier (`30%`, `2倍`, `3割`) stated as a claim: its sentence names a population (`企業`, `users`), a change (`向上`, `削減`, `faster`) or an approximation (`約` before an amount, `程度`, `about`), and its paragraph has no link, footnote, named source, stated assumption (`仮定`, `estimate`) or measurement (`63 → 27 ms`). Table rows and ranges such as `15-30%`, `15 - 30%` and `15% - 30%` are not checked. A source in a different Markdown block, such as the next list item or a section after a heading, does not support the claim's paragraph. Generated drafts invent such figures. Do not look for a source and do not change the number: if it is decoration, delete the sentence and record the value in `preservation`; if the document depends on it, keep it and list it under `decisions` as needing a source, then exempt the hit with that reason. A figure measured in the document itself (a benchmark table, a log) is exempted with that named (CON-03)."
    },
    {
      "id": "DEN-01",
      "tier": "density",
      "lang": "any",
      "metric": "bold_per_1000",
      "max": 3.0,
      "note": "Too much bold: emphasis on everything is emphasis on nothing",
      "doc": "Bold spans per 1,000 prose characters above 3. Keep bold for the one term a reader must not miss per section, or for UI labels; remove the rest."
    },
    {
      "id": "DEN-02",
      "tier": "density",
      "lang": "en",
      "metric": "dash_per_1000",
      "max": 1.5,
      "note": "Em-dash habit",
      "doc": "Em dashes per 1,000 characters above 1.5 (English). Use commas, parentheses, a colon, or two sentences."
    },
    {
      "id": "DEN-03",
      "tier": "density",
      "lang": "any",
      "metric": "exclaim_ratio",
      "max": 0.05,
      "note": "Exclamation marks in expository text",
      "doc": "Over 5% of sentences end in `!`. Expository text states; remove them."
    },
    {
      "id": "DEN-04",
      "tier": "density",
      "lang": "any",
      "metric": "boldlead_items",
      "max": 2,
      "note": "Bullet lists of '**Label**: explanation'",
      "doc": "Three or more `**Label**: explanation` or `**Label:** explanation` bullets. Write the items as prose, or as a plain list or table when the reader scans them (the `reference` genre exempts it). A block of short field labels with values (`日時`, `場所`, `Owner`, `Due`, `Status`) is a form the reader fills in or scans, not prose cut into pieces: keep its bold and exempt the hit naming the block (the `template` genre exempts it)."
    },
    {
      "id": "DEN-05",
      "tier": "density",
      "lang": "any",
      "metric": "heading_per_1000",
      "max": 5.0,
      "min_chars": 1500,
      "note": "A heading for every few sentences",
      "doc": "More than 5 headings per 1,000 prose characters, checked from 1,500 characters of prose: below that a title and a few sections decide the rate. Merge thin sections; keep a heading only where a reader would navigate to it."
    },
    {
      "id": "DEN-06",
      "tier": "density",
      "lang": "any",
      "metric": "list_ratio",
      "max": 0.6,
      "min_chars": 1500,
      "note": "Most of the document is bullets",
      "doc": "More than 60% of body lines are list items (10 lines or more), checked from 1,500 characters of prose: below that one checklist decides the share. Turn reasoning back into sentences; keep lists for steps, options and inventories."
    },
    {
      "id": "DEN-07",
      "tier": "density",
      "lang": "ja",
      "metric": "ending_run",
      "max": 3,
      "note": "同じ文末が4文以上続く",
      "doc": "Four or more consecutive Japanese sentences ending in the same three characters (`〜できます。` ×4). Hard-wrapped lines are joined into their paragraph first, and a `。` inside `「」` or `『』` does not end a sentence. A heading or a table ends the run; a blank line between paragraphs does not. Combine sentences, change which part comes last, or cut one. Do not vary endings at random; vary them because the sentences say different kinds of things."
    },
    {
      "id": "DEN-08",
      "tier": "density",
      "lang": "any",
      "metric": "length_cv",
      "min": 0.3,
      "note": "Every sentence the same length",
      "doc": "Sentence-length coefficient of variation below 0.3 over eight or more sentences: every sentence the same length. Merge related short sentences and split overloaded ones where the content asks for it."
    },
    {
      "id": "DEN-09",
      "tier": "density",
      "lang": "en",
      "metric": "triad_count",
      "max": 2,
      "note": "Lists of exactly three, again and again",
      "doc": "Three or more `X, Y, and Z` lists (English). Keep the items that matter; two items or four are fine when that is how many there are."
    },
    {
      "id": "DEN-10",
      "tier": "density",
      "lang": "any",
      "metric": "hr_count",
      "max": 2,
      "note": "Horizontal rules between sections",
      "doc": "Three or more horizontal rules (`---`, `***`) between sections. Headings already separate sections; remove the rules. A slide deck or a document whose format uses rules as separators is a genre exemption."
    }
  ],
  "perspectives": [
    {
      "id": "STR-01",
      "name": "Announced opening",
      "doc": "**Announced opening.** The first paragraph says what the document will do, or restates the title. Delete it; the first sentence should already be content. An opening often wraps the one piece of content it has, the problem the document answers (`レビューに時間がかかりすぎる`), in an importance claim, a borrowed majority and an announcement. Delete the wrapping and keep that problem as one plain sentence; a reader new to the document needs it to know why the rest follows. When the announcement also tells how the sections are arranged (by period, then by theme), keep that arrangement as a plain sentence too; without it the next sentences point at nothing.",
      "group": "structure"
    },
    {
      "id": "STR-02",
      "name": "Closing that restates the body",
      "doc": "**Closing that restates the body.** A final section or paragraph repeats the main points. Delete it, or keep only what is new (a next step, a limit). The author's own feeling or stance in a closing (`私はターミナルを選びました`) is new, not a restatement: in a first-person article keep it even when the rest of the section goes. A \"challenges and future outlook\" close that ends on optimism is the same pattern (EN-26).",
      "group": "structure"
    },
    {
      "id": "STR-03",
      "name": "Moral at the end of every paragraph",
      "doc": "**Moral at the end of every paragraph.** Paragraphs close with a sentence that evaluates what was just said (\"This makes X much easier\"). Cut those sentences.",
      "group": "structure"
    },
    {
      "id": "STR-04",
      "name": "Padded triads and enumerations",
      "doc": "**Padded triads.** Groups of exactly three (adjectives, benefits, bullets) where the content has two or four. Keep the real number of items.",
      "group": "structure"
    },
    {
      "id": "STR-05",
      "name": "Over-structuring",
      "quiet": [
        "readme",
        "reference",
        "spec",
        "pr",
        "changelog"
      ],
      "doc": "**Over-structuring.** Headings, bullets, bold and tables where a paragraph would read better: a heading over two sentences, bullets that are one argument cut into pieces. Restore prose; keep structure the reader navigates or scans. A checklist, a template's fields, a set of labels or parallel tools each with its job is an inventory the reader scans or copies: drop its bold, keep it a list. Folded into one sentence (`〜か、〜か、〜か、です。`) it is harder to read than the list it replaced. A density limit is not a reason to flatten an inventory: when a density hit stands only because of such lists, exempt it and name the inventories in the reason. A heading that marks a change of topic is navigation even when its parent heading names both topics: after a figure, table or code block, after a paragraph or list that closes one subject, and over each of several parallel items (measures, options, steps) the reader compares. Removing a heading must not leave a topic change unmarked, a density limit is never the reason to remove one, and the gap is never filled with a signpost sentence (STR-10).",
      "group": "structure"
    },
    {
      "id": "STR-06",
      "name": "Symmetric sections",
      "quiet": [
        "reference",
        "spec",
        "changelog"
      ],
      "doc": "**Symmetric sections.** Every section has the same shape and length (intro sentence, three bullets, closing line). Let each section be as long as its content.",
      "group": "structure"
    },
    {
      "id": "STR-07",
      "name": "Generic claims without specifics",
      "doc": "**Generic claims.** Sentences that would be true of any product or topic (\"improves efficiency\", \"多くの企業が\"), claims credited to unnamed experts or studies (EN-24), and statistics with no source. Replace with the document's own specifics, or delete. Never invent the specifics. The content tests in `reference/content.md` decide whether such a claim has anything left to keep.",
      "group": "structure"
    },
    {
      "id": "STR-08",
      "name": "Hedging and false balance",
      "doc": "**Hedging and false balance.** Qualifiers on things the document knows; \"on the other hand\" sections that exist only to look balanced, and pros-and-cons that end without a choice (`一概には言えません`, JA-29). State what is known; keep a caveat only where there is a real condition.",
      "group": "structure"
    },
    {
      "id": "STR-09",
      "name": "Reflexive contrast framing",
      "doc": "**Reflexive contrast framing.** Repeated \"not X but Y\" (`単なる〜ではなく`) against a position nobody holds. State Y.",
      "group": "structure"
    },
    {
      "id": "STR-10",
      "name": "Signposting and meta-commentary",
      "doc": "**Signposting and meta-commentary.** \"Next, let's look at…\", \"次に〜を見て いきましょう\", \"As mentioned above\". Delete; headings and order already signpost.",
      "group": "structure"
    },
    {
      "id": "STR-11",
      "name": "Restatement",
      "doc": "**Restatement.** The same point twice in a row in different words (`つまり`, `In other words`). Keep the clearer one.",
      "group": "structure"
    },
    {
      "id": "STR-12",
      "name": "Register and enthusiasm mismatch",
      "doc": "**Register and enthusiasm mismatch.** Hype, exclamation, praise of the reader or sympathy formulas in a technical or business document. Match the register in `voice`.",
      "group": "structure"
    },
    {
      "id": "STR-13",
      "name": "Uniform rhythm",
      "doc": "**Uniform rhythm.** Every sentence the same length and build, every paragraph three sentences. Let the content set the rhythm: combine what belongs together, split what is overloaded (see DEN-07, DEN-08).",
      "group": "structure"
    },
    {
      "id": "STR-14",
      "name": "Question headings and FAQ padding",
      "doc": "**Question headings and FAQ padding.** Headings phrased as the reader's question (`〜とは？`, \"What is X?\"), FAQ entries nobody asks. Name the content; fold padding questions into the text or delete them.",
      "group": "structure"
    },
    {
      "id": "STR-15",
      "name": "Translationese",
      "doc": "**Translationese.** English structure in Japanese (`〜において`, explicit pronouns `それは`, `〜することができる`, a subject in every sentence) or Japanese structure in English. Rewrite as a native writer of the target language would.",
      "group": "structure"
    },
    {
      "id": "STR-16",
      "name": "Voice drift from the author",
      "doc": "**Voice drift from the author.** The rewrite or the original drifts from the rules in `voice`: register changes mid-document, terms translated that the author keeps in English, a different person addressing the reader. Bring it back to the recorded voice.",
      "group": "structure"
    },
    {
      "id": "STR-17",
      "name": "Detail the reader cannot skip",
      "only": [
        "pr"
      ],
      "doc": "**Detail the reader cannot skip.** A pull request description longer than one screen with every section at the same level: the reviewer reads all of it to learn what the change is and whether it needs them. Put the shortest text that answers those two questions first, then fold the rest into one `<details>` block, as Simon Willison does with agent-written descriptions (<https://simonwillison.net/2026/Nov/9/details-summary/>). - The opener is one to three sentences chosen from the document. Nothing is written for it that the document does not say. It is the author's statement of what deserves the reader's time, so list it under `decisions` for the author to confirm. - What a reviewer must act on stays outside the fold: breaking changes, questions put to the reviewer, screenshots, and every section the repository's PR template requires (ticket number, disclosure, checklist). - The fold exempts nothing. Every rule and perspective applies to the text inside it as it does outside, and it is rewritten the same way. - `<summary>` names what is folded (`Details`, `詳細`). A model name goes there only when the document or the requester gives one. - Write `<details>`, then `<summary>…</summary>` on its own line, a blank line, the Markdown, a blank line, `</details>`. Without the blank line the Markdown stays part of the HTML block and is shown as typed (CommonMark, HTML blocks). Headings, tables and code blocks move into the fold unchanged; do not convert them to HTML tags. - A description under 20 non-blank lines stays flat: a fold over a few lines is over-structuring (STR-05). One fold, closed by default (no `open`).",
      "group": "structure"
    },
    {
      "id": "CON-01",
      "name": "Sentence that tells the reader nothing",
      "doc": "**Sentence that tells the reader nothing.** Fails the information or substitution test: `キャッシュはパフォーマンスにとって重要です`, `Security is a top priority`, `This guide will help you get the most out of X`. Delete it. Do not replace it with a better-sounding sentence of the same emptiness.",
      "group": "content"
    },
    {
      "id": "CON-02",
      "name": "Content the reader already knows or does not need",
      "doc": "**Content the reader already knows or does not need.** Definitions of terms the reader uses daily, reminders to test and back up, a history of the field in an installation guide. Judge against the least experienced reader the document names or addresses (a FAQ for all staff includes new hires, who need `報連相` spelled out): an API reference does not explain what an API is. Delete it, or link to where it is explained if the document already links there.",
      "group": "content"
    },
    {
      "id": "CON-03",
      "name": "Unsupported specifics",
      "doc": "**Unsupported specifics.** Statistics, study results, quotations, dates, user counts and benchmark figures with no source in the document and no way to derive them from it (`導入企業の約30%が効果を実感`, `studies show a 40% increase`). Generated drafts invent these. They are never verified or replaced by this skill: when the figure is decoration (an opening hook, an aside nothing else depends on), delete the sentence and record the number in `preservation`; when the document's argument rests on it, keep it unchanged and list it under `decisions` as needing a source. `CNT-01` points at percentages and multipliers with nothing cited in their paragraph. When the document itself says its specifics are assumed or unverified (a generated reference whose options were invented), that statement is the support status: keep it as a plain sentence, never delete it (EN-25, JA-33).",
      "group": "content"
    },
    {
      "id": "CON-04",
      "name": "Invented or generic illustration",
      "doc": "**Invented or generic illustration.** Hypothetical scenarios and personas (`Imagine you're a developer who…`, `例えば、あなたが`, `Aさん（仮名）の場合`) and examples that fit any product (`EC サイトや SNS など`). If the document has a real example, use that one; otherwise delete the illustration and keep the point it was meant to illustrate, stated directly.",
      "group": "content"
    },
    {
      "id": "CON-05",
      "name": "Coverage padding",
      "doc": "**Coverage padding.** Sections and bullets present because a complete article \"should\" have them: benefits, use cases, best practices, security considerations, future prospects, FAQ, each one generic. Keep what the reader needs for their task and what is specific to this subject; remove the rest, headings included. Ask what the reader would miss, not what a table of contents would miss.",
      "group": "content"
    },
    {
      "id": "CON-06",
      "name": "No position where the document has the basis for one",
      "doc": "**No position where the document has the basis for one.** Options compared and left at `一概には言えません` or \"it depends on your needs\" when the document itself contains the conditions that decide. State the choice under each condition the document gives (`更新が多いなら TTL を短く`). When the document does not contain the basis, delete the empty comparison rather than inventing a recommendation, and list the open question under `decisions`.",
      "group": "content"
    },
    {
      "id": "CON-07",
      "name": "Effect claimed without a mechanism",
      "doc": "**Effect claimed without a mechanism.** Benefits asserted with no account of how they happen: `生産性が向上します`, `improves the developer experience`, `ユーザー満足度を高めます`. Replace with the mechanism the document describes (what the reader no longer has to do, what the system skips), or delete the claim when the document describes none.",
      "group": "content"
    },
    {
      "id": "CON-08",
      "name": "Borrowed authority or experience",
      "doc": "**Borrowed authority or experience.** Appeals to unnamed experts, trends and majorities (`専門家によると`, `多くの企業が`, `experts agree`), and first-person experience the author's other material does not support (`私も以前は〜で悩んで いました`, `In my years of experience`). Name the source the document actually cites, or cut the appeal and keep the claim only if the document supports it. First-person experience is never deleted on suspicion alone: when nothing in `voice` or the document backs it, list it under `decisions` for the author to confirm or remove.",
      "group": "content"
    }
  ],
  "genres": [
    {
      "id": "general",
      "name": "General prose",
      "match": [],
      "exempt": {},
      "limits": {}
    },
    {
      "id": "readme",
      "name": "README",
      "match": [
        "readme*"
      ],
      "exempt": {
        "DEN-06": "install steps and feature inventories are lists"
      },
      "limits": {
        "DEN-05": {
          "max": 8.0
        }
      }
    },
    {
      "id": "reference",
      "name": "API / reference",
      "match": [],
      "exempt": {
        "DEN-01": "parameter and option names are bold",
        "DEN-04": "parameters are listed as name: description",
        "DEN-05": "one heading per endpoint, command or option",
        "DEN-06": "parameter lists are lists",
        "DEN-08": "terse entries share one build"
      },
      "limits": {}
    },
    {
      "id": "tutorial",
      "name": "Tutorial",
      "match": [],
      "exempt": {
        "DEN-05": "one heading per step",
        "DEN-06": "the steps are a numbered list"
      },
      "limits": {
        "DEN-03": {
          "max": 0
        }
      }
    },
    {
      "id": "article",
      "name": "Blog / article",
      "match": [],
      "exempt": {},
      "limits": {
        "DEN-01": {
          "max": 1.5
        },
        "DEN-04": {
          "max": 0
        },
        "DEN-05": {
          "max": 3.0
        },
        "DEN-06": {
          "max": 0.3
        }
      }
    },
    {
      "id": "spec",
      "name": "Spec / RFC",
      "match": [],
      "exempt": {
        "DEN-05": "one section per requirement",
        "DEN-06": "requirements are numbered items",
        "DEN-08": "requirements share one build"
      },
      "limits": {
        "DEN-03": {
          "max": 0
        }
      }
    },
    {
      "id": "pr",
      "name": "PR description",
      "match": [],
      "exempt": {
        "DEN-06": "one bullet per change"
      },
      "limits": {
        "DEN-03": {
          "max": 0
        },
        "DEN-10": {
          "max": 0
        }
      }
    },
    {
      "id": "message",
      "name": "Email / message",
      "match": [],
      "exempt": {
        "EN-20": "an invitation to reply is customary in a message to a person",
        "JA-21": "人宛てのメッセージでは問い合わせへの誘いが慣習"
      },
      "limits": {
        "DEN-04": {
          "max": 0
        },
        "DEN-05": {
          "max": 0
        },
        "DEN-06": {
          "max": 0.3
        }
      }
    },
    {
      "id": "changelog",
      "name": "Changelog",
      "match": [
        "changelog*",
        "changes*",
        "history*",
        "news*"
      ],
      "exempt": {
        "DEN-05": "one heading per release",
        "DEN-06": "one bullet per change",
        "DEN-08": "entries share one build"
      },
      "limits": {}
    },
    {
      "id": "template",
      "name": "Template",
      "match": [],
      "exempt": {
        "ART-07": "the placeholders are the fields its user fills in",
        "DEN-04": "each field has its bold label"
      },
      "limits": {}
    }
  ],
  "samples": {
    "ja_cache": {
      "id": "ja_cache",
      "label": "日本語：キャッシュ設定ガイド (examples/before.ja.md)",
      "shortLabel": "examples/before.ja.md",
      "lang": "ja",
      "genre": "general",
      "before": "# キャッシュ設定ガイド：パフォーマンスを最大限に引き出す完全ガイド 🚀\n\n本記事では、`tilecache` のキャッシュ設定について詳しく解説します。\n\n## キャッシュとは？\n\n現代のWebアプリケーションにおいて、キャッシュは重要な役割を果たしています。多くの企業がキャッシュを導入しており、導入企業の約30%がレスポンス改善を実感していると言われています。キャッシュを活用することで、レスポンス速度の向上が可能になります。キャッシュは単なる高速化の手段ではなく、システム全体の安定性を支える基盤と言っても過言ではありません。\n\n## 設定のポイント\n\n設定のポイントとしては、以下の3つが挙げられます。\n\n- **TTL**: キャッシュの有効期限を設定することができます。\n- **容量**: メモリ上限を設定することができます。\n- **退避方式**: 古いエントリの扱いを設定することができます。\n\nTTL は `ttl_seconds` で指定します。既定値は 300 秒です。容量は `max_entries` で指定し、既定値は 10000 件です。\n\n```toml\n[cache]\nttl_seconds = 300\nmax_entries = 10000\n```\n\nつまり、TTL と容量の2つを調整することが鍵となります。さまざまな用途に合わせて柔軟に設定してみてはいかがでしょうか。\n\n## まとめ\n\nいかがでしたか？キャッシュを正しく設定することで、アプリケーションのパフォーマンスを飛躍的に向上させることが期待されます。詳細は https://example.com/tilecache/docs を参照してください。参考になれば幸いです！\n",
      "after": "# キャッシュ設定\n\n`tilecache` のキャッシュ設定は TTL、容量、退避方式の3項目です。TTL は `ttl_seconds` で指定し、既定値は 300 秒です。容量は `max_entries` で指定し、既定値は 10000 件です。\n\n```toml\n[cache]\nttl_seconds = 300\nmax_entries = 10000\n```\n\n詳細は https://example.com/tilecache/docs を参照してください。\n",
      "preserved": [
        {
          "kind": "inline_code",
          "value": "tilecache"
        },
        {
          "kind": "inline_code",
          "value": "ttl_seconds"
        },
        {
          "kind": "number",
          "value": "300"
        },
        {
          "kind": "inline_code",
          "value": "max_entries"
        },
        {
          "kind": "number",
          "value": "10000"
        },
        {
          "kind": "code_block",
          "value": "[cache]\\nttl_seconds = 300\\nmax_entries = 10000"
        },
        {
          "kind": "url",
          "value": "https://example.com/tilecache/docs"
        }
      ],
      "dropped_stats": [
        {
          "kind": "number",
          "value": "30%",
          "reason": "出典のない装飾統計（導入企業の約30%が実感）をCON-03/CNT-01により削除しpreservationに記録"
        }
      ],
      "before_scan": {
        "lang": "ja",
        "genre": "general",
        "metrics": {
          "chars": 594,
          "sentences": 18,
          "bold_per_1000": 5.050505050505051,
          "dash_per_1000": 0.0,
          "exclaim_ratio": 0.05555555555555555,
          "boldlead_items": 3,
          "heading_per_1000": 6.734006734006734,
          "list_ratio": 0,
          "ending_run": 3,
          "length_cv": 0.4027704970610317,
          "triad_count": 0,
          "hr_count": 0
        },
        "hits": [
          {
            "line": 1,
            "col": 1,
            "rule": "DEN-01",
            "tier": "density",
            "text": "bold_per_1000=5.05 (max 3.0)",
            "context": "document",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Too much bold: emphasis on everything is emphasis on nothing"
          },
          {
            "line": 1,
            "col": 1,
            "rule": "DEN-03",
            "tier": "density",
            "text": "exclaim_ratio=0.06 (max 0.05)",
            "context": "document",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Exclamation marks in expository text"
          },
          {
            "line": 1,
            "col": 1,
            "rule": "DEN-04",
            "tier": "density",
            "text": "boldlead_items=3 (max 2)",
            "context": "document",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Bullet lists of '**Label**: explanation'"
          },
          {
            "line": 1,
            "col": 22,
            "rule": "JA-06",
            "tier": "lexical",
            "text": "最大限に引き出",
            "context": "heading",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "中身のない宣伝語"
          },
          {
            "line": 1,
            "col": 30,
            "rule": "JA-14",
            "tier": "lexical",
            "text": "完全ガイド",
            "context": "heading",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "冒険・探求の比喩"
          },
          {
            "line": 1,
            "col": 36,
            "rule": "EMO-01",
            "tier": "lexical",
            "text": "🚀",
            "context": "heading",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Decorative emoji in prose or headings"
          },
          {
            "line": 3,
            "col": 1,
            "rule": "JA-08",
            "tier": "lexical",
            "text": "本記事では、`tilecache` のキャッシュ設定について詳しく解説します",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "これから書く内容の予告"
          },
          {
            "line": 3,
            "col": 31,
            "rule": "JA-23",
            "tier": "lexical",
            "text": "詳しく解説します",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "本題の前の道案内"
          },
          {
            "line": 5,
            "col": 1,
            "rule": "JA-17",
            "tier": "lexical",
            "text": "## キャッシュとは？",
            "context": "heading",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "SEO記事型の見出し"
          },
          {
            "line": 7,
            "col": 26,
            "rule": "JA-03",
            "tier": "lexical",
            "text": "重要な役割を果たし",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "重要さを示さずに宣言する"
          },
          {
            "line": 7,
            "col": 40,
            "rule": "JA-31",
            "tier": "lexical",
            "text": "多くの企業が",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "出典を示さない伝聞や多数派への言及"
          },
          {
            "line": 7,
            "col": 65,
            "rule": "CNT-01",
            "tier": "content",
            "text": "30%",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Figure stated as a claim with nothing cited in its paragraph"
          },
          {
            "line": 7,
            "col": 83,
            "rule": "JA-31",
            "tier": "lexical",
            "text": "と言われています",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "出典を示さない伝聞や多数派への言及"
          },
          {
            "line": 7,
            "col": 102,
            "rule": "JA-07",
            "tier": "lexical",
            "text": "ことで、レスポンス速度の向上が可能になり",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "「〜することで〜が可能になります」型の抽象的な効能文"
          },
          {
            "line": 7,
            "col": 131,
            "rule": "JA-12",
            "tier": "lexical",
            "text": "単なる高速化の手段ではなく",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "反射的な「AではなくB」対比"
          },
          {
            "line": 7,
            "col": 161,
            "rule": "JA-02",
            "tier": "lexical",
            "text": "と言っても過言ではありません",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "誇張の定型句"
          },
          {
            "line": 9,
            "col": 1,
            "rule": "JA-17",
            "tier": "lexical",
            "text": "## 設定のポイント",
            "context": "heading",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "SEO記事型の見出し"
          },
          {
            "line": 11,
            "col": 18,
            "rule": "JA-13",
            "tier": "lexical",
            "text": "が挙げられます",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "列挙の定型句"
          },
          {
            "line": 13,
            "col": 25,
            "rule": "JA-04",
            "tier": "lexical",
            "text": "することができます",
            "context": "list",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "「〜できる」で足りる冗長形"
          },
          {
            "line": 14,
            "col": 19,
            "rule": "JA-04",
            "tier": "lexical",
            "text": "することができます",
            "context": "list",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "「〜できる」で足りる冗長形"
          },
          {
            "line": 15,
            "col": 25,
            "rule": "JA-04",
            "tier": "lexical",
            "text": "することができます",
            "context": "list",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "「〜できる」で足りる冗長形"
          },
          {
            "line": 25,
            "col": 1,
            "rule": "JA-11",
            "tier": "lexical",
            "text": "つまり、",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "直前の文の言い直し"
          },
          {
            "line": 25,
            "col": 22,
            "rule": "JA-03",
            "tier": "lexical",
            "text": "が鍵となります",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "重要さを示さずに宣言する"
          },
          {
            "line": 25,
            "col": 30,
            "rule": "JA-18",
            "tier": "lexical",
            "text": "さまざまな用途",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "具体例の代わりの「さまざまな〜」"
          },
          {
            "line": 25,
            "col": 47,
            "rule": "JA-10",
            "tier": "lexical",
            "text": "してみてはいかがでしょうか",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "読者への勧誘"
          },
          {
            "line": 27,
            "col": 1,
            "rule": "JA-09",
            "tier": "lexical",
            "text": "## まとめ",
            "context": "heading",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "本文を繰り返すだけの締め"
          },
          {
            "line": 29,
            "col": 1,
            "rule": "ART-04",
            "tier": "artifact",
            "text": "いかがでしたか",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Chat reply closer addressed to whoever asked"
          },
          {
            "line": 29,
            "col": 43,
            "rule": "JA-06",
            "tier": "lexical",
            "text": "飛躍的に",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "中身のない宣伝語"
          },
          {
            "line": 29,
            "col": 52,
            "rule": "JA-16",
            "tier": "lexical",
            "text": "ことが期待されます",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "出典のない動向の断定"
          },
          {
            "line": 29,
            "col": 111,
            "rule": "ART-04",
            "tier": "artifact",
            "text": "参考になれば幸いです",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Chat reply closer addressed to whoever asked"
          }
        ],
        "cues": [
          {
            "path": "input.md",
            "line": 3,
            "perspective": "STR-01",
            "text": "本記事では、`tilecache` のキャッシュ設定について詳しく解説します。",
            "why": "the opening sentence announces what the document will do",
            "name": "Announced opening"
          },
          {
            "path": "input.md",
            "line": 5,
            "perspective": "STR-14",
            "text": "## キャッシュとは？",
            "why": "heading phrased as the reader's question",
            "name": "Question headings and FAQ padding"
          },
          {
            "path": "input.md",
            "line": 27,
            "perspective": "STR-02",
            "text": "## まとめ",
            "why": "the last section is a summary by name",
            "name": "Closing that restates the body"
          }
        ],
        "summary": {
          "files": 1,
          "total": 30,
          "open": 30,
          "exempt": 0,
          "by_rule": {
            "ART-04": 2,
            "CNT-01": 1,
            "DEN-01": 1,
            "DEN-03": 1,
            "DEN-04": 1,
            "EMO-01": 1,
            "JA-02": 1,
            "JA-03": 2,
            "JA-04": 3,
            "JA-06": 2,
            "JA-07": 1,
            "JA-08": 1,
            "JA-09": 1,
            "JA-10": 1,
            "JA-11": 1,
            "JA-12": 1,
            "JA-13": 1,
            "JA-14": 1,
            "JA-16": 1,
            "JA-17": 2,
            "JA-18": 1,
            "JA-23": 1,
            "JA-31": 2
          },
          "cues": 3
        },
        "diagnosis": "# deslop diagnosis\n\n1 documents, 30 hits: **30 open**, 0 exempt; 3 perspective cues.\n\nHits are candidates read in context, not verdicts. Most are fixed by deleting the sentence or word; see `reference/patterns.md` for each rule.\n\n| Document | Genre | Language | Prose chars | Open | Exempt | Cues |\n|---|---|---|---:|---:|---:|---:|\n| <code>input.md</code> | general | ja | 594 | 30 | 0 | 3 |\n\n## <code>input.md</code>\n\nGeneral prose (`general`), ja, 594 prose characters in 18 sentences.\n\n### Open hits by section\n\nMost frequent: JA-04 ×3, JA-06 ×2, JA-17 ×2, JA-03 ×2, JA-31 ×2.\n\n| Line | Section | Rule | Text | What it is |\n|---:|---|---|---|---|\n| 1:22 | キャッシュ設定ガイド：パフォーマンスを最大限に引き出す完全ガイド 🚀 | JA-06 | <code>最大限に引き出</code> | 中身のない宣伝語 |\n| 1:30 | キャッシュ設定ガイド：パフォーマンスを最大限に引き出す完全ガイド 🚀 | JA-14 | <code>完全ガイド</code> | 冒険・探求の比喩 |\n| 1:36 | キャッシュ設定ガイド：パフォーマンスを最大限に引き出す完全ガイド 🚀 | EMO-01 | <code>🚀</code> | Decorative emoji in prose or headings |\n| 3:1 | キャッシュ設定ガイド：パフォーマンスを最大限に引き出す完全ガイド 🚀 | JA-08 | <code>本記事では、`tilecache` のキャッシュ設定について詳しく解説します</code> | これから書く内容の予告 |\n| 3:31 | キャッシュ設定ガイド：パフォーマンスを最大限に引き出す完全ガイド 🚀 | JA-23 | <code>詳しく解説します</code> | 本題の前の道案内 |\n| 5:1 | キャッシュとは？ | JA-17 | <code>## キャッシュとは？</code> | SEO記事型の見出し |\n| 7:26 | キャッシュとは？ | JA-03 | <code>重要な役割を果たし</code> | 重要さを示さずに宣言する |\n| 7:40 | キャッシュとは？ | JA-31 | <code>多くの企業が</code> | 出典を示さない伝聞や多数派への言及 |\n| 7:65 | キャッシュとは？ | CNT-01 | <code>30%</code> | Figure stated as a claim with nothing cited in its paragraph |\n| 7:83 | キャッシュとは？ | JA-31 | <code>と言われています</code> | 出典を示さない伝聞や多数派への言及 |\n| 7:102 | キャッシュとは？ | JA-07 | <code>ことで、レスポンス速度の向上が可能になり</code> | 「〜することで〜が可能になります」型の抽象的な効能文 |\n| 7:131 | キャッシュとは？ | JA-12 | <code>単なる高速化の手段ではなく</code> | 反射的な「AではなくB」対比 |\n| 7:161 | キャッシュとは？ | JA-02 | <code>と言っても過言ではありません</code> | 誇張の定型句 |\n| 9:1 | 設定のポイント | JA-17 | <code>## 設定のポイント</code> | SEO記事型の見出し |\n| 11:18 | 設定のポイント | JA-13 | <code>が挙げられます</code> | 列挙の定型句 |\n| 13:25 | 設定のポイント | JA-04 | <code>することができます</code> | 「〜できる」で足りる冗長形 |\n| 14:19 | 設定のポイント | JA-04 | <code>することができます</code> | 「〜できる」で足りる冗長形 |\n| 15:25 | 設定のポイント | JA-04 | <code>することができます</code> | 「〜できる」で足りる冗長形 |\n| 25:1 | 設定のポイント | JA-11 | <code>つまり、</code> | 直前の文の言い直し |\n| 25:22 | 設定のポイント | JA-03 | <code>が鍵となります</code> | 重要さを示さずに宣言する |\n| 25:30 | 設定のポイント | JA-18 | <code>さまざまな用途</code> | 具体例の代わりの「さまざまな〜」 |\n| 25:47 | 設定のポイント | JA-10 | <code>してみてはいかがでしょうか</code> | 読者への勧誘 |\n| 27:1 | まとめ | JA-09 | <code>## まとめ</code> | 本文を繰り返すだけの締め |\n| 29:1 | まとめ | ART-04 | <code>いかがでしたか</code> | Chat reply closer addressed to whoever asked |\n| 29:43 | まとめ | JA-06 | <code>飛躍的に</code> | 中身のない宣伝語 |\n| 29:52 | まとめ | JA-16 | <code>ことが期待されます</code> | 出典のない動向の断定 |\n| 29:111 | まとめ | ART-04 | <code>参考になれば幸いです</code> | Chat reply closer addressed to whoever asked |\n\n### Density across the document\n\n| Rule | Measure (limit) | What it is |\n|---|---|---|\n| DEN-01 | <code>bold_per_1000=5.05 (max 3.0)</code> | Too much bold: emphasis on everything is emphasis on nothing |\n| DEN-03 | <code>exclaim_ratio=0.06 (max 0.05)</code> | Exclamation marks in expository text |\n| DEN-04 | <code>boldlead_items=3 (max 2)</code> | Bullet lists of '**Label**: explanation' |\n\n### Where to read for perspectives\n\nCues are not hits. They name lines where a content or structural perspective probably applies (`reference/content.md`, `reference/structure.md`).\n\n| Line | Section | Perspective | Why | Line text |\n|---:|---|---|---|---|\n| 3 | キャッシュ設定ガイド：パフォーマンスを最大限に引き出す完全ガイド 🚀 | STR-01 Announced opening | the opening sentence announces what the document will do | <code>本記事では、`tilecache` のキャッシュ設定について詳しく解説します。</code> |\n| 5 | キャッシュとは？ | STR-14 Question headings and FAQ padding | heading phrased as the reader's question | <code>## キャッシュとは？</code> |\n| 27 | まとめ | STR-02 Closing that restates the body | the last section is a summary by name | <code>## まとめ</code> |\n"
      },
      "after_scan": {
        "lang": "ja",
        "genre": "general",
        "metrics": {
          "chars": 153,
          "sentences": 4,
          "bold_per_1000": 0.0,
          "dash_per_1000": 0.0,
          "exclaim_ratio": 0.0,
          "boldlead_items": 0,
          "heading_per_1000": 6.5359477124183005,
          "list_ratio": 0,
          "ending_run": 1,
          "length_cv": null,
          "triad_count": 0,
          "hr_count": 0
        },
        "hits": [],
        "cues": [],
        "summary": {
          "files": 1,
          "total": 0,
          "open": 0,
          "exempt": 0,
          "by_rule": {},
          "cues": 0
        },
        "diagnosis": "# deslop diagnosis\n\n1 documents, 0 hits: **0 open**, 0 exempt; 0 perspective cues.\n\n| Document | Genre | Language | Prose chars | Open | Exempt | Cues |\n|---|---|---|---:|---:|---:|---:|\n| <code>input.md</code> | general | ja | 153 | 0 | 0 | 0 |\n\n## <code>input.md</code>\n\nGeneral prose (`general`), ja, 153 prose characters in 4 sentences.\n\nNo hits and no cues.\n"
      }
    },
    "en_cache": {
      "id": "en_cache",
      "label": "English: Tile Caching Guide (examples/before.en.md)",
      "shortLabel": "examples/before.en.md",
      "lang": "en",
      "genre": "general",
      "before": "# Unlocking the Power of Tile Caching: A Comprehensive Guide\n\nCertainly! Here's a revised overview of caching in `tilecache`.\n\nIn today's fast-paced digital landscape, performance plays a crucial role in user experience. Let's dive into how tilecache can help you leverage caching to deliver a seamless experience — whether you're a seasoned engineer or just getting started.\n\n## Key Settings\n\n- **TTL**: Controls how long an entry lives.\n- **Capacity**: Controls how many entries are kept.\n- **Eviction**: Controls which entries are removed first.\n\nTTL is set with `ttl_seconds`; the default is 300 seconds. Capacity is set with `max_entries`; the default is 10000 entries.\n\n```toml\n[cache]\nttl_seconds = 300\nmax_entries = 10000\n```\n\nIt's important to note that caching isn't just about speed — it's about reliability, scalability, and peace of mind. Moreover, a robust cache configuration underscores the importance of thoughtful system design.\n\n## Conclusion\n\nIn conclusion, tuning TTL and capacity can potentially transform your application. See https://example.com/tilecache/docs for details. I hope this helps!\n",
      "after": "# Tile caching\n\n`tilecache` has three cache settings: TTL, capacity and eviction. TTL is set with `ttl_seconds`; the default is 300 seconds. Capacity is set with `max_entries`; the default is 10000 entries.\n\n```toml\n[cache]\nttl_seconds = 300\nmax_entries = 10000\n```\n\nSee https://example.com/tilecache/docs for details.\n",
      "preserved": [
        {
          "kind": "inline_code",
          "value": "tilecache"
        },
        {
          "kind": "inline_code",
          "value": "ttl_seconds"
        },
        {
          "kind": "number",
          "value": "300"
        },
        {
          "kind": "inline_code",
          "value": "max_entries"
        },
        {
          "kind": "number",
          "value": "10000"
        },
        {
          "kind": "code_block",
          "value": "[cache]\\nttl_seconds = 300\\nmax_entries = 10000"
        },
        {
          "kind": "url",
          "value": "https://example.com/tilecache/docs"
        }
      ],
      "dropped_stats": [],
      "before_scan": {
        "lang": "en",
        "genre": "general",
        "metrics": {
          "chars": 951,
          "sentences": 14,
          "bold_per_1000": 3.1545741324921135,
          "dash_per_1000": 2.103049421661409,
          "exclaim_ratio": 0.14285714285714285,
          "boldlead_items": 3,
          "heading_per_1000": 3.1545741324921135,
          "list_ratio": 0,
          "ending_run": 1,
          "length_cv": 0.6206096799708021,
          "triad_count": 2,
          "hr_count": 0
        },
        "hits": [
          {
            "line": 1,
            "col": 1,
            "rule": "DEN-01",
            "tier": "density",
            "text": "bold_per_1000=3.15 (max 3.0)",
            "context": "document",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Too much bold: emphasis on everything is emphasis on nothing"
          },
          {
            "line": 1,
            "col": 1,
            "rule": "DEN-02",
            "tier": "density",
            "text": "dash_per_1000=2.1 (max 1.5)",
            "context": "document",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Em-dash habit"
          },
          {
            "line": 1,
            "col": 1,
            "rule": "DEN-03",
            "tier": "density",
            "text": "exclaim_ratio=0.14 (max 0.05)",
            "context": "document",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Exclamation marks in expository text"
          },
          {
            "line": 1,
            "col": 1,
            "rule": "DEN-04",
            "tier": "density",
            "text": "boldlead_items=3 (max 2)",
            "context": "document",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Bullet lists of '**Label**: explanation'"
          },
          {
            "line": 1,
            "col": 3,
            "rule": "EN-03",
            "tier": "lexical",
            "text": "Unlocking the Power",
            "context": "heading",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Inflated verb where a plain one says the same"
          },
          {
            "line": 1,
            "col": 42,
            "rule": "EN-14",
            "tier": "lexical",
            "text": "Comprehensive",
            "context": "heading",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Intensifier adjective standing in for detail"
          },
          {
            "line": 3,
            "col": 1,
            "rule": "ART-01",
            "tier": "artifact",
            "text": "Certainly!",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Chat reply opener left in the document"
          },
          {
            "line": 3,
            "col": 12,
            "rule": "ART-08",
            "tier": "artifact",
            "text": "Here's a revised",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Framing of a chat response rather than the document itself"
          },
          {
            "line": 5,
            "col": 1,
            "rule": "EN-07",
            "tier": "lexical",
            "text": "In today's fast-paced digital landscape",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Generic scene-setting opener"
          },
          {
            "line": 5,
            "col": 54,
            "rule": "EN-05",
            "tier": "lexical",
            "text": "plays a crucial role",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Importance asserted instead of shown"
          },
          {
            "line": 5,
            "col": 95,
            "rule": "EN-12",
            "tier": "lexical",
            "text": "Let's dive",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Signposted dive instead of starting"
          },
          {
            "line": 5,
            "col": 138,
            "rule": "EN-03",
            "tier": "lexical",
            "text": "leverage",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Inflated verb where a plain one says the same"
          },
          {
            "line": 5,
            "col": 168,
            "rule": "EN-04",
            "tier": "lexical",
            "text": "seamless",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Promotional adjective with no measurable content"
          },
          {
            "line": 5,
            "col": 190,
            "rule": "EN-15",
            "tier": "lexical",
            "text": "whether you're a seasoned engineer or",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Audience-widening 'whether you're X or Y'"
          },
          {
            "line": 21,
            "col": 1,
            "rule": "EN-06",
            "tier": "lexical",
            "text": "It's important to note",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Throat-clearing before the actual point"
          },
          {
            "line": 21,
            "col": 37,
            "rule": "EN-10",
            "tier": "lexical",
            "text": "isn't just",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Reflexive 'not X but Y' contrast"
          },
          {
            "line": 21,
            "col": 118,
            "rule": "EN-09",
            "tier": "lexical",
            "text": "Moreover,",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Essay connective stacking paragraphs mechanically"
          },
          {
            "line": 21,
            "col": 130,
            "rule": "EN-04",
            "tier": "lexical",
            "text": "robust",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Promotional adjective with no measurable content"
          },
          {
            "line": 21,
            "col": 157,
            "rule": "EN-13",
            "tier": "lexical",
            "text": "underscores",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Significance verb that adds no information"
          },
          {
            "line": 25,
            "col": 1,
            "rule": "EN-08",
            "tier": "lexical",
            "text": "In conclusion,",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Formulaic wrap-up that restates the body"
          },
          {
            "line": 25,
            "col": 40,
            "rule": "EN-16",
            "tier": "lexical",
            "text": "can potentially",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Stacked hedge"
          },
          {
            "line": 25,
            "col": 136,
            "rule": "ART-03",
            "tier": "artifact",
            "text": "I hope this helps",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Chat reply closer addressed to whoever asked"
          }
        ],
        "cues": [
          {
            "path": "input.md",
            "line": 3,
            "perspective": "STR-13",
            "text": "Certainly! Here's a revised overview of caching in `tilecache`.",
            "why": "4 of 5 paragraphs have 2 sentences",
            "name": "Uniform rhythm"
          },
          {
            "path": "input.md",
            "line": 23,
            "perspective": "STR-02",
            "text": "## Conclusion",
            "why": "the last section is a summary by name",
            "name": "Closing that restates the body"
          }
        ],
        "summary": {
          "files": 1,
          "total": 22,
          "open": 22,
          "exempt": 0,
          "by_rule": {
            "ART-01": 1,
            "ART-03": 1,
            "ART-08": 1,
            "DEN-01": 1,
            "DEN-02": 1,
            "DEN-03": 1,
            "DEN-04": 1,
            "EN-03": 2,
            "EN-04": 2,
            "EN-05": 1,
            "EN-06": 1,
            "EN-07": 1,
            "EN-08": 1,
            "EN-09": 1,
            "EN-10": 1,
            "EN-12": 1,
            "EN-13": 1,
            "EN-14": 1,
            "EN-15": 1,
            "EN-16": 1
          },
          "cues": 2
        },
        "diagnosis": "# deslop diagnosis\n\n1 documents, 22 hits: **22 open**, 0 exempt; 2 perspective cues.\n\nHits are candidates read in context, not verdicts. Most are fixed by deleting the sentence or word; see `reference/patterns.md` for each rule.\n\n| Document | Genre | Language | Prose chars | Open | Exempt | Cues |\n|---|---|---|---:|---:|---:|---:|\n| <code>input.md</code> | general | en | 951 | 22 | 0 | 2 |\n\n## <code>input.md</code>\n\nGeneral prose (`general`), en, 951 prose characters in 14 sentences.\n\n### Open hits by section\n\nMost frequent: EN-03 ×2, EN-04 ×2, EN-14 ×1, ART-01 ×1, ART-08 ×1.\n\n| Line | Section | Rule | Text | What it is |\n|---:|---|---|---|---|\n| 1:3 | Unlocking the Power of Tile Caching: A Comprehensive Guide | EN-03 | <code>Unlocking the Power</code> | Inflated verb where a plain one says the same |\n| 1:42 | Unlocking the Power of Tile Caching: A Comprehensive Guide | EN-14 | <code>Comprehensive</code> | Intensifier adjective standing in for detail |\n| 3:1 | Unlocking the Power of Tile Caching: A Comprehensive Guide | ART-01 | <code>Certainly!</code> | Chat reply opener left in the document |\n| 3:12 | Unlocking the Power of Tile Caching: A Comprehensive Guide | ART-08 | <code>Here's a revised</code> | Framing of a chat response rather than the document itself |\n| 5:1 | Unlocking the Power of Tile Caching: A Comprehensive Guide | EN-07 | <code>In today's fast-paced digital landscape</code> | Generic scene-setting opener |\n| 5:54 | Unlocking the Power of Tile Caching: A Comprehensive Guide | EN-05 | <code>plays a crucial role</code> | Importance asserted instead of shown |\n| 5:95 | Unlocking the Power of Tile Caching: A Comprehensive Guide | EN-12 | <code>Let's dive</code> | Signposted dive instead of starting |\n| 5:138 | Unlocking the Power of Tile Caching: A Comprehensive Guide | EN-03 | <code>leverage</code> | Inflated verb where a plain one says the same |\n| 5:168 | Unlocking the Power of Tile Caching: A Comprehensive Guide | EN-04 | <code>seamless</code> | Promotional adjective with no measurable content |\n| 5:190 | Unlocking the Power of Tile Caching: A Comprehensive Guide | EN-15 | <code>whether you're a seasoned engineer or</code> | Audience-widening 'whether you're X or Y' |\n| 21:1 | Key Settings | EN-06 | <code>It's important to note</code> | Throat-clearing before the actual point |\n| 21:37 | Key Settings | EN-10 | <code>isn't just</code> | Reflexive 'not X but Y' contrast |\n| 21:118 | Key Settings | EN-09 | <code>Moreover,</code> | Essay connective stacking paragraphs mechanically |\n| 21:130 | Key Settings | EN-04 | <code>robust</code> | Promotional adjective with no measurable content |\n| 21:157 | Key Settings | EN-13 | <code>underscores</code> | Significance verb that adds no information |\n| 25:1 | Conclusion | EN-08 | <code>In conclusion,</code> | Formulaic wrap-up that restates the body |\n| 25:40 | Conclusion | EN-16 | <code>can potentially</code> | Stacked hedge |\n| 25:136 | Conclusion | ART-03 | <code>I hope this helps</code> | Chat reply closer addressed to whoever asked |\n\n### Density across the document\n\n| Rule | Measure (limit) | What it is |\n|---|---|---|\n| DEN-01 | <code>bold_per_1000=3.15 (max 3.0)</code> | Too much bold: emphasis on everything is emphasis on nothing |\n| DEN-02 | <code>dash_per_1000=2.1 (max 1.5)</code> | Em-dash habit |\n| DEN-03 | <code>exclaim_ratio=0.14 (max 0.05)</code> | Exclamation marks in expository text |\n| DEN-04 | <code>boldlead_items=3 (max 2)</code> | Bullet lists of '**Label**: explanation' |\n\n### Where to read for perspectives\n\nCues are not hits. They name lines where a content or structural perspective probably applies (`reference/content.md`, `reference/structure.md`).\n\n| Line | Section | Perspective | Why | Line text |\n|---:|---|---|---|---|\n| 3 | Unlocking the Power of Tile Caching: A Comprehensive Guide | STR-13 Uniform rhythm | 4 of 5 paragraphs have 2 sentences | <code>Certainly! Here's a revised overview of caching in `tilecache`.</code> |\n| 23 | Conclusion | STR-02 Closing that restates the body | the last section is a summary by name | <code>## Conclusion</code> |\n"
      },
      "after_scan": {
        "lang": "en",
        "genre": "general",
        "metrics": {
          "chars": 229,
          "sentences": 4,
          "bold_per_1000": 0.0,
          "dash_per_1000": 0.0,
          "exclaim_ratio": 0.0,
          "boldlead_items": 0,
          "heading_per_1000": 4.366812227074236,
          "list_ratio": 0,
          "ending_run": 1,
          "length_cv": null,
          "triad_count": 1,
          "hr_count": 0
        },
        "hits": [],
        "cues": [],
        "summary": {
          "files": 1,
          "total": 0,
          "open": 0,
          "exempt": 0,
          "by_rule": {},
          "cues": 0
        },
        "diagnosis": "# deslop diagnosis\n\n1 documents, 0 hits: **0 open**, 0 exempt; 0 perspective cues.\n\n| Document | Genre | Language | Prose chars | Open | Exempt | Cues |\n|---|---|---|---:|---:|---:|---:|\n| <code>input.md</code> | general | en | 229 | 0 | 0 | 0 |\n\n## <code>input.md</code>\n\nGeneral prose (`general`), en, 229 prose characters in 4 sentences.\n\nNo hits and no cues.\n"
      }
    },
    "ja_review": {
      "id": "ja_review",
      "label": "日本語：社内技術記事 (corpus/article/code-review-ja.md)",
      "shortLabel": "corpus/article/code-review-ja.md",
      "lang": "ja",
      "genre": "article",
      "before": "# チームでコードレビューを効率化する方法\n\n## はじめに\n\nコードレビューはソフトウェア開発において、品質向上とナレッジ共有に欠かせない重要なプロセスです。しかし、多くのチームではレビューに時間がかかりすぎたり、レビュー担当者に負荷が集中したりする問題を抱えています。本記事では、チーム全体でコードレビューを効率化するための実践的な方法をご紹介します。\n\n## 1. プルリクエストのサイズを小さく保つ\n\n効率的なレビューの第一歩は、プルリクエスト（PR）のサイズを適切に管理することです。\n\n### なぜ小さいPRが重要か\n\n- **レビューの質が向上する**：変更範囲が小さいと、レビュアーが細部まで確認しやすくなります\n- **フィードバックが早い**：小さなPRはすぐにレビューでき、開発サイクルが加速します\n- **マージ時の競合が減る**：小さな変更は他のブランチとの競合が少なくなります\n\n### 実践方法\n\n一般的には、1つのPRで変更する行数を200〜400行程度に抑えることが推奨されています。大きな機能開発の場合は、以下のように分割することを検討してください：\n\n- データモデルの変更\n- ビジネスロジックの実装\n- UIの実装\n- テストの追加\n\n## 2. 明確なレビュー基準を設定する\n\nチーム内でレビューの基準が曖昧だと、レビュアーによって指摘内容がばらつき、時間の無駄が生まれます。\n\n### チェックリストの作成\n\n以下のような項目をチームで合意しておくと効果的です：\n\n1. **機能要件**：実装が仕様を満たしているか\n2. **コード品質**：命名規則、可読性、重複がないか\n3. **テスト**：適切なテストが含まれているか\n4. **セキュリティ**：脆弱性がないか\n5. **パフォーマンス**：明らかな性能問題がないか\n\n### 指摘の優先度を明示する\n\nコメントに優先度をつけることで、作成者が対応すべき内容を判断しやすくなります。\n\n- **[must]**：マージ前に必ず修正が必要\n- **[should]**：修正が望ましい\n- **[nits]**：細かい指摘（任意対応）\n- **[question]**：質問や確認事項\n\n## 3. 自動化ツールを積極的に活用する\n\n人間がレビューすべきでない部分は、ツールに任せることでレビューの負担を大幅に軽減できます。\n\n### 導入すべきツール\n\n- **リンター・フォーマッター**：ESLint、Prettier、Black などでコードスタイルを自動統一\n- **静的解析**：SonarQube などで潜在的なバグや脆弱性を検出\n- **CI/CD**：GitHub Actions などでテストを自動実行\n- **AIレビューツール**：初期段階の指摘を自動化\n\nこれにより、レビュアーはロジックや設計といった本質的な部分に集中できるようになります。\n\n## 4. レビューのプロセスを最適化する\n\n### レビュー担当者のローテーション\n\n特定のメンバーにレビューが集中すると、ボトルネックが発生します。CODEOWNERSファイルの活用や、ランダムアサインの仕組みを導入して負荷を分散させましょう。\n\n### レビューの時間を確保する\n\n「レビューは空いた時間にやる」という考え方では、レビュー待ちが長期化しがちです。1日の中でレビュー専用の時間帯を設けるなど、チームとしてルール化することが大切です。\n\n### SLAを設定する\n\n「PRが出されてから24時間以内に初回レビューを行う」といった目標を設定すると、レビュー待ちの時間を短縮できます。\n\n## 5. PRの説明を充実させる\n\nレビュアーがコードの意図を理解するのに時間がかかると、レビュー全体が遅れます。PRテンプレートを用意し、以下の情報を記載するようにしましょう。\n\n- 変更の目的・背景\n- 変更内容の概要\n- 動作確認の方法\n- スクリーンショット（UI変更の場合）\n- レビューで特に見てほしいポイント\n\n## 6. 建設的なコミュニケーションを心がける\n\n効率化は技術的な側面だけではありません。心理的安全性の高いコミュニケーションも重要です。\n\n- 否定ではなく提案の形でコメントする（例：「〜した方が良いと思います」）\n- 良い点も積極的に褒める\n- 複雑な議論はテキストではなく、口頭やペアプログラミングで解決する\n\n## まとめ\n\nコードレビューの効率化には、以下のポイントが重要です。\n\n- PRを小さく保つ\n- レビュー基準を明確にする\n- 自動化ツールを活用する\n- レビュープロセスを最適化する\n- PRの説明を充実させる\n- 建設的なコミュニケーションを心がける\n\nこれらの取り組みは一度にすべて導入する必要はありません。チームの状況に合わせて、できるところから少しずつ改善していきましょう。効率的なコードレビューは、開発スピードと品質の両立を実現し、チーム全体の成長にもつながります。\n",
      "after": null,
      "preserved": [
        {
          "kind": "number",
          "value": "200〜400行"
        },
        {
          "kind": "number",
          "value": "24時間以内"
        },
        {
          "kind": "inline_code",
          "value": "CODEOWNERS"
        }
      ],
      "dropped_stats": [],
      "before_scan": {
        "lang": "ja",
        "genre": "article",
        "metrics": {
          "chars": 1728,
          "sentences": 22,
          "bold_per_1000": 9.25925925925926,
          "dash_per_1000": 0.0,
          "exclaim_ratio": 0.0,
          "boldlead_items": 16,
          "heading_per_1000": 9.837962962962964,
          "list_ratio": 0.6938775510204082,
          "ending_run": 1,
          "length_cv": 0.23824643467712928,
          "triad_count": 0,
          "hr_count": 0
        },
        "hits": [
          {
            "line": 1,
            "col": 1,
            "rule": "DEN-01",
            "tier": "density",
            "text": "bold_per_1000=9.26 (max 1.5)",
            "context": "document",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Too much bold: emphasis on everything is emphasis on nothing"
          },
          {
            "line": 1,
            "col": 1,
            "rule": "DEN-04",
            "tier": "density",
            "text": "boldlead_items=16 (max 0)",
            "context": "document",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Bullet lists of '**Label**: explanation'"
          },
          {
            "line": 1,
            "col": 1,
            "rule": "DEN-05",
            "tier": "density",
            "text": "heading_per_1000=9.84 (max 3.0)",
            "context": "document",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "A heading for every few sentences"
          },
          {
            "line": 1,
            "col": 1,
            "rule": "DEN-06",
            "tier": "density",
            "text": "list_ratio=0.69 (max 0.3)",
            "context": "document",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Most of the document is bullets"
          },
          {
            "line": 1,
            "col": 1,
            "rule": "DEN-08",
            "tier": "density",
            "text": "length_cv=0.24 (min 0.3)",
            "context": "document",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "Every sentence the same length"
          },
          {
            "line": 5,
            "col": 105,
            "rule": "JA-08",
            "tier": "lexical",
            "text": "本記事では、チーム全体でコードレビューを効率化するための実践的な方法をご紹介します",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "これから書く内容の予告"
          },
          {
            "line": 94,
            "col": 1,
            "rule": "JA-09",
            "tier": "lexical",
            "text": "## まとめ",
            "context": "heading",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "本文を繰り返すだけの締め"
          },
          {
            "line": 96,
            "col": 22,
            "rule": "JA-03",
            "tier": "lexical",
            "text": "が重要です",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "重要さを示さずに宣言する"
          }
        ],
        "cues": [],
        "summary": {
          "files": 1,
          "total": 8,
          "open": 8,
          "exempt": 0,
          "by_rule": {
            "DEN-01": 1,
            "DEN-04": 1,
            "DEN-05": 1,
            "DEN-06": 1,
            "DEN-08": 1,
            "JA-03": 1,
            "JA-08": 1,
            "JA-09": 1
          },
          "cues": 0
        },
        "diagnosis": "# deslop diagnosis\n\n1 documents, 8 hits: **8 open**, 0 exempt; 0 perspective cues.\n\nHits are candidates read in context, not verdicts. Most are fixed by deleting the sentence or word; see `reference/patterns.md` for each rule.\n\n| Document | Genre | Language | Prose chars | Open | Exempt | Cues |\n|---|---|---|---:|---:|---:|---:|\n| <code>input.md</code> | article | ja | 1,728 | 8 | 0 | 0 |\n\n## <code>input.md</code>\n\nBlog / article (`article`), ja, 1,728 prose characters in 22 sentences.\n\n### Open hits by section\n\nMost frequent: JA-08 ×1, JA-09 ×1, JA-03 ×1.\n\n| Line | Section | Rule | Text | What it is |\n|---:|---|---|---|---|\n| 5:105 | はじめに | JA-08 | <code>本記事では、チーム全体でコードレビューを効率化するための実践的な方法をご紹介します</code> | これから書く内容の予告 |\n| 94:1 | まとめ | JA-09 | <code>## まとめ</code> | 本文を繰り返すだけの締め |\n| 96:22 | まとめ | JA-03 | <code>が重要です</code> | 重要さを示さずに宣言する |\n\n### Density across the document\n\n| Rule | Measure (limit) | What it is |\n|---|---|---|\n| DEN-01 | <code>bold_per_1000=9.26 (max 1.5)</code> | Too much bold: emphasis on everything is emphasis on nothing |\n| DEN-04 | <code>boldlead_items=16 (max 0)</code> | Bullet lists of '**Label**: explanation' |\n| DEN-05 | <code>heading_per_1000=9.84 (max 3.0)</code> | A heading for every few sentences |\n| DEN-06 | <code>list_ratio=0.69 (max 0.3)</code> | Most of the document is bullets |\n| DEN-08 | <code>length_cv=0.24 (min 0.3)</code> | Every sentence the same length |\n"
      }
    },
    "ja_cli_ref": {
      "id": "ja_cli_ref",
      "label": "日本語：CLIリファレンス (corpus/reference/deploy-cli-reference-ja.md)",
      "shortLabel": "corpus/reference/deploy-cli-reference-ja.md",
      "lang": "ja",
      "genre": "reference",
      "before": "**注意:** 作業ディレクトリは空で、`shipit` もインストールされていないため、実際の仕様は確認できていません。以下のオプション名・デフォルト値・終了コードは一般的なデプロイ CLI を参考にした**仮の内容**です。公開前に、`shipit deploy --help` またはソースと照らし合わせてください。照合が必要な箇所には HTML コメントで `#TODO` を入れてあります（Markdown の表示には出ません）。\n\n---\n\n<!-- #TODO(agent): 全オプション名・デフォルト値・終了コードを shipit の実装と照合する（仮仕様で作成） -->\n\n# shipit deploy\n\n指定したアプリケーションを、対象の環境へデプロイします。\n\n## 書式\n\n```\nshipit deploy [OPTIONS] <APP>\n```\n\n## 説明\n\n`shipit deploy` はアプリケーション `<APP>` のビルド成果物を、指定した環境へリリースします。デプロイは次の順で進みます。\n\n1. 事前チェック（認証、対象環境の状態、デプロイロックの有無）\n2. 成果物の取得（`--ref` で指定したリビジョン、または `--image` で指定したイメージ）\n3. ロールアウト（`--strategy` に従う）\n4. ヘルスチェック\n5. 失敗した場合は自動でロールバック（`--no-rollback` を指定した場合を除く）\n\n本番環境（`production`）へデプロイするときは、`--yes` を指定しない限り確認プロンプトが表示されます。\n\n## 引数\n\n| 引数 | 説明 |\n|---|---|\n| `<APP>` | デプロイするアプリケーション名。`shipit apps list` で確認できます。 |\n\n## オプション\n\n| オプション | 短縮形 | 値 | デフォルト | 説明 |\n|---|---|---|---|---|\n| `--env` | `-e` | `<ENV>` | `staging` | デプロイ先の環境（`development` / `staging` / `production`）。 |\n| `--ref` | `-r` | `<GIT_REF>` | `main` の最新コミット | デプロイするブランチ、タグ、またはコミット SHA。 |\n| `--image` | | `<IMAGE>` | なし | ビルド済みのコンテナイメージを直接指定します。`--ref` とは同時に指定できません。 |\n| `--strategy` | `-s` | `rolling` \\| `blue-green` \\| `canary` | `rolling` | ロールアウトの方式。 |\n| `--canary-percent` | | `<1-100>` | `10` | `--strategy canary` のとき、最初にトラフィックを流す割合。 |\n| `--timeout` | `-t` | `<DURATION>` | `10m` | デプロイ全体のタイムアウト（例: `30s`、`5m`、`1h`）。 |\n| `--dry-run` | `-n` | | `false` | 実際には変更せず、実行予定の内容だけを表示します。 |\n| `--yes` | `-y` | | `false` | 確認プロンプトを省略します。CI での利用を想定しています。 |\n| `--no-rollback` | | | `false` | 失敗しても自動ロールバックを行いません。 |\n| `--force` | `-f` | | `false` | デプロイロックや凍結期間を無視して実行します。権限が必要です。 |\n| `--message` | `-m` | `<TEXT>` | なし | デプロイ履歴と通知に記録するメモ。 |\n| `--wait` / `--no-wait` | | | `--wait` | ヘルスチェックの完了まで待つかどうか。 |\n| `--output` | `-o` | `text` \\| `json` | `text` | 出力形式。 |\n| `--verbose` | `-v` | | `false` | 詳細なログを出力します。 |\n| `--help` | `-h` | | | ヘルプを表示します。 |\n\n## 環境変数\n\n| 変数 | 説明 |\n|---|---|\n| `SHIPIT_TOKEN` | API 認証トークン。設定がない場合は `shipit login` で保存した認証情報を使います。 |\n| `SHIPIT_ENV` | `--env` のデフォルト値を上書きします。 |\n\nコマンドラインのオプションは、環境変数より優先されます。\n\n## 使用例\n\nステージング環境へ `main` の最新版をデプロイする:\n\n```sh\nshipit deploy api\n```\n\n特定のタグを本番環境へデプロイする:\n\n```sh\nshipit deploy api --env production --ref v2.4.1\n```\n\n実行内容を事前に確認する（ドライラン）:\n\n```sh\nshipit deploy api --env production --ref v2.4.1 --dry-run\n```\n\nカナリア方式で、最初に 5% のトラフィックだけを流す:\n\n```sh\nshipit deploy web -e production -s canary --canary-percent 5\n```\n\nCI から確認なしで実行し、結果を JSON で受け取る:\n\n```sh\nshipit deploy worker -e production -r \"$GIT_SHA\" --yes --output json -m \"CI build #$BUILD_ID\"\n```\n\nビルド済みのイメージを指定してデプロイする:\n\n```sh\nshipit deploy api -e staging --image registry.example.com/api:2024-11-01\n```\n\n## 終了コード\n\n| コード | 意味 |\n|---|---|\n| `0` | 成功。`--dry-run` の場合は、計画の作成に成功したことを示します。 |\n| `1` | 一般的なエラー（想定外のエラー）。 |\n| `2` | 引数またはオプションが不正（例: `--ref` と `--image` を同時に指定した）。 |\n| `3` | 認証エラー、または権限不足。 |\n| `4` | 事前チェックで失敗（デプロイロック中、凍結期間中、対象のリビジョンが見つからない、など）。 |\n| `5` | デプロイに失敗し、自動ロールバックに成功した。 |\n| `6` | デプロイに失敗し、ロールバックにも失敗した、または `--no-rollback` が指定されていた。**手動での対応が必要です。** |\n| `7` | タイムアウト（`--timeout` を超えた）。 |\n| `130` | ユーザーが中断した（Ctrl+C）、または確認プロンプトで拒否した。 |\n\n## 関連項目\n\n- `shipit rollback` — 直前のリリースに戻す\n- `shipit status` — 環境ごとのデプロイ状況を表示する\n- `shipit history` — デプロイ履歴を表示する\n",
      "after": null,
      "preserved": [
        {
          "kind": "inline_code",
          "value": "shipit deploy [OPTIONS] <APP>"
        },
        {
          "kind": "inline_code",
          "value": "--canary-percent"
        },
        {
          "kind": "number",
          "value": "終了コード 0〜7, 130"
        }
      ],
      "dropped_stats": [],
      "before_scan": {
        "lang": "ja",
        "genre": "reference",
        "metrics": {
          "chars": 878,
          "sentences": 9,
          "bold_per_1000": 3.4168564920273345,
          "dash_per_1000": 3.4168564920273345,
          "exclaim_ratio": 0.0,
          "boldlead_items": 0,
          "heading_per_1000": 10.250569476082005,
          "list_ratio": 0.38095238095238093,
          "ending_run": 1,
          "length_cv": 0.36496535240322536,
          "triad_count": 0,
          "hr_count": 1
        },
        "hits": [
          {
            "line": 1,
            "col": 1,
            "rule": "DEN-01",
            "tier": "density",
            "text": "bold_per_1000=3.42 (max 3.0)",
            "context": "document",
            "path": "input.md",
            "exempt": true,
            "exempt_by": "genre",
            "exempt_reason": "API / reference: parameter and option names are bold",
            "note": "Too much bold: emphasis on everything is emphasis on nothing"
          },
          {
            "line": 1,
            "col": 49,
            "rule": "JA-33",
            "tier": "lexical",
            "text": "仕様は確認できていません",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "生成モデル自身の断り書き（未確認・仮定・参考にした一般例）"
          },
          {
            "line": 1,
            "col": 85,
            "rule": "JA-33",
            "tier": "lexical",
            "text": "一般的なデプロイ CLI を参考にした",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "生成モデル自身の断り書き（未確認・仮定・参考にした一般例）"
          },
          {
            "line": 1,
            "col": 106,
            "rule": "JA-33",
            "tier": "lexical",
            "text": "仮の内容",
            "context": "prose",
            "path": "input.md",
            "exempt": false,
            "exempt_reason": null,
            "note": "生成モデル自身の断り書き（未確認・仮定・参考にした一般例）"
          }
        ],
        "cues": [],
        "summary": {
          "files": 1,
          "total": 4,
          "open": 3,
          "exempt": 1,
          "by_rule": {
            "JA-33": 3
          },
          "cues": 0
        },
        "diagnosis": "# deslop diagnosis\n\n1 documents, 4 hits: **3 open**, 1 exempt; 0 perspective cues.\n\nHits are candidates read in context, not verdicts. Most are fixed by deleting the sentence or word; see `reference/patterns.md` for each rule.\n\n| Document | Genre | Language | Prose chars | Open | Exempt | Cues |\n|---|---|---|---:|---:|---:|---:|\n| <code>input.md</code> | reference | ja | 878 | 3 | 1 | 0 |\n\n## <code>input.md</code>\n\nAPI / reference (`reference`), ja, 878 prose characters in 9 sentences.\n\n### Open hits by section\n\nMost frequent: JA-33 ×3.\n\n| Line | Section | Rule | Text | What it is |\n|---:|---|---|---|---|\n| 1:49 | (before the first heading) | JA-33 | <code>仕様は確認できていません</code> | 生成モデル自身の断り書き（未確認・仮定・参考にした一般例） |\n| 1:85 | (before the first heading) | JA-33 | <code>一般的なデプロイ CLI を参考にした</code> | 生成モデル自身の断り書き（未確認・仮定・参考にした一般例） |\n| 1:106 | (before the first heading) | JA-33 | <code>仮の内容</code> | 生成モデル自身の断り書き（未確認・仮定・参考にした一般例） |\n\n<details><summary>Exempt hits (1)</summary>\n\n| Line | Rule | Text | Reason |\n|---:|---|---|---|\n| 1:1 | DEN-01 | <code>bold_per_1000=3.42 (max 3.0)</code> | API / reference: parameter and option names are bold |\n\n</details>\n"
      }
    }
  }
};
