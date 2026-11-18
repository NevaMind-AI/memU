import { defineConfig } from 'vitepress'

const repository = 'https://github.com/XnneHangLab-Mirror/memU'

export default defineConfig({
  title: 'memU',
  description: 'Memory across sessions and agents',
  srcDir: 'site',
  head: [['link', { rel: 'icon', type: 'image/png', href: '/memu-icon.png' }]],
  lastUpdated: true,
  locales: {
    root: {
      label: 'English',
      lang: 'en',
      themeConfig: {
        nav: [
          { text: 'Guide', link: '/guide/getting-started' },
          { text: 'Reference', link: '/reference/configuration' },
          { text: 'Contribute', link: '/development/documentation' },
        ],
        sidebar: [
          { text: 'Start here', items: [
            { text: 'Getting started', link: '/guide/getting-started' },
            { text: 'Host adapters', link: '/hosts/' },
            { text: 'Troubleshooting', link: '/troubleshooting/' },
          ] },
          { text: 'Reference', items: [
            { text: 'Configuration', link: '/reference/configuration' },
            { text: 'MemoryService', link: '/reference/service' },
          ] },
          { text: 'Development', items: [
            { text: 'Writing documentation', link: '/development/documentation' },
            { text: 'Architecture decisions', link: `${repository}/tree/main/docs/adr` },
            { text: 'Community tasks', link: `${repository}/blob/main/docs/community/tasks.en.md` },
            { text: 'Changelog', link: `${repository}/blob/main/CHANGELOG.md` },
          ] },
        ],
      },
    },
    zh: {
      label: '简体中文',
      lang: 'zh-CN',
      description: '跨会话、跨 Agent 的共享记忆',
      themeConfig: {
        nav: [
          { text: '指南', link: '/zh/guide/getting-started' },
          { text: '参考', link: '/zh/reference/configuration' },
          { text: '参与贡献', link: '/zh/development/documentation' },
        ],
        sidebar: [
          { text: '开始使用', items: [
            { text: '快速开始', link: '/zh/guide/getting-started' },
            { text: '宿主接入', link: '/zh/hosts/' },
            { text: '故障排查', link: '/zh/troubleshooting/' },
          ] },
          { text: '参考', items: [
            { text: '配置', link: '/zh/reference/configuration' },
            { text: 'MemoryService', link: '/zh/reference/service' },
          ] },
          { text: '开发', items: [
            { text: '文档维护', link: '/zh/development/documentation' },
            { text: '架构决策', link: `${repository}/tree/main/docs/adr` },
            { text: '社区任务', link: `${repository}/blob/main/docs/community/tasks.md` },
            { text: '更新日志', link: `${repository}/blob/main/CHANGELOG.md` },
          ] },
        ],
        outline: { label: '本页目录' },
        docFooter: { prev: '上一页', next: '下一页' },
        lastUpdated: { text: '最后更新' },
        langMenuLabel: '语言',
        returnToTopLabel: '返回顶部',
        sidebarMenuLabel: '菜单',
      },
    },
  },
  themeConfig: {
    logo: { src: '/memu-logo.png', alt: 'memU' },
    siteTitle: false,
    search: { provider: 'local' },
    socialLinks: [{ icon: 'github', link: repository }],
  },
})
