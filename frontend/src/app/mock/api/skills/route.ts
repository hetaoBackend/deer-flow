export function GET() {
  return Response.json({
    skills: [
      {
        name: "frontend-design",
        description:
          "Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples include websites, landing pages, dashboards, React components, HTML/CSS layouts, or when styling/beautifying any web UI). Generates creative, polished code and UI design that avoids generic AI aesthetics.",
        license: "Complete terms in LICENSE.txt",
        category: "public",
        enabled: true,
      },
      {
        name: "pdf-processing",
        description:
          "Comprehensive PDF manipulation toolkit for extracting text and tables, creating new PDFs, merging/splitting documents, and handling forms. When Claude needs to fill in a PDF form or programmatically process, generate, or analyze PDF documents at scale.",
        license: "Proprietary. LICENSE.txt has complete terms",
        category: "public",
        enabled: true,
      },
      {
        name: "vercel-deploy",
        description:
          'Deploy applications and websites to Vercel. Use this skill when the user requests deployment actions such as "Deploy my app", "Deploy this to production", "Create a preview deployment", "Deploy and give me the link", or "Push this live". No authentication required - returns preview URL and claimable deployment link.',
        license: null,
        category: "public",
        enabled: true,
      },
      {
        name: "web-design-guidelines",
        description:
          'Review UI code for Web Interface Guidelines compliance. Use when asked to "review my UI", "check accessibility", "audit design", "review UX", or "check my site against best practices".',
        license: null,
        category: "public",
        enabled: true,
      },
      {
        name: "cartoon-generator",
        description:
          'Generate cartoon images based on a description. Use when asked to "generate a cartoon image", "create a cartoon", "draw a cartoon", or "generate a cartoon image based on a description".',
        license: null,
        category: "custom",
        enabled: true,
      },
      {
        name: "podcast-generator",
        description:
          'Generate a podcast episode based on a topic. Use when asked to "generate a podcast episode", "create a podcast episode", "generate a podcast episode based on a topic", or "generate a podcast episode based on a description".',
        license: null,
        category: "custom",
        enabled: true,
      },
      {
        name: "advanced-data-analysis",
        description:
          'Perform advanced data analysis and visualization. Use when asked to "analyze data", "visualize data", "analyze data based on a description", or "visualize data based on a description".',
        license: null,
        category: "custom",
        enabled: true,
      },
      {
        name: "3d-model-generator",
        description:
          'Generate 3D models based on a description. Use when asked to "generate a 3D model", "create a 3D model", "generate a 3D model based on a description", or "generate a 3D model based on a description".',
        license: null,
        category: "custom",
        enabled: true,
      },
    ],
  });
}
