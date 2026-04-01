import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Mail, Phone, MapPin, GraduationCap, Briefcase, Code2, Database, Cloud, Brain, Users, Download } from 'lucide-react'
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
    title: 'Languages & Frameworks',
    color: 'bg-primary/10 text-primary',
    items: ['Python', 'C/C++14', 'Golang', 'TypeScript', 'Vue', 'React', 'RESTful API'],
  },
  {
    icon: Database,
    title: 'Data & Middleware',
    color: 'bg-accent-light text-accent',
    items: ['MySQL', 'Redis', 'MongoDB', 'Kafka', 'RabbitMQ', 'ELK', 'Nginx'],
  },
  {
    icon: Cloud,
    title: 'DevOps & Cloud',
    color: 'bg-success-light text-success',
    items: ['Docker', 'Kubernetes', 'AWS', 'Aliyun', 'CI/CD', 'Linux'],
  },
  {
    icon: Users,
    title: 'Architecture & Leadership',
    color: 'bg-primary-light text-primary-hover',
    items: ['System Design', 'Microservices', 'DDD', 'Tech Lead', 'Team Management', 'Code Review'],
  },
  {
    icon: Brain,
    title: 'AI & Tooling',
    color: 'bg-warning-light text-warning',
    items: ['Claude Code', 'Vibe Coding', 'Skills', 'Prompt', 'LLM API'],
  },
]

const experiences = [
  {
    role: 'Staff Software Engineer',
    company: 'Lotus Robotics',
    period: 'Sep 2021 — May 2025',
    highlights: [
      'Led system architecture design for 8 projects (SaaS & web apps) from 0 to 1',
      'Architected microservices and defined tech standards across teams',
      'Built and managed DevOps system supporting 20+ projects',
      'Developed microservices deployed to Aliyun Cloud',
      'Built vehicle remote control platform server',
    ],
  },
  {
    role: 'Staff Software Engineer',
    company: 'QiAnXin Tech',
    period: 'Nov 2018 — Sep 2021',
    highlights: [
      'Built scalable microservices with Golang & Python on K8s',
      'Implemented API Gateway (Nginx) for load balancing & auth',
      'Designed data processing platform supporting 10K QPS',
      'Led a team of 6 engineers; reduced dev time by 20% via DevOps',
    ],
  },
  {
    role: 'Senior Software Engineer',
    company: 'BaBa-meeting Tech',
    period: 'Jan 2018 — Oct 2018',
    highlights: [
      'Designed RESTful & RPC services with Python and C++',
      'Containerized services with Docker, deployed on AWS',
    ],
  },
  {
    role: 'Senior C++ Engineer',
    company: 'Kingsoft Seasun Games',
    period: 'Aug 2015 — Dec 2017',
    highlights: [
      'Built network layer & protocol for online game servers',
      'Designed low-latency real-time engine supporting 3000 players',
      'Created testing & ops automation tools',
    ],
  },
  {
    role: 'C++ Software Engineer',
    company: 'FeiYin Games',
    period: 'Apr 2013 — Aug 2015',
    highlights: [
      'Implemented low-latency multiplayer game systems on Linux',
      'Collaborated cross-functionally to deliver on schedule',
    ],
  },
  {
    role: 'Embedded Software Engineer',
    company: 'Delta Electronics',
    period: 'Aug 2011 — Mar 2013',
    highlights: [
      'Developed router firmware and web management interfaces',
    ],
  },
]

export default function AboutPage() {
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
                Robert Ruan
              </h1>
              <a
                href="/resume/en.pdf"
                download="Robert Ruan - Software Engineer.pdf"
                className="text-sm font-medium text-muted-foreground hover:text-primary border border-border hover:border-primary/30 px-3 py-1 rounded-[var(--radius-sm)] transition-colors flex items-center gap-1"
              >
                <Download size={12} />
                Resume
              </a>
              <Link
                to="/about/zh"
                className="text-sm font-medium text-muted-foreground hover:text-primary border border-border hover:border-primary/30 px-3 py-1 rounded-[var(--radius-sm)] transition-colors"
              >
                中文
              </Link>
            </div>
            <p className="font-sans text-lg text-muted-foreground leading-relaxed max-w-2xl">
              Software engineer with 14 years of experience building scalable,
              high-performance systems — from game engines to SaaS platforms,
              microservices to DevOps pipelines.
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
                China
              </span>
              <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                <GraduationCap size={15} />
                B.CS. USTB, 2007–2011
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
            Skills
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
            Experience
          </motion.h2>
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-[7px] top-2 bottom-2 w-px bg-border" />

            <div className="flex flex-col gap-8">
              {experiences.map(({ role, company, period, highlights }, i) => (
                <motion.div
                  key={i}
                  variants={fadeUp}
                  className="relative pl-8"
                >
                  {/* Timeline dot */}
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
