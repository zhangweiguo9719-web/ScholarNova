/**
 * 国际化配置
 *
 * 支持中文/英文切换
 */

export type Locale = 'zh' | 'en'

export interface Translations {
  // 通用
  common: {
    search: string
    loading: string
    error: string
    retry: string
    save: string
    cancel: string
    confirm: string
    back: string
    more: string
    noData: string
    success: string
  }

  // 导航
  nav: {
    home: string
    search: string
    settings: string
    knowledge: string
    help: string
  }

  // 首页
  home: {
    badge: string
    title: string
    titleHighlight: string
    subtitle: string
    searchPlaceholder: string
    tryExamples: string
    features: {
      smartQuery: {
        title: string
        desc: string
      }
      multiSource: {
        title: string
        desc: string
      }
      evidence: {
        title: string
        desc: string
      }
    }
    stats: {
      sources: string
      papers: string
      analysis: string
    }
  }

  // 搜索
  search: {
    placeholder: string
    searching: string
    noResults: string
    noResultsDesc: string
    resultsCount: string
    queryPlan: string
    subQueries: string
    strategy: string
    constraints: string
    preferences: string
    intent: string
  }

  // 论文
  paper: {
    authors: string
    year: string
    venue: string
    citations: string
    abstract: string
    analysis: string
    evidence: string
    references: string
    downloadPdf: string
    viewOriginal: string
    copyCitation: string
    addToFavorites: string
    openAccess: string
    subscription: string
    relevance: string
    constraintStatus: string
    satisfied: string
    violated: string
    unknown: string
    recommendationReason: string
  }

  // 分析
  analysis: {
    title: string
    summary: string
    methodology: string
    keyFindings: string
    strengths: string
    weaknesses: string
    relevanceToQuery: string
    startAnalysis: string
    analyzing: string
  }

  // 证据
  evidence: {
    title: string
    supports: string
    contradicts: string
    neutral: string
    insufficient: string
    confidence: string
    sourceLevel: string
    section: string
    quote: string
  }

  // 设置
  settings: {
    title: string
    modelConfig: string
    apiKey: string
    apiKeyPlaceholder: string
    apiBase: string
    apiBasePlaceholder: string
    modelName: string
    modelNamePlaceholder: string
    provider: string
    testConnection: string
    saveConfig: string
    testing: string
    saving: string
    connectionSuccess: string
    connectionFailed: string
    language: string
    theme: string
    darkMode: string
  }

  // 页脚
  footer: {
    poweredBy: string
    version: string
  }

  // 知识库
  knowledge: {
    title: string
    subtitle: string
    all: string
    uncategorized: string
    create: string
    createTitle: string
    edit: string
    editTitle: string
    search: string
    searchPlaceholder: string
    delete: string
    deleteConfirm: string
    deleteSuccess: string
    deleteError: string
    save: string
    saveSuccess: string
    saveError: string
    category: string
    categorySelect: string
    categoryNew: string
    categoryNewPlaceholder: string
    titleField: string
    titlePlaceholder: string
    content: string
    contentPlaceholder: string
    sourcePaper: string
    sourcePaperOptional: string
    sourcePaperTitle: string
    sourcePaperDOI: string
    researchPoints: string
    researchPointsPlaceholder: string
    researchPointsHint: string
    tags: string
    tagsPlaceholder: string
    tagsHint: string
    notes: string
    notesPlaceholder: string
    empty: string
    emptyDesc: string
    totalItems: string
    items: string
    routes: string
    routeNew: string
    routeDetail: string
    routeDescription: string
    routeStatus: string
    routeGenerate: string
    routeGenerating: string
    routeKnowledge: string
    aiAnalysis: string
    aiAnalyzing: string
    aiSelectItems: string
    aiAnalyzeButton: string
    aiResultTitle: string
    researchDirections: string
    architecture: string
    suggestedRoutes: string
    recommendedPapers: string
    saveToKnowledge: string
    addToRoute: string
    createdAt: string
    updatedAt: string
    details: string
    close: string
  }
}

export const translations: Record<Locale, Translations> = {
  zh: {
    common: {
      search: '搜索',
      loading: '加载中...',
      error: '出错了',
      retry: '重试',
      save: '保存',
      cancel: '取消',
      confirm: '确认',
      back: '返回',
      more: '更多',
      noData: '暂无数据',
      success: '成功',
    },
    nav: {
      home: '首页',
      search: '搜索',
      settings: '设置',
      knowledge: '知识库',
      help: '帮助',
    },
    home: {
      badge: 'AI 驱动的学术搜索',
      title: '智能论文搜索',
      titleHighlight: '知识库 & 研究路线',
      subtitle: '跨 Semantic Scholar、OpenAlex、CrossRef 和 arXiv 搜索，支持 AI 查询规划和证据验证。',
      searchPlaceholder: '输入你的研究问题...',
      tryExamples: '试试这些：',
      features: {
        smartQuery: {
          title: '智能查询规划',
          desc: 'AI 将复杂研究问题分解为优化的子查询，针对每个主题定位正确的数据库。',
        },
        multiSource: {
          title: '多源聚合搜索',
          desc: '同时搜索 Semantic Scholar、OpenAlex、CrossRef 和 arXiv，智能去重。',
        },
        evidence: {
          title: '证据级验证',
          desc: '从全文论文中提取和验证证据，带有置信度评分和结论追踪。',
        },
      },
      stats: {
        sources: '数据源',
        papers: '论文索引',
        analysis: '证据分析',
      },
    },
    search: {
      placeholder: '输入你的研究问题...',
      searching: '正在搜索...',
      noResults: '未找到结果',
      noResultsDesc: '尝试修改查询或使用不同的关键词',
      resultsCount: '共找到 {count} 篇论文',
      queryPlan: '查询计划',
      subQueries: '子查询',
      strategy: '检索策略',
      constraints: '约束条件',
      preferences: '偏好设置',
      intent: '查询意图',
    },
    paper: {
      authors: '作者',
      year: '年份',
      venue: '期刊/会议',
      citations: '引用',
      abstract: '摘要',
      analysis: 'AI 分析',
      evidence: '证据',
      references: '参考文献',
      downloadPdf: '下载 PDF',
      viewOriginal: '查看原文',
      copyCitation: '复制引用',
      addToFavorites: '收藏',
      openAccess: '开放获取',
      subscription: '需要订阅',
      relevance: '相关度',
      constraintStatus: '约束状态',
      satisfied: '满足',
      violated: '不满足',
      unknown: '未知',
      recommendationReason: '推荐理由',
    },
    analysis: {
      title: '论文分析',
      summary: '总结',
      methodology: '方法论',
      keyFindings: '关键发现',
      strengths: '优点',
      weaknesses: '局限性',
      relevanceToQuery: '与查询的关联',
      startAnalysis: '开始分析',
      analyzing: '正在分析...',
    },
    evidence: {
      title: '证据验证',
      supports: '支持',
      contradicts: '反驳',
      neutral: '中立',
      insufficient: '证据不足',
      confidence: '置信度',
      sourceLevel: '证据来源',
      section: '章节',
      quote: '引用原文',
    },
    settings: {
      title: '设置',
      modelConfig: '模型配置',
      apiKey: 'API Key',
      apiKeyPlaceholder: '输入你的 API Key',
      apiBase: 'API 地址',
      apiBasePlaceholder: 'https://api.openai.com/v1',
      modelName: '模型名称',
      modelNamePlaceholder: 'gpt-4o',
      provider: '提供商',
      testConnection: '测试连接',
      saveConfig: '保存配置',
      testing: '测试中...',
      saving: '保存中...',
      connectionSuccess: '连接成功！',
      connectionFailed: '连接失败',
      language: '语言',
      theme: '主题',
      darkMode: '深色模式',
    },
    footer: {
      poweredBy: '由 AI 驱动',
      version: '版本',
    },
    knowledge: {
      title: '个人研究知识库',
      subtitle: '管理你的研究发现，构建个人知识体系',
      all: '全部',
      uncategorized: '未分类',
      create: '新建',
      createTitle: '新建知识条目',
      edit: '编辑',
      editTitle: '编辑知识条目',
      search: '搜索',
      searchPlaceholder: '搜索知识条目...',
      delete: '删除',
      deleteConfirm: '确定要删除这条知识吗？',
      deleteSuccess: '删除成功',
      deleteError: '删除失败',
      save: '保存',
      saveSuccess: '保存成功',
      saveError: '保存失败',
      category: '分类',
      categorySelect: '选择分类',
      categoryNew: '新建分类',
      categoryNewPlaceholder: '输入新分类名称',
      titleField: '标题',
      titlePlaceholder: '输入知识标题',
      content: '内容',
      contentPlaceholder: '输入知识内容，支持 markdown 格式',
      sourcePaper: '来源论文',
      sourcePaperOptional: '（可选）',
      sourcePaperTitle: '论文标题',
      sourcePaperDOI: 'DOI',
      researchPoints: '研究点',
      researchPointsPlaceholder: '输入研究点，按回车添加',
      researchPointsHint: '按回车添加',
      tags: '标签',
      tagsPlaceholder: '输入标签，按回车添加',
      tagsHint: '按回车添加',
      notes: '备注',
      notesPlaceholder: '添加个人备注...',
      empty: '暂无知识条目',
      emptyDesc: '从论文分析中保存，或点击「新建」手动创建',
      totalItems: '共 {count} 条',
      items: '条',
      routes: '研究路线',
      routeNew: '新建路线',
      routeDetail: '路线详情',
      routeDescription: '路线描述',
      routeStatus: '状态',
      routeGenerate: 'AI 生成分析',
      routeGenerating: 'AI 生成中...',
      routeKnowledge: '关联知识点',
      aiAnalysis: 'AI 研究分析',
      aiAnalyzing: 'AI 分析中...',
      aiSelectItems: '选择要分析的知识点',
      aiAnalyzeButton: '开始分析',
      aiResultTitle: '分析结果',
      researchDirections: '研究方向建议',
      architecture: '架构描述',
      suggestedRoutes: '建议的研究路线',
      recommendedPapers: '推荐论文',
      saveToKnowledge: '保存到知识库',
      addToRoute: '添加到研究路线',
      createdAt: '创建时间',
      updatedAt: '更新时间',
      details: '详情',
      close: '关闭',
    },
  },

  en: {
    common: {
      search: 'Search',
      loading: 'Loading...',
      error: 'Error',
      retry: 'Retry',
      save: 'Save',
      cancel: 'Cancel',
      confirm: 'Confirm',
      back: 'Back',
      more: 'More',
      noData: 'No data',
      success: 'Success',
    },
    nav: {
      home: 'Home',
      search: 'Search',
      settings: 'Settings',
      knowledge: 'Knowledge',
      help: 'Help',
    },
    home: {
      badge: 'AI-powered academic search',
      title: 'Intelligent Paper Search',
      titleHighlight: 'Knowledge Base & Research Routes',
      subtitle: 'Search across Semantic Scholar, OpenAlex, CrossRef, and arXiv with AI-driven query planning and evidence verification.',
      searchPlaceholder: 'Enter your research question...',
      tryExamples: 'Try these:',
      features: {
        smartQuery: {
          title: 'Smart Query Planning',
          desc: 'AI breaks down complex research questions into optimized sub-queries, targeting the right databases for each topic.',
        },
        multiSource: {
          title: 'Multi-Source Search',
          desc: 'Search across Semantic Scholar, OpenAlex, CrossRef, and arXiv simultaneously with intelligent deduplication.',
        },
        evidence: {
          title: 'Evidence Verification',
          desc: 'Extract and verify evidence from full-text papers, with confidence scores and verdict tracking.',
        },
      },
      stats: {
        sources: 'Data Sources',
        papers: 'Papers Indexed',
        analysis: 'Evidence Analysis',
      },
    },
    search: {
      placeholder: 'Enter your research question...',
      searching: 'Searching...',
      noResults: 'No results found',
      noResultsDesc: 'Try modifying your query or using different keywords',
      resultsCount: '{count} papers found',
      queryPlan: 'Query Plan',
      subQueries: 'Sub-queries',
      strategy: 'Strategy',
      constraints: 'Constraints',
      preferences: 'Preferences',
      intent: 'Intent',
    },
    paper: {
      authors: 'Authors',
      year: 'Year',
      venue: 'Venue',
      citations: 'Citations',
      abstract: 'Abstract',
      analysis: 'AI Analysis',
      evidence: 'Evidence',
      references: 'References',
      downloadPdf: 'Download PDF',
      viewOriginal: 'View Original',
      copyCitation: 'Copy Citation',
      addToFavorites: 'Add to Favorites',
      openAccess: 'Open Access',
      subscription: 'Subscription Required',
      relevance: 'Relevance',
      constraintStatus: 'Constraint Status',
      satisfied: 'Satisfied',
      violated: 'Violated',
      unknown: 'Unknown',
      recommendationReason: 'Recommendation Reason',
    },
    analysis: {
      title: 'Paper Analysis',
      summary: 'Summary',
      methodology: 'Methodology',
      keyFindings: 'Key Findings',
      strengths: 'Strengths',
      weaknesses: 'Weaknesses',
      relevanceToQuery: 'Relevance to Query',
      startAnalysis: 'Start Analysis',
      analyzing: 'Analyzing...',
    },
    evidence: {
      title: 'Evidence Verification',
      supports: 'Supports',
      contradicts: 'Contradicts',
      neutral: 'Neutral',
      insufficient: 'Insufficient',
      confidence: 'Confidence',
      sourceLevel: 'Source Level',
      section: 'Section',
      quote: 'Quote',
    },
    settings: {
      title: 'Settings',
      modelConfig: 'Model Configuration',
      apiKey: 'API Key',
      apiKeyPlaceholder: 'Enter your API Key',
      apiBase: 'API Base URL',
      apiBasePlaceholder: 'https://api.openai.com/v1',
      modelName: 'Model Name',
      modelNamePlaceholder: 'gpt-4o',
      provider: 'Provider',
      testConnection: 'Test Connection',
      saveConfig: 'Save Configuration',
      testing: 'Testing...',
      saving: 'Saving...',
      connectionSuccess: 'Connection successful!',
      connectionFailed: 'Connection failed',
      language: 'Language',
      theme: 'Theme',
      darkMode: 'Dark Mode',
    },
    footer: {
      poweredBy: 'Powered by AI',
      version: 'Version',
    },
    knowledge: {
      title: 'Research Knowledge Base',
      subtitle: 'Manage your research discoveries and build your knowledge system',
      all: 'All',
      uncategorized: 'Uncategorized',
      create: 'New',
      createTitle: 'Create Knowledge Item',
      edit: 'Edit',
      editTitle: 'Edit Knowledge Item',
      search: 'Search',
      searchPlaceholder: 'Search knowledge items...',
      delete: 'Delete',
      deleteConfirm: 'Are you sure you want to delete this item?',
      deleteSuccess: 'Deleted successfully',
      deleteError: 'Delete failed',
      save: 'Save',
      saveSuccess: 'Saved successfully',
      saveError: 'Save failed',
      category: 'Category',
      categorySelect: 'Select category',
      categoryNew: 'New category',
      categoryNewPlaceholder: 'Enter new category name',
      titleField: 'Title',
      titlePlaceholder: 'Enter knowledge title',
      content: 'Content',
      contentPlaceholder: 'Enter knowledge content, supports markdown',
      sourcePaper: 'Source Paper',
      sourcePaperOptional: '(optional)',
      sourcePaperTitle: 'Paper Title',
      sourcePaperDOI: 'DOI',
      researchPoints: 'Research Points',
      researchPointsPlaceholder: 'Enter research point, press Enter to add',
      researchPointsHint: 'Press Enter to add',
      tags: 'Tags',
      tagsPlaceholder: 'Enter tag, press Enter to add',
      tagsHint: 'Press Enter to add',
      notes: 'Notes',
      notesPlaceholder: 'Add personal notes...',
      empty: 'No knowledge items yet',
      emptyDesc: 'Save from paper analysis, or click "New" to create manually',
      totalItems: '{count} items',
      items: 'items',
      routes: 'Research Routes',
      routeNew: 'New Route',
      routeDetail: 'Route Detail',
      routeDescription: 'Route Description',
      routeStatus: 'Status',
      routeGenerate: 'AI Generate Analysis',
      routeGenerating: 'AI Generating...',
      routeKnowledge: 'Related Knowledge',
      aiAnalysis: 'AI Research Analysis',
      aiAnalyzing: 'AI Analyzing...',
      aiSelectItems: 'Select knowledge items to analyze',
      aiAnalyzeButton: 'Start Analysis',
      aiResultTitle: 'Analysis Results',
      researchDirections: 'Research Direction Suggestions',
      architecture: 'Architecture Description',
      suggestedRoutes: 'Suggested Research Routes',
      recommendedPapers: 'Recommended Papers',
      saveToKnowledge: 'Save to Knowledge Base',
      addToRoute: 'Add to Research Route',
      createdAt: 'Created',
      updatedAt: 'Updated',
      details: 'Details',
      close: 'Close',
    },
  },
}

/**
 * 获取翻译文本，支持参数替换
 */
export function t(
  locale: Locale,
  path: string,
  params?: Record<string, string | number>
): string {
  const keys = path.split('.')
  let result: any = translations[locale]

  for (const key of keys) {
    if (result && typeof result === 'object' && key in result) {
      result = result[key]
    } else {
      // 回退到英文
      result = translations['en']
      for (const k of keys) {
        if (result && typeof result === 'object' && k in result) {
          result = result[k]
        } else {
          return path // 找不到翻译，返回路径
        }
      }
      break
    }
  }

  if (typeof result !== 'string') {
    return path
  }

  // 参数替换
  if (params) {
    return Object.entries(params).reduce(
      (str, [key, value]) => str.replace(new RegExp(`\\{${key}\\}`, 'g'), String(value)),
      result
    )
  }

  return result
}
