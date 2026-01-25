import type { Translations } from "./types";

export const zhCN: Translations = {
  // Locale meta
  locale: {
    localName: "中文",
  },

  // Common
  common: {
    home: "首页",
    settings: "设置",
    delete: "删除",
    openInNewWindow: "在新窗口打开",
    close: "关闭",
    more: "更多",
    search: "搜索",
    download: "下载",
    thinking: "思考",
    artifacts: "文件",
    public: "公共",
    custom: "自定义",
    notAvailableInDemoMode: "在演示模式下不可用",
    loading: "加载中...",
    code: "代码",
    preview: "预览",
  },

  // Welcome
  welcome: {
    greeting: "👋 你好，欢迎回来！",
    description:
      "欢迎使用 🦌 DeerFlow，一个完全开源的超级智能体。通过内置和\n自定义的 Skills，DeerFlow 可以帮你搜索网络、分析数据，\n还能为你生成幻灯片、网页等作品，几乎可以做任何事情。",
  },

  // Clipboard
  clipboard: {
    copyToClipboard: "复制到剪贴板",
    copiedToClipboard: "已复制到剪贴板",
    failedToCopyToClipboard: "复制到剪贴板失败",
  },

  // Input Box
  inputBox: {
    placeholder: "今天我能为你做些什么？",
    addAttachments: "添加附件",
    mode: "模式",
    flashMode: "闪速",
    flashModeDescription: "快速且高效的完成任务，但可能不够精准",
    reasoningMode: "思考",
    reasoningModeDescription: "思考后再行动，在时间与准确性之间取得平衡",
    proMode: "专业",
    proModeDescription: "思考、计划再执行，获得更精准的结果，可能需要更多时间",
    searchModels: "搜索模型...",
  },

  // Sidebar
  sidebar: {
    newChat: "新对话",
    chats: "对话",
    recentChats: "最近的对话",
    demoChats: "演示对话",
  },

  // Breadcrumb
  breadcrumb: {
    workspace: "工作区",
    chats: "对话",
  },

  // Workspace
  workspace: {
    officialWebsite: "访问 DeerFlow 官方网站",
    githubTooltip: "访问 DeerFlow 的 Github 仓库",
    settingsAndMore: "设置和更多",
    visitGithub: "在 Github 上查看 DeerFlow",
    reportIssue: "报告问题",
    contactUs: "联系我们",
    about: "关于 DeerFlow",
  },

  // Conversation
  conversation: {
    noMessages: "还没有消息",
    startConversation: "开始新的对话以查看消息",
  },

  // Chats
  chats: {
    searchChats: "搜索对话",
  },

  // Tool calls
  toolCalls: {
    moreSteps: (count: number) => `查看其他 ${count} 个步骤`,
    lessSteps: "隐藏步骤",
    executeCommand: "执行命令",
    presentFiles: "展示文件",
    needYourHelp: "需要你的协助",
    useTool: (toolName: string) => `使用 “${toolName}” 工具`,
    searchForRelatedInfo: "搜索相关信息",
    searchOnWebFor: (query: string) => `在网络上搜索 “${query}”`,
    viewWebPage: "查看网页",
    listFolder: "列出文件夹",
    readFile: "读取文件",
    writeFile: "写入文件",
    writeTodos: "更新 To-do 列表",
  },

  // Settings
  settings: {
    title: "设置",
    description: "根据你的偏好调整 DeerFlow 的界面和行为。",
    sections: {
      appearance: "外观",
      tools: "工具",
      skills: "技能",
      acknowledge: "致谢",
    },
    appearance: {
      themeTitle: "主题",
      themeDescription: "跟随系统或选择固定的界面模式。",
      system: "系统",
      light: "浅色",
      dark: "深色",
      systemDescription: "自动跟随系统主题。",
      lightDescription: "更明亮的配色，适合日间使用。",
      darkDescription: "更暗的配色，减少眩光方便专注。",
      languageTitle: "语言",
      languageDescription: "在不同语言之间切换。",
    },
    tools: {
      title: "工具",
      description: "管理 MCP 工具的配置和启用状态。",
    },
    skills: {
      title: "技能",
      description: "管理 Agent Skill 配置和启用状态。",
    },
    acknowledge: {
      emptyTitle: "致谢",
      emptyDescription: "相关的致谢信息会展示在这里。",
    },
  },
};
