// 法律咨询 内存 mock 后端。联调前默认启用（VITE_LEGAL_MOCK 控制）。

import type { ApiResponse } from '../types/auth'
import type {
  Citation,
  LawArticleResponse,
  LegalMessage,
  LegalMessagesResponse,
  SendMessageHandlers,
} from '../types/legalConsult'

const nowIso = () => new Date().toISOString()
const rid = () => Math.random().toString(36).slice(2, 10)
const delay = (ms: number) => new Promise((r) => setTimeout(r, ms))

const articles: Record<number, { label: string; content: string }> = {
  469: {
    label: '第四百六十九条',
    content:
      '当事人订立合同，可以采用书面形式、口头形式或者其他形式。书面形式是合同书、信件、电报、电传、传真等可以有形地表现所载内容的形式。以电子数据交换、电子邮件等方式能够有形地表现所载内容，并可以随时调取查用的数据电文，视为书面形式。',
  },
  577: {
    label: '第五百七十七条',
    content:
      '当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。',
  },
  667: {
    label: '第六百六十七条',
    content: '借款合同是借款人向贷款人借款，到期返还借款并支付利息的合同。',
  },
  675: {
    label: '第六百七十五条',
    content:
      '借款人应当按照约定的期限返还借款。对借款期限没有约定或者约定不明确，依据本法第五百一十条的规定仍不能确定的，借款人可以随时返还；贷款人可以催告借款人在合理期限内返还。',
  },
  708: {
    label: '第七百零八条',
    content:
      '出租人应当按照约定将租赁物交付承租人，并在租赁期限内保持租赁物符合约定的用途。',
  },
  710: {
    label: '第七百一十条',
    content:
      '承租人按照约定的方法或者根据租赁物的性质使用租赁物，致使租赁物受到损耗的，不承担赔偿责任。',
  },
  1087: {
    label: '第一千零八十七条',
    content:
      '离婚时，夫妻的共同财产由双方协议处理；协议不成的，由人民法院根据财产的具体情况，按照照顾子女、女方和无过错方权益的原则判决。',
  },
}

interface CannedAnswer {
  keywords: string[]
  content: string
  citations: Citation[]
}

const canned: CannedAnswer[] = [
  {
    keywords: ['押金', '租房', '房东', '退租'],
    content:
      '关键在于损耗是否属于正常使用造成的自然损耗。\n\n《民法典》第七百一十条规定，承租人按照约定的方法或者根据租赁物的性质使用租赁物，致使租赁物受到损耗的，不承担赔偿责任。日常居住产生的轻微磨损、污渍通常属于正常损耗，房东不能以此为由扣留全部押金。\n\n即使损耗超出正常使用范围，房东也只能主张与实际损失相当的修复费用，而非全额扣押押金。',
    citations: [
      { article_no: 710, label: '第七百一十条' },
      { article_no: 708, label: '第七百零八条' },
    ],
  },
  {
    keywords: ['口头', '承诺', '约定'],
    content:
      '口头约定同样具有法律效力。《民法典》第四百六十九条规定，当事人订立合同，可以采用书面形式、口头形式或者其他形式。口头达成的约定属于合同内容的一部分，对双方都有约束力。\n\n需要注意的是，口头约定的难点在于举证——聊天记录、通话录音、证人证言等都可以作为证明口头约定存在的证据。',
    citations: [{ article_no: 469, label: '第四百六十九条' }],
  },
  {
    keywords: ['借', '欠', '还钱', '借款'],
    content:
      '借款关系中，借款人负有到期返还借款的义务。\n\n《民法典》第六百七十五条规定，借款人应当按照约定的期限返还借款；若未约定还款期限，贷款人可以催告借款人在合理期限内返还。借款人到期不还的，依据第五百七十七条构成违约，应当承担继续履行、赔偿损失等违约责任。\n\n借条、转账记录、聊天记录等都是证明借款关系存在的重要证据。',
    citations: [
      { article_no: 675, label: '第六百七十五条' },
      { article_no: 667, label: '第六百六十七条' },
      { article_no: 577, label: '第五百七十七条' },
    ],
  },
  {
    keywords: ['离婚', '财产', '分割', '夫妻'],
    content:
      '离婚时的财产处理以协议优先。\n\n《民法典》第一千零八十七条规定，离婚时夫妻的共同财产由双方协议处理；协议不成的，由人民法院根据财产的具体情况，按照照顾子女、女方和无过错方权益的原则判决。\n\n也就是说，共同财产并非机械地对半分割，法院会综合考虑子女抚养、双方过错等因素作出判决。',
    citations: [{ article_no: 1087, label: '第一千零八十七条' }],
  },
]

const outOfScope =
  '抱歉，当前知识库仅覆盖《中华人民共和国民法典》。你的问题可能涉及民法典之外的领域（如刑事、税务、行政法规等），我无法给出有依据的解读。\n\n如果你的问题与合同、物权、婚姻家庭、继承、侵权等民事法律关系相关，欢迎换个方式描述，我会尽力结合民法典条文为你解读。'

let messages: LegalMessage[] = [
  {
    id: 'mock-1',
    role: 'user',
    content: '我租的房子到期了，房东以墙面有污渍为由不退我 5000 元押金，这样合理吗？',
    citations: [],
    created_at: '2026-10-23T09:30:00Z',
  },
  {
    id: 'mock-2',
    role: 'assistant',
    content: canned[0].content,
    citations: canned[0].citations,
    created_at: '2026-10-23T09:30:12Z',
  },
]

function pickAnswer(content: string): CannedAnswer | null {
  for (const c of canned) {
    if (c.keywords.some((k) => content.includes(k))) return c
  }
  return null
}

export async function getMessagesMock(): Promise<ApiResponse<LegalMessagesResponse>> {
  await delay(400)
  return { code: 0, data: { messages: [...messages] }, message: 'ok' }
}

export async function clearMessagesMock(): Promise<ApiResponse<null>> {
  await delay(300)
  messages = []
  return { code: 0, data: null, message: 'ok' }
}

export async function getArticleMock(
  articleNo: number,
): Promise<ApiResponse<LawArticleResponse>> {
  await delay(250)
  const found = articles[articleNo]
  if (!found) {
    return { code: 2010, data: null as unknown as LawArticleResponse, message: '条文不存在' }
  }
  return {
    code: 0,
    data: { article: { article_no: articleNo, label: found.label, content: found.content } },
    message: 'ok',
  }
}

export async function sendMessageMock(
  content: string,
  handlers: SendMessageHandlers,
): Promise<void> {
  const userMsg: LegalMessage = {
    id: rid(),
    role: 'user',
    content,
    citations: [],
    created_at: nowIso(),
  }
  messages.push(userMsg)

  // 模拟「模拟失败」入口，便于验证错误态
  if (content.includes('#error')) {
    await delay(800)
    handlers.onError(5001, '模型服务异常，请稍后重试')
    return
  }

  const answer = pickAnswer(content)
  const text = answer?.content ?? outOfScope
  const citations = answer?.citations ?? []

  await delay(900)
  handlers.onCitations(citations)
  await delay(300)

  for (let i = 0; i < text.length; i += 3) {
    handlers.onDelta(text.slice(i, i + 3))
    await delay(18)
  }

  const aiMsg: LegalMessage = {
    id: rid(),
    role: 'assistant',
    content: text,
    citations,
    created_at: nowIso(),
  }
  messages.push(aiMsg)
  handlers.onDone(aiMsg)
}
