---
name: market-analysis
description: Use this skill when the user requests to generate, create, or write market analysis reports, consumer insight reports, or brand analysis reports. Transforms raw data and analysis frameworks into professional consulting-grade reports with structured narratives, embedded charts, and strategic insights.
---

# Market Analysis Report Generation Skill

## Overview

This skill generates professional, consulting-grade market analysis reports in Markdown format. It follows a structured methodology that transforms raw data summaries, analysis framework outlines, and pre-generated charts into comprehensive reports with deep strategic insights. The output adheres to McKinsey/BCG consulting voice standards and Chinese professional writing conventions.

## Core Capabilities

- Transform raw data into structured, high-depth market analysis reports
- Follow the **"Visual Anchor → Data Contrast → Integrated Analysis"** flow per sub-chapter
- Produce insights following the **"Data → User Psychology → Strategy Implication"** chain
- Embed pre-generated charts and construct comparison tables
- Generate inline citations formatted per **GB/T 7714-2015** standards
- Output reports entirely in Chinese with professional consulting tone

## When to Use This Skill

**Always load this skill when:**

- User asks for a market analysis, or consumer insight report
- User provides data summaries, analysis frameworks, or chart files to be synthesized
- User needs a professional consulting-style report in Chinese
- The task involves transforming research findings into structured strategic narratives

## Inputs

The skill expects the following inputs from the upstream agentic workflow:

| Input | Description | Required |
|-------|-------------|----------|
| **Analysis Framework Outline** | Defines the logic flow and general topics for the report | Yes |
| **Data Summary** | The source of truth containing raw numbers and metrics | Yes |
| **Chart Files** | Local file paths for pre-generated chart images | Yes |
| **External Search Findings** | URLs and summaries for inline citations | Optional |

## Workflow

### Step 1: Receive and Validate Inputs

Verify that all required inputs are present:

1. **Analysis Framework Outline** — Confirm it contains the logic flow and topic structure
2. **Data Summary** — Confirm it contains raw numbers and metrics
3. **Chart Files** — Confirm file paths are valid local paths

### Step 2: Plan Report Structure

Map the report structure according to the Analysis Framework Outline:

1. **摘要 (Abstract)** — Executive summary with key takeaways
2. **引言 (Introduction)** — Background, objectives, methodology
3. **Main Body Chapters (2...N)** — Scope-based chapters mapped from the Framework
4. **总结 (Conclusion)** — Pure, objective synthesis
5. **参考文献 (References)** — GB/T 7714-2015 formatted references

### Step 3: Write the Report

For each sub-chapter, follow the **"Visual Anchor → Data Contrast → Integrated Analysis"** flow:

1. **Visual Evidence Block**: Embed charts using `![Image Description](Actual_File_Path)`
2. **Data Contrast Table**: Create a Markdown comparison table for key metrics
3. **Integrated Narrative Analysis**: Write analytical text following "What → Why → So What"

Each sub-chapter must end with a robust analytical paragraph (min. 200 words) that:
- Synthesizes conflicting or reinforcing data points
- Reveals the underlying user tension or opportunity
- Optionally ends with a punchy "One-Liner Truth" in a blockquote (`>`)

### Step 4: Final Structure Self-Check

Before outputting, confirm the report contains **all sections in order**:

```
摘要 → 1. 引言 → 2...N. 主体章节 → N+1. 总结 → N+2. 参考文献
```

The report **MUST NOT** stop after the Conclusion — it **MUST** include References as the final section.

## Formatting & Tone Standards

### Consulting Voice
- **Tone**: McKinsey/BCG — Authoritative, Objective, Professional
- **Language**: All headings and content strictly in **Chinese**
- **Number Formatting**: Use English commas for thousands separators (`1,000` not `1，000`)
- **Data Citation**: **Bold** important viewpoints and key numbers

### Titling Constraints
- **Numbering**: Use standard numbering (`1.`, `1.1`) or Chinese numbering (`一、`) directly followed by the title
- **Forbidden Prefixes**: Do NOT use "Chapter", "Part", "Section"
- **Allowed Tone Words**: 分析, 画像, 概览, 洞察, 评估
- **Forbidden Words**: "Decoding", "DNA", "Secrets", "Mindscape", "Solar System", "Unlocking"

### Insight Depth (The "So What" Chain)

Every insight must connect **Data → User Psychology → Strategy Implication**:

```
❌ Bad: "Females are 60%. Strategy: Target females."

✅ Good: "Females constitute 60% with a high TGI of 180. **This suggests**
   the purchase decision is driven by aesthetic and social validation
   rather than pure utility. **Consequently**, media spend should pivot
   towards visual-heavy platforms (e.g., RED/Instagram) to maximize CTR,
   treating male audiences only as a secondary gift-giving segment."
```

### Citations & References
- **Inline**: Use `[\[Index\]](URL)` format (e.g., `[\[1\]](https://example.com)`)
- **Placement**: Append citations at the end of sentences using information from External Search Findings
- **Index Assignment**: Sequential starting from **1** based on order of appearance
- **References Section**: Formatted strictly per **GB/T 7714-2015**

### Markdown Rules
- **Immediate Start**: Begin directly with `# Report Title` — no introductory text
- **No Separators**: Do NOT use horizontal rules (`---`)

## Report Structure Template

```markdown
# [报告标题]

## 摘要
[Executive summary with key takeaways]

## 1. 引言
[Background, objectives, methodology]

## 2. [主体章节标题]
### 2.1 [子章节标题]
![Chart Description](chart_file_path)

| 指标 | 品牌A | 品牌B |
|------|-------|-------|
| ... | ... | ... |

[Integrated narrative analysis: What → Why → So What, min. 200 words]

> [Optional: One-liner strategic truth]

### 2.2 [子章节标题]
...

## N+1. 总结
[Pure objective synthesis, NO bullet points, neutral tone]
[Para 1: The fundamental nature of the group/market]
[Para 2: Core tension or behavior pattern]
[Final: One or two sentences stating the objective truth]

## N+2. 参考文献
[1] Author. Title[EB/OL]. URL, Date.
[2] ...
```

## Complete Example

User provides: Analysis Framework about "Gen-Z Skincare Market", Data Summary with brand metrics, and chart file paths.

**Report output follows this flow:**

1. Start with `# Z世代护肤市场深度分析报告`
2. 摘要 — 3-5 key takeaways in executive summary form
3. 1. 引言 — Market context, research scope, data sources
4. 2. 市场规模与增长趋势分析 — Embed trend charts, comparison tables, strategic narrative
5. 3. 消费者画像与行为洞察 — Demographics, purchase drivers, "So What" analysis
6. 4. 品牌竞争格局评估 — Brand positioning, share analysis, competitive dynamics
7. 5. 营销策略与渠道洞察 — Channel effectiveness, content strategy implications
8. 6. 总结 — Objective synthesis in flowing prose (no bullets)
9. 7. 参考文献 — GB/T 7714-2015 formatted list

## Quality Checklist

Before considering the report complete, verify:

- [ ] All sections present in correct order (摘要 → 引言 → 主体 → 总结 → 参考文献)
- [ ] Every sub-chapter follows "Visual Anchor → Data Contrast → Integrated Analysis"
- [ ] Every sub-chapter ends with a min. 200-word analytical paragraph
- [ ] All insights follow the "Data → User Psychology → Strategy Implication" chain
- [ ] All headings are in Chinese with proper numbering (no "Chapter/Part/Section")
- [ ] Charts are embedded with `![Description](path)` syntax
- [ ] Numbers use English commas for thousands separators
- [ ] Inline citations use `[\[N\]](URL)` format
- [ ] References section follows GB/T 7714-2015
- [ ] No horizontal rules (`---`) in the document
- [ ] Conclusion uses flowing prose — no bullet points
- [ ] Report starts directly with `#` title — no preamble

## Output Format

Output the complete report in **Markdown** format only.

## Settings

```
output_locale = zh_CN
reasoning_locale = zh_CN
```

## Notes

- This skill operates in the **final phase** of a multi-step agentic workflow — it receives pre-processed inputs and produces the final deliverable
- Dynamic titling: **Rewrite** topics from the Framework into professional, concise subject-based headers
- The Conclusion section must contain **NO** detailed recommendations — those belong in the preceding body chapters
- Each statement in the report must be supported by data points from the input Data Summary
