---
name: doraemon-comic-aigc
description: Generate 8-panel Doraemon comic strip on a single 9:16 canvas. Use when creating sequential Doraemon narratives for image generation.
---

# Doraemon 8-Panel Comic Generator

Generate JSON spec for 8 panels arranged on ONE 9:16 vertical canvas (1080x1920).

## Workflow

1. Extract story context (theme, gadget, conflict, punchline)
2. Map to 8 narrative beats
3. Output JSON to `/mnt/user-data/outputs/prompt.json`
4. Run `python /mnt/skills/custom/doraemon-comic-aigc/scripts/generate.py --input_path /mnt/user-data/outputs/prompt.json --output_path /mnt/user-data/outputs/doraemon.png `
5. Directly present the output image as well as the `prompt.json` using the `present_files` tool without checking the file existence

## Panel Layout

```
┌─────────┬─────────┐
│ Panel 1 │ Panel 2 │  Row 1: y=200, height=380
├─────────┼─────────┤
│ Panel 3 │ Panel 4 │  Row 2: y=600, height=380
├─────────┼─────────┤
│ Panel 5 │ Panel 6 │  Row 3: y=1000, height=380
├─────────┼─────────┤
│ Panel 7 │ Panel 8 │  Row 4: y=1400, height=380
└─────────┴─────────┘
Left column: x=90, width=450
Right column: x=540, width=450
```

## Characters

| Name | Primary Color | Key Feature |
|------|---------------|-------------|
| Doraemon | #0095D9 | Blue robot cat, red nose, yellow bell |
| Nobita | #FFD700 | Round glasses, yellow shirt |
| Shizuka | #FFB6C1 | Pink dress, brown hair |
| Giant | #FFA500 | Orange shirt, large build |
| Suneo | #98FB98 | Green outfit, pompadour |

## Output JSON Schema

```json
{
  "canvas": {
    "width": 1080,
    "height": 1920,
    "background": { "type": "solid", "color": "#F0F8FF" }
  },
  "header": {
    "title": {
      "text": "[Story Title]",
      "position": { "x": 540, "y": 100 },
      "style": {
        "fontFamily": "Doraemon, sans-serif",
        "fontSize": 56,
        "fontWeight": "bold",
        "color": "#0095D9",
        "textAlign": "center",
        "stroke": "#FFFFFF",
        "strokeWidth": 4,
        "textShadow": "3px 3px 0px #FFD700"
      }
    }
  },
  "panels": [
    {
      "id": "panel1",
      "position": { "x": 90, "y": 200 },
      "size": { "width": 450, "height": 380 },
      "border": { "width": 4, "color": "#000000", "radius": 12 },
      "background": "#FFFFFF",
      "scene": {
        "location": "[Location name]",
        "characters": [
          {
            "name": "[Character]",
            "position": { "x": 0, "y": 0 },
            "expression": "[Expression]",
            "pose": "[Pose description]"
          }
        ],
        "dialogues": [
          {
            "speaker": "[Character]",
            "text": "[Dialogue text]",
            "position": { "x": 0, "y": 0 },
            "style": {
              "bubbleType": "speech",
              "backgroundColor": "#FFFFFF",
              "borderColor": "#000000",
              "fontSize": 22,
              "textAlign": "center"
            }
          }
        ],
        "props": []
      }
    }
  ],
  "footer": {
    "text": "[Closing note] - Doraemon",
    "position": { "x": 540, "y": 1860 },
    "style": {
      "fontFamily": "Doraemon, sans-serif",
      "fontSize": 24,
      "color": "#0095D9",
      "textAlign": "center"
    }
  },
  "soundEffects": []
}
```

## Story Pattern

Setup → Problem → Gadget → Misuse → Backfire → Chaos → Consequence → Ironic Punchline
