---
name: ppt-generation
description: Use this skill when the user requests to generate, create, or make presentations (PPT/PPTX). Creates visually rich slides by generating images for each slide and composing them into a PowerPoint file.
---

# PPT Generation Skill

## Overview

This skill generates professional PowerPoint presentations by creating AI-generated images for each slide and composing them into a PPTX file. The workflow includes planning the presentation structure with a consistent visual style, generating slide images sequentially (using the previous slide as a reference for style consistency), and assembling them into a final presentation.

## Core Capabilities

- Plan and structure multi-slide presentations with unified visual style
- Support multiple presentation styles: Business, Academic, Minimal, Apple Keynote, Creative
- Generate unique AI images for each slide using image-generation skill
- Maintain visual consistency by using previous slide as reference image
- Compose images into a professional PPTX file

## Presentation Styles

Choose one of the following styles when creating the presentation plan:

| Style | Description | Best For |
|-------|-------------|----------|
| **business** | Professional corporate look with clean lines, navy/blue tones, structured layouts, subtle gradients | Corporate reports, business proposals, quarterly reviews |
| **academic** | Scholarly and formal, serif fonts aesthetic, muted colors, data-focused layouts, whitespace emphasis | Research presentations, lectures, thesis defense |
| **minimal** | Ultra-clean with maximum whitespace, single accent color, simple geometric shapes, focus on content | Product launches, tech demos, modern startups |
| **keynote** | Apple-inspired aesthetic with bold typography, dramatic imagery, high contrast, cinematic feel | Keynotes, product reveals, inspirational talks |
| **creative** | Bold colors, artistic layouts, unique compositions, expressive visuals, unconventional designs | Creative pitches, design portfolios, artistic presentations |

## Workflow

### Step 1: Understand Requirements

When a user requests presentation generation, identify:

- Topic/subject: What is the presentation about
- Number of slides: How many slides are needed (default: 5-10)
- **Style**: business / academic / minimal / keynote / creative
- Aspect ratio: Standard (16:9) or classic (4:3)
- Content outline: Key points for each slide
- You don't need to check the folder under `/mnt/user-data`

### Step 2: Create Presentation Plan

Create a JSON file in `/mnt/user-data/workspace/` with the presentation structure. **Important**: Include the `style` field to define the overall visual consistency.

```json
{
  "title": "Presentation Title",
  "style": "keynote",
  "style_guidelines": {
    "color_palette": "Deep black backgrounds, white text, single accent color (blue or orange)",
    "typography": "Bold sans-serif headlines, clean body text, dramatic size contrast",
    "imagery": "High-quality photography, full-bleed images, cinematic composition",
    "layout": "Generous whitespace, centered focus, minimal elements per slide"
  },
  "aspect_ratio": "16:9",
  "slides": [
    {
      "slide_number": 1,
      "type": "title",
      "title": "Main Title",
      "subtitle": "Subtitle or tagline",
      "visual_description": "Detailed description for image generation"
    },
    {
      "slide_number": 2,
      "type": "content",
      "title": "Slide Title",
      "key_points": ["Point 1", "Point 2", "Point 3"],
      "visual_description": "Detailed description for image generation"
    }
  ]
}
```

### Step 3: Generate Slide Images Sequentially

**IMPORTANT**: Generate slides one by one, using the previous slide as a reference image to maintain visual consistency.

1. Read the image-generation skill: `/mnt/skills/public/image-generation/SKILL.md`

2. **For the FIRST slide (slide 1)**, create a prompt that establishes the visual style:

```json
{
  "prompt": "Professional presentation slide. [style_guidelines from plan]. Title: 'Your Title'. [visual_description]. This slide establishes the visual language for the entire presentation.",
  "style": "[Based on chosen style - e.g., Apple Keynote aesthetic, dramatic lighting, cinematic]",
  "composition": "Clean layout with clear text hierarchy, [style-specific composition]",
  "color_palette": "[From style_guidelines]",
  "typography": "[From style_guidelines]"
}
```

```bash
python /mnt/skills/public/image-generation/scripts/generate.py \
  --prompt-file /mnt/user-data/workspace/slide-01-prompt.json \
  --output-file /mnt/user-data/outputs/slide-01.jpg \
  --aspect-ratio 16:9
```

3. **For subsequent slides (slide 2+)**, use the PREVIOUS slide as a reference image:

```json
{
  "prompt": "Professional presentation slide continuing the visual style from the reference image. Maintain the same color palette, typography style, and overall aesthetic. Title: 'Slide Title'. [visual_description]. Keep visual consistency with the reference.",
  "style": "Match the style of the reference image exactly",
  "composition": "Similar layout principles as reference, adapted for this content",
  "color_palette": "Same as reference image",
  "consistency_note": "This slide must look like it belongs in the same presentation as the reference image"
}
```

```bash
python /mnt/skills/public/image-generation/scripts/generate.py \
  --prompt-file /mnt/user-data/workspace/slide-02-prompt.json \
  --reference-images /mnt/user-data/outputs/slide-01.jpg \
  --output-file /mnt/user-data/outputs/slide-02.jpg \
  --aspect-ratio 16:9
```

4. **Continue for all remaining slides**, always referencing the previous slide:

```bash
# Slide 3 references slide 2
python /mnt/skills/public/image-generation/scripts/generate.py \
  --prompt-file /mnt/user-data/workspace/slide-03-prompt.json \
  --reference-images /mnt/user-data/outputs/slide-02.jpg \
  --output-file /mnt/user-data/outputs/slide-03.jpg \
  --aspect-ratio 16:9

# Slide 4 references slide 3
python /mnt/skills/public/image-generation/scripts/generate.py \
  --prompt-file /mnt/user-data/workspace/slide-04-prompt.json \
  --reference-images /mnt/user-data/outputs/slide-03.jpg \
  --output-file /mnt/user-data/outputs/slide-04.jpg \
  --aspect-ratio 16:9
```

### Step 4: Compose PPT

After all slide images are generated, call the composition script:

```bash
python /mnt/skills/public/ppt-generation/scripts/generate.py \
  --plan-file /mnt/user-data/workspace/presentation-plan.json \
  --slide-images /mnt/user-data/outputs/slide-01.jpg /mnt/user-data/outputs/slide-02.jpg /mnt/user-data/outputs/slide-03.jpg \
  --output-file /mnt/user-data/outputs/presentation.pptx
```

Parameters:

- `--plan-file`: Absolute path to the presentation plan JSON file (required)
- `--slide-images`: Absolute paths to slide images in order (required, space-separated)
- `--output-file`: Absolute path to output PPTX file (required)

[!NOTE]
Do NOT read the python file, just call it with the parameters.

## Complete Example: Apple Keynote Style

User request: "Create a keynote-style presentation about the future of AI in healthcare"

### Step 1: Create presentation plan

Create `/mnt/user-data/workspace/ai-healthcare-plan.json`:
```json
{
  "title": "The Future of AI in Healthcare",
  "style": "keynote",
  "style_guidelines": {
    "color_palette": "Deep black or dark gray backgrounds, crisp white text, electric blue accent color for highlights",
    "typography": "San Francisco or Helvetica Neue inspired, bold headlines 72pt+, light body text, extreme size contrast",
    "imagery": "Cinematic photography, dramatic lighting, shallow depth of field, human-centered tech imagery",
    "layout": "Single focal point per slide, asymmetric balance, 60%+ negative space, no bullet points visible"
  },
  "aspect_ratio": "16:9",
  "slides": [
    {
      "slide_number": 1,
      "type": "title",
      "title": "The Future of AI in Healthcare",
      "subtitle": "Transforming Patient Care",
      "visual_description": "Dark cinematic background with subtle blue light rays. Large bold white title centered. Subtle medical imagery (heartbeat line, DNA helix) as abstract light trails. Apple keynote aesthetic with dramatic lighting."
    },
    {
      "slide_number": 2,
      "type": "content",
      "title": "Diagnosis Revolution",
      "key_points": ["AI detects diseases earlier", "98% accuracy in imaging", "Saves countless lives"],
      "visual_description": "Split composition: left side shows a doctor viewing a holographic medical scan, right side has the title in large white text. Dark background with blue accent lighting on the hologram. Cinematic, dramatic."
    },
    {
      "slide_number": 3,
      "type": "content",
      "title": "Personalized Medicine",
      "key_points": ["Treatment tailored to your DNA", "Predictive health insights", "AI-powered drug discovery"],
      "visual_description": "Abstract DNA double helix rendered in glowing blue light against deep black. Title overlaid in bold white. Futuristic yet human. Shallow depth of field effect."
    },
    {
      "slide_number": 4,
      "type": "content",
      "title": "Always There For You",
      "key_points": ["24/7 AI health monitoring", "Early warning systems", "Peace of mind"],
      "visual_description": "Warm scene of a smartwatch on a wrist displaying health metrics, soft bokeh background of a family moment. Emotional, human-centered. Title in white, positioned to not overlap the main image."
    },
    {
      "slide_number": 5,
      "type": "conclusion",
      "title": "The Future is Now",
      "subtitle": "",
      "visual_description": "Powerful closing image: silhouette of a healthcare worker against a sunrise/dawn sky with subtle tech elements. Hopeful, inspiring. Large bold title. Minimal, impactful."
    }
  ]
}
```

### Step 2: Read image-generation skill

Read `/mnt/skills/public/image-generation/SKILL.md` to understand how to generate images.

### Step 3: Generate slide images sequentially with reference chaining

**Slide 1 - Title (establishes the style):**

Create `/mnt/user-data/workspace/ai-healthcare-slide-01.json`:
```json
{
  "prompt": "Professional presentation title slide in Apple Keynote style. Deep black background with subtle blue light rays emanating from center. Large bold white sans-serif title 'The Future of AI in Healthcare' centered, subtitle 'Transforming Patient Care' below in lighter weight. Abstract medical elements (heartbeat line, DNA helix) as subtle glowing blue light trails. Cinematic dramatic lighting. Premium tech aesthetic. 16:9 aspect ratio presentation slide.",
  "style": "Apple Keynote presentation, premium tech aesthetic, cinematic dramatic lighting, WWDC style",
  "composition": "Centered title, 60% negative space, subtle background imagery, clear text hierarchy",
  "lighting": "Dramatic rim lighting, subtle blue accent glow, dark moody atmosphere",
  "color_palette": "Deep black background (#0a0a0a), pure white text (#ffffff), electric blue accent (#0071e3)"
}
```

```bash
python /mnt/skills/public/image-generation/scripts/generate.py \
  --prompt-file /mnt/user-data/workspace/ai-healthcare-slide-01.json \
  --output-file /mnt/user-data/outputs/ai-healthcare-slide-01.jpg \
  --aspect-ratio 16:9
```

**Slide 2 - Content (references slide 1):**

Create `/mnt/user-data/workspace/ai-healthcare-slide-02.json`:
```json
{
  "prompt": "Presentation slide continuing the exact visual style from the reference image. Same dark background, same typography style, same blue accent color. Title 'Diagnosis Revolution' in bold white on the right. Left side shows a doctor viewing a holographic medical brain scan with blue glow. Maintain the cinematic Apple Keynote aesthetic from reference. Dark premium tech look.",
  "style": "Match reference image style exactly - Apple Keynote, dark cinematic, premium",
  "composition": "Asymmetric split layout, imagery left, text right, consistent with reference aesthetic",
  "color_palette": "Exactly match the reference image colors - deep black, white text, blue accents",
  "consistency_note": "Must appear as part of the same presentation as the reference image"
}
```

```bash
python /mnt/skills/public/image-generation/scripts/generate.py \
  --prompt-file /mnt/user-data/workspace/ai-healthcare-slide-02.json \
  --reference-images /mnt/user-data/outputs/ai-healthcare-slide-01.jpg \
  --output-file /mnt/user-data/outputs/ai-healthcare-slide-02.jpg \
  --aspect-ratio 16:9
```

**Continue for slides 3-5, each referencing the previous slide...**

### Step 4: Compose final PPT

```bash
python /mnt/skills/public/ppt-generation/scripts/generate.py \
  --plan-file /mnt/user-data/workspace/ai-healthcare-plan.json \
  --slide-images /mnt/user-data/outputs/ai-healthcare-slide-01.jpg /mnt/user-data/outputs/ai-healthcare-slide-02.jpg /mnt/user-data/outputs/ai-healthcare-slide-03.jpg /mnt/user-data/outputs/ai-healthcare-slide-04.jpg /mnt/user-data/outputs/ai-healthcare-slide-05.jpg \
  --output-file /mnt/user-data/outputs/ai-healthcare-presentation.pptx
```

## Style-Specific Guidelines

### Business Style
```json
{
  "style": "business",
  "style_guidelines": {
    "color_palette": "Navy blue (#1a365d), white, light gray backgrounds, subtle gold accents",
    "typography": "Clean sans-serif (Arial, Calibri style), professional hierarchy, 44pt titles",
    "imagery": "Professional photography, office environments, handshakes, charts, clean iconography",
    "layout": "Grid-based, structured, clear sections, subtle divider lines, company branding space"
  }
}
```

### Academic Style
```json
{
  "style": "academic",
  "style_guidelines": {
    "color_palette": "White/cream backgrounds, dark navy text, burgundy or forest green accents",
    "typography": "Serif fonts (Times, Georgia style) for scholarly feel, clear hierarchy for citations",
    "imagery": "Diagrams, charts, scholarly imagery, books, research settings, data visualizations",
    "layout": "Traditional layouts, room for references, structured content areas, institution logo space"
  }
}
```

### Minimal Style
```json
{
  "style": "minimal",
  "style_guidelines": {
    "color_palette": "Pure white background, black text, single accent color (e.g., coral, teal)",
    "typography": "Thin modern sans-serif, generous letter-spacing, one font weight for body",
    "imagery": "Simple line illustrations, geometric shapes, isolated objects, vast whitespace",
    "layout": "Maximum whitespace (70%+), single element focus, extreme simplicity"
  }
}
```

### Creative Style
```json
{
  "style": "creative",
  "style_guidelines": {
    "color_palette": "Bold vibrant colors, gradients, unexpected color combinations, high saturation",
    "typography": "Mix of display and body fonts, creative text arrangements, variable sizes",
    "imagery": "Artistic photography, illustrations, collage elements, textures, hand-drawn elements",
    "layout": "Breaking the grid, overlapping elements, dynamic compositions, visual storytelling"
  }
}
```

## Output Handling

After generation:

- The PPTX file is saved in `/mnt/user-data/outputs/`
- Share the generated presentation with user using `present_files` tool
- Also share the individual slide images if requested
- Provide brief description of the presentation
- Offer to iterate or regenerate specific slides if needed

## Notes

- Always use English for image prompts regardless of user's language
- **Generate slides sequentially** - each slide must reference the previous one for consistency
- The first slide is critical - it establishes the visual language for the entire presentation
- Include style_guidelines in the prompt for every slide to maintain consistency
- The image-generation skill is a dependency - ensure it's available
- If a slide looks inconsistent, regenerate it with stronger reference to the previous slide
- For best results, be very specific about matching colors, typography, and mood in prompts
