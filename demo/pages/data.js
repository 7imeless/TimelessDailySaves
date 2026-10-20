/* Demo data shared by the secondary pages. No backend involved. */

window.TL_POSTS = [
  {
    id: 'cache',
    category: '工程实践',
    date: '2026-10-12',
    title: '缓存失效之后：一次关于“新鲜感”的系统思考',
    excerpt: '一个缓存 key 没有失效，整个首页却像失去了记忆。从一次线上事故出发，聊聊缓存、认知，以及我们为什么总会忘记更新。',
    minutes: 8,
    tags: ['系统设计', '缓存', '写作'],
    href: 'article.html'
  },
  {
    id: 'slow-query',
    category: '随笔',
    date: '2026-09-18',
    title: '把写作当成一次慢查询',
    excerpt: '不急着给结论，让问题在草稿里多待一会儿。写作和查库一样，慢一点，才看得见真正昂贵的部分。',
    minutes: 5,
    tags: ['写作', '注意力']
  },
  {
    id: 'best-practice',
    category: '前端',
    date: '2026-08-24',
    title: '当我不再追逐“最佳实践”',
    excerpt: '工具会变，但判断问题的方式可以留下。比起记住答案，我更想保留提问的顺序。',
    minutes: 6,
    tags: ['前端', '工程']
  },
  {
    id: 'design-defaults',
    category: '读书',
    date: '2026-07-16',
    title: '读《设计心理学》：好的默认值',
    excerpt: '少一个选择，有时就是多一点自由。好的默认值不替人做决定，它只是让正确的路更容易走。',
    minutes: 4,
    tags: ['设计', '阅读']
  },
  {
    id: 'observability',
    category: '工程实践',
    date: '2026-06-08',
    title: '把“可观测”从口号变成习惯',
    excerpt: '日志、指标和那些真正需要被看见的信号。可观测不是多接一块大屏，而是先想清楚要回答什么问题。',
    minutes: 9,
    tags: ['系统设计', '可观测性']
  },
  {
    id: 'workflow',
    category: '工具',
    date: '2026-05-21',
    title: '从一张便签到一套工具',
    excerpt: '工具不是越多越好。它应该沿着你原本的动作生长，而不是要求你换一种生活。',
    minutes: 7,
    tags: ['工具', '系统设计']
  },
  {
    id: 'quiet',
    category: '随笔',
    date: '2026-04-29',
    title: '给忙碌的人留一块没有通知的地方',
    excerpt: '关于注意力、边界和一个下午的散步。不是逃离连接，而是重新决定什么时候被找到。',
    minutes: 3,
    tags: ['注意力', '生活']
  },
  {
    id: 'paper-notes',
    category: '随笔',
    date: '2026-02-06',
    title: '为什么我又开始用纸质笔记',
    excerpt: '纸张不会提醒我同步，也不会在深夜推送一条回顾。它只是安静地等一支笔。',
    minutes: 4,
    tags: ['工具', '阅读', '注意力']
  }
];

window.TL_WORDS = [
  {
    word: 'state',
    phonetic: '/steɪt/',
    translation: 'n. 状态；国家；州\nv. 陈述；说明',
    definition: 'the particular condition that someone or something is in at a specific time',
    tags: ['高频', '多义']
  },
  {
    word: 'maintain',
    phonetic: '/meɪnˈteɪn/',
    translation: 'v. 维持；维修；主张',
    definition: 'to keep something in good condition by checking or repairing it regularly',
    tags: ['动词', '维护']
  },
  {
    word: 'observe',
    phonetic: '/əbˈzɜːrv/',
    translation: 'v. 观察；遵守；评论',
    definition: 'to watch carefully the way something happens or the way someone does something',
    tags: ['动词', '观察']
  },
  {
    word: 'design',
    phonetic: '/dɪˈzaɪn/',
    translation: 'n. 设计；图案；意图\nv. 设计；筹划',
    definition: 'the way in which something is planned and made',
    tags: ['名词', '动词']
  },
  {
    word: 'default',
    phonetic: '/dɪˈfɔːlt/',
    translation: 'n. 默认值；违约\nv. 不履行；默认',
    definition: 'the thing that exists or happens if you do not change it intentionally',
    tags: ['设计', '系统']
  },
  {
    word: 'attention',
    phonetic: '/əˈtenʃn/',
    translation: 'n. 注意力；关注；照料',
    definition: 'the act of watching or listening to something carefully',
    tags: ['名词', '认知']
  },
  {
    word: 'archive',
    phonetic: '/ˈɑːrkaɪv/',
    translation: 'n. 档案；档案馆\nv. 归档；存档',
    definition: 'a collection of historical records relating to a place, organization, or family',
    tags: ['名词', '动词']
  },
  {
    word: 'refresh',
    phonetic: '/rɪˈfreʃ/',
    translation: 'v. 刷新；使恢复；更新',
    definition: 'to make someone feel less tired or less hot, or to update something',
    tags: ['动词', '缓存']
  }
];

window.TL_MONEY = [
  { id: 'm-01', date: '2026-10-01', type: 'income', category: '工资', amount: 1800000, note: '十月工资' },
  { id: 'm-02', date: '2026-10-02', type: 'expense', category: '居住', amount: 420000, note: '房租' },
  { id: 'm-03', date: '2026-10-05', type: 'expense', category: '餐饮', amount: 28650, note: '周末买菜' },
  { id: 'm-04', date: '2026-10-08', type: 'expense', category: '学习', amount: 12800, note: '《设计心理学》' },
  { id: 'm-05', date: '2026-10-10', type: 'expense', category: '交通', amount: 21000, note: '地铁充值' },
  { id: 'm-06', date: '2026-10-12', type: 'expense', category: '餐饮', amount: 4600, note: '咖啡' },
  { id: 'm-07', date: '2026-10-15', type: 'expense', category: '购物', amount: 39900, note: '耳机' },
  { id: 'm-08', date: '2026-10-18', type: 'expense', category: '娱乐', amount: 7600, note: '电影' },
  { id: 'm-09', date: '2026-10-19', type: 'expense', category: '餐饮', amount: 3200, note: '午饭' },
  { id: 'm-10', date: '2026-09-01', type: 'income', category: '工资', amount: 1800000, note: '九月工资' },
  { id: 'm-11', date: '2026-09-02', type: 'expense', category: '居住', amount: 420000, note: '房租' },
  { id: 'm-12', date: '2026-09-06', type: 'expense', category: '餐饮', amount: 31200, note: '买菜' },
  { id: 'm-13', date: '2026-09-09', type: 'expense', category: '学习', amount: 6800, note: '一本旧书' },
  { id: 'm-14', date: '2026-09-14', type: 'expense', category: '交通', amount: 21000, note: '地铁充值' },
  { id: 'm-15', date: '2026-09-21', type: 'expense', category: '购物', amount: 18900, note: '收纳盒' },
  { id: 'm-16', date: '2026-09-27', type: 'expense', category: '娱乐', amount: 12000, note: '展览' }
];

window.TL_CATEGORIES = {
  expense: ['餐饮', '交通', '购物', '居住', '娱乐', '学习', '医疗', '其他'],
  income: ['工资', '兼职', '投资', '其他']
};
