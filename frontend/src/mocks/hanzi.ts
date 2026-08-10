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
    example_words: [
      ['人类', '大人', '人口', '人们'],
      ['口水', '开口', '门口', '人口'],
      ['日子', '生日', '日出', '今日'],
      ['月亮', '月光', '每月', '岁月'],
      ['山水', '山上', '高山', '山口'],
      ['水果', '喝水', '山水', '水口'],
      ['火车', '大火', '着火', '火山'],
      ['土地', '泥土', '土豆', '尘土'],
      ['木头', '树木', '木门', '木料'],
      ['金子', '金色', '五金', '金鱼'],
      ['大小', '大人', '大门', '大家'],
      ['小心', '小孩', '小时', '大小'],
      ['上面', '上班', '早上', '向上'],
      ['下面', '下雨', '下班', '下午'],
      ['中间', '中国', '中心', '空中'],
      ['天空', '今天', '天气', '每天'],
      ['孩子', '儿子', '子女', '种子'],
      ['女孩', '女人', '子女', '少女'],
      ['手指', '双手', '拍手', '手心'],
      ['脚步', '双脚', '脚下', '脚印'],
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
