// Mock 数据：Step 4 前端实现阶段的假数据，联调后可删除
import type { HanziCharacter, HanziLevel } from '../types/hanzi'

const NOW = '2026-07-01T00:00:00Z'

export const mockLevels: HanziLevel[] = [
  {
    id: 'lvl-1',
    name: '启蒙 · Level 1',
    description: '最基础的常用字：人、口、日、月、山、水……',
    order_index: 1,
    total: 20,
    learned: 8,
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: 'lvl-2',
    name: '启蒙 · Level 2',
    description: '巩固扩展：数字、方位、颜色',
    order_index: 2,
    total: 40,
    learned: 0,
    created_at: NOW,
    updated_at: NOW,
  },
  {
    id: 'lvl-3',
    name: '进阶 · Level 3',
    description: '日常场景：家庭、食物、动物',
    order_index: 3,
    total: 80,
    learned: 0,
    created_at: NOW,
    updated_at: NOW,
  },
]

const level1Chars = [
  '人', '口', '日', '月', '山', '水', '火', '土', '木', '金',
  '大', '小', '上', '下', '中', '天', '子', '女', '手', '足',
]

export const mockCharacters: Record<string, HanziCharacter[]> = {
  'lvl-1': level1Chars.map((char, i) => ({
    id: `char-1-${i}`,
    level_id: 'lvl-1',
    char,
    pinyin: [
      'rén', 'kǒu', 'rì', 'yuè', 'shān', 'shuǐ', 'huǒ', 'tǔ', 'mù', 'jīn',
      'dà', 'xiǎo', 'shàng', 'xià', 'zhōng', 'tiān', 'zǐ', 'nǚ', 'shǒu', 'zú',
    ][i],
    meaning: [
      '人类', '嘴巴', '太阳；天', '月亮', '山峰', '水', '火焰', '泥土', '树木', '金属',
      '大', '小', '上方', '下方', '中间', '天空', '孩子', '女性', '手', '脚',
    ][i],
    order_index: i,
    learned: i < 8,
    learned_at: i < 8 ? NOW : null,
    created_at: NOW,
    updated_at: NOW,
  })),
  'lvl-2': [],
  'lvl-3': [],
}
