import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Mail, Phone, MapPin, GraduationCap, Briefcase, Code2, Database, Cloud, Brain, Users } from 'lucide-react'
import Navbar from '../components/layout/Navbar'
import Footer from '../components/layout/Footer'

const stagger = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
}

const fadeUp = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: 'easeOut' as const } },
}

const skillGroups = [
  {
    icon: Code2,
    title: '编程语言 & 框架',
    color: 'bg-primary/10 text-primary',
    items: ['Python', 'C/C++14', 'Golang', 'TypeScript', 'Vue', 'React', 'RESTful API'],
  },
  {
    icon: Database,
    title: '数据 & 中间件',
    color: 'bg-accent-light text-accent',
    items: ['MySQL', 'Redis', 'MongoDB', 'Kafka', 'RabbitMQ', 'ELK', 'Nginx'],
  },
  {
    icon: Cloud,
    title: 'DevOps & 云服务',
    color: 'bg-success-light text-success',
    items: ['Docker', 'Kubernetes', 'AWS', '阿里云', 'CI/CD', 'Linux'],
  },
  {
    icon: Users,
    title: '架构设计 & 团队管理',
    color: 'bg-primary-light text-primary-hover',
    items: ['系统架构', '微服务', 'DDD', '技术负责人', '团队管理', 'Code Review'],
  },
  {
    icon: Brain,
    title: 'AI & 工具',
    color: 'bg-warning-light text-warning',
    items: ['Claude Code', 'Vibe Coding', 'Skills', 'Prompt', 'LLM API'],
  },
]

const experiences = [
  {
    role: '资深软件工程师',
    company: '路特斯汽车机器人',
    period: '2021.09 — 2025.05',
    highlights: [
      '主导 8 个项目的系统架构设计（SaaS 平台 & Web 应用），从 0 到 1 交付',
      '制定团队技术规范，设计微服务架构方案',
      '搭建并维护 DevOps 体系，支撑 20+ 个项目的持续交付',
      '开发微服务并部署至阿里云',
      '构建车辆远程控制平台服务端',
    ],
  },
  {
    role: '资深软件工程师',
    company: '奇安信科技',
    period: '2018.11 — 2021.09',
    highlights: [
      '使用 Golang & Python 构建可扩展的微服务，部署于 K8s',
      '基于 Nginx 实现 API 网关，支持负载均衡、缓存、认证和日志',
      '设计数据处理平台及 RESTful API，支撑 10K QPS',
      '带领 6 人团队，搭建 DevOps 体系，研发效率提升 20%',
    ],
  },
  {
    role: '高级软件工程师',
    company: 'BaBa-meeting（创业公司）',
    period: '2018.01 — 2018.10',
    highlights: [
      '使用 Python 和 C++ 设计 RESTful & RPC 服务',
      '基于 Docker 构建服务并部署至 AWS',
    ],
  },
  {
    role: '高级 C++ 工程师',
    company: '金山西山居',
    period: '2015.08 — 2017.12',
    highlights: [
      '实现网络游戏服务端与客户端的网络层及通信协议',
      '设计低延迟实时游戏引擎（游戏服务器、网关、IM），支持 3000 人同时在线',
      '开发自动化测试和运维工具，提升团队效率',
    ],
  },
  {
    role: 'C++ 软件工程师',
    company: '飞音游戏',
    period: '2013.04 — 2015.08',
    highlights: [
      '基于 Linux C++ 实现多人在线游戏的低延迟系统',
      '跨团队协作，按时交付高质量软件',
    ],
  },
  {
    role: '嵌入式软件工程师',
    company: '台达电子',
    period: '2011.08 — 2013.03',
    highlights: [
      '开发路由器固件及 Web 管理界面',
    ],
  },
]

export default function AboutZhPage() {
  return (
    <div className="min-h-screen flex flex-col bg-page relative">
      <div
        className="fixed inset-0 opacity-[0.4] pointer-events-none"
        style={{
          backgroundImage:
            'linear-gradient(to right, var(--rg-color-border) 1px, transparent 1px), linear-gradient(to bottom, var(--rg-color-border) 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
      />

      <Navbar />

      <main className="flex-1 relative z-[1]">
        {/* Hero */}
        <motion.section
          variants={stagger}
          initial="hidden"
          animate="show"
          className="max-w-3xl mx-auto px-5 pt-16 pb-12 md:pt-24 md:pb-16"
        >
          <motion.div variants={fadeUp} className="flex flex-col gap-4">
            <div className="flex items-baseline gap-3">
              <h1 className="font-sans text-4xl md:text-5xl font-extrabold text-primary tracking-tight leading-[1.1]">
                阮波
              </h1>
              <Link
                to="/about"
                className="text-xs font-medium text-muted-foreground hover:text-primary border border-border hover:border-primary/30 px-2 py-0.5 rounded-[var(--radius-sm)] transition-colors"
              >
                EN
              </Link>
            </div>
            <p className="font-sans text-lg text-muted-foreground leading-relaxed max-w-2xl">
              14 年软件工程经验，专注于高性能、可扩展系统的设计与实现——从游戏引擎到
              SaaS 平台，从微服务架构到 DevOps 工程化。
            </p>
            <div className="flex flex-wrap items-center gap-4 mt-1">
              <a
                href="mailto:ruanbodev@gmail.com"
                className="flex items-center gap-1.5 text-sm font-medium text-primary hover:text-primary-hover transition-colors"
              >
                <Mail size={15} />
                ruanbodev@gmail.com
              </a>
              <a
                href="tel:+8618575651049"
                className="flex items-center gap-1.5 text-sm font-medium text-primary hover:text-primary-hover transition-colors"
              >
                <Phone size={15} />
                +86-18575651049
              </a>
              <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <MapPin size={15} />
                中国
              </span>
              <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <GraduationCap size={15} />
                北京科技大学 自动化 本科 2007–2011
              </span>
            </div>
          </motion.div>
        </motion.section>

        {/* Skills */}
        <motion.section
          variants={stagger}
          initial="hidden"
          animate="show"
          className="max-w-3xl mx-auto px-5 pb-12 md:pb-16"
        >
          <motion.h2
            variants={fadeUp}
            className="font-sans text-xs font-semibold text-muted-foreground tracking-widest uppercase mb-5"
          >
            专业技能
          </motion.h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {skillGroups.map(({ icon: Icon, title, color, items }) => (
              <motion.div
                key={title}
                variants={fadeUp}
                className="flex flex-col gap-3 p-5 bg-card rounded-[var(--radius-lg)] border border-border shadow-sm"
              >
                <div className="flex items-center gap-2.5">
                  <div className={`w-8 h-8 rounded-[var(--radius-sm)] flex items-center justify-center ${color}`}>
                    <Icon size={16} />
                  </div>
                  <h3 className="font-sans text-sm font-bold text-text-primary">{title}</h3>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {items.map((item) => (
                    <span
                      key={item}
                      className="px-2 py-0.5 text-xs font-medium text-text-secondary bg-page-alt rounded-[var(--radius-sm)]"
                    >
                      {item}
                    </span>
                  ))}
                </div>
              </motion.div>
            ))}
          </div>
        </motion.section>

        {/* Experience Timeline */}
        <motion.section
          variants={stagger}
          initial="hidden"
          animate="show"
          className="max-w-3xl mx-auto px-5 pb-20 md:pb-28"
        >
          <motion.h2
            variants={fadeUp}
            className="font-sans text-xs font-semibold text-muted-foreground tracking-widest uppercase mb-5"
          >
            工作经历
          </motion.h2>
          <div className="relative">
            <div className="absolute left-[7px] top-2 bottom-2 w-px bg-border" />

            <div className="flex flex-col gap-8">
              {experiences.map(({ role, company, period, highlights }, i) => (
                <motion.div
                  key={i}
                  variants={fadeUp}
                  className="relative pl-8"
                >
                  <div className="absolute left-0 top-1.5 w-[15px] h-[15px] rounded-full border-2 border-primary bg-card" />

                  <div className="flex flex-col gap-2">
                    <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-1">
                      <div>
                        <h3 className="font-sans text-base font-bold text-text-primary">
                          {role}
                        </h3>
                        <p className="font-sans text-sm font-medium text-primary">
                          {company}
                        </p>
                      </div>
                      <span className="font-sans text-xs font-medium text-muted-foreground whitespace-nowrap flex items-center gap-1.5">
                        <Briefcase size={12} />
                        {period}
                      </span>
                    </div>
                    <ul className="flex flex-col gap-1">
                      {highlights.map((h, j) => (
                        <li
                          key={j}
                          className="font-sans text-sm text-text-secondary leading-relaxed pl-3 relative before:content-[''] before:absolute before:left-0 before:top-[9px] before:w-1 before:h-1 before:rounded-full before:bg-muted-foreground"
                        >
                          {h}
                        </li>
                      ))}
                    </ul>
                  </div>
                </motion.div>
              ))}
            </div>
          </div>
        </motion.section>
      </main>

      <Footer />
    </div>
  )
}
