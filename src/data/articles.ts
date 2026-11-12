import type { Lang } from './i18n';

export interface CatDialogue {
  speaker: 'marc' | 'suzuka' | 'naomi';
  mood?: string;
  text: string;
}

export interface ArticleSection {
  heading: string;
  body: string;
}

export interface ResultRow {
  pos: string;
  riderOrTeam: string;
  machine: string;
  timeOrNote: string;
}

export interface SnsCiteItem {
  platform: 'X' | 'YouTube' | 'OfficialWeb' | 'Facebook' | 'Instagram';
  citationType?: 'direct_post' | 'hashtag_hub' | 'official_channel' | 'official_web';
  accountName: string;
  handle: string;
  url: string;
  postUrl?: string;
  publishedDate?: string;
  quotedPostText: Record<Lang, string>;
  editorialCommentary: Record<Lang, string>;
}

export interface FactSource {
  title: string;
  url: string;
}

export interface FactCheckMeta {
  verified: boolean;
  verifiedAt: string;
  basis: Record<Lang, string>;
  sources: FactSource[];
}

export interface DiagramPanel {
  statusType: 'good' | 'bad' | 'detail';
  statusLabel: string;
  title: string;
  caption: string;
  keyMetric?: string;
  badge?: string;
}

export interface LocalizedDiagram {
  tag?: string;
  title: string;
  caption: string;
  panels: DiagramPanel[];
}

export interface LocalizedArticleContent {
  title: string;
  subtitle: string;
  summary: string;
  highlightPoint: string;
  sections: ArticleSection[];
  resultTableTitle?: string;
  results?: ResultRow[];
  catDialogues: CatDialogue[];
  diagram?: LocalizedDiagram;
}

export interface ArticleData {
  id: string;
  slug: string;
  publishedAt: string;
  category: 'world' | 'kyushu' | 'endurance-fun' | 'all-japan' | 'spotlight' | 'maintenance';
  articleType: 'preview' | 'digest' | 'spotlight' | 'maintenance';
  circuit: string;
  region: string;
  featuredCat: 'marc' | 'suzuka' | 'naomi';
  heroImage: string;
  tags: string[];
  snsCitations?: SnsCiteItem[];
  factCheck?: FactCheckMeta;
  eventMeta: {
    date: string;
    venue: Record<Lang, string>;
    weather: Record<Lang, string>;
  };
  locales: Record<Lang, LocalizedArticleContent>;
}

const articleModules = import.meta.glob('./articles/*.json', { eager: true });

export type ArticleCategory = 'world' | 'kyushu' | 'endurance-fun' | 'all-japan' | 'spotlight' | 'maintenance';

export const ALL_CATEGORIES: ArticleCategory[] = [
  'world',
  'kyushu',
  'endurance-fun',
  'all-japan',
  'spotlight',
  'maintenance'
];

export function getAllArticles(): ArticleData[] {
  const articles = Object.values(articleModules).map((mod: any) => mod.default || mod) as ArticleData[];
  return articles.sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
}

export function getArticlesByCategory(category: string): ArticleData[] {
  return getAllArticles().filter((a) => a.category === category);
}

export function getAllTags(): string[] {
  const articles = getAllArticles();
  const tagSet = new Set<string>();
  articles.forEach((a) => {
    (a.tags || []).forEach((t) => {
      const trimmed = t.trim();
      if (trimmed) tagSet.add(trimmed);
    });
  });
  return Array.from(tagSet).sort((a, b) => a.localeCompare(b, 'ja'));
}

export function getArticlesByTag(tag: string): ArticleData[] {
  const target = tag.trim().toLowerCase();
  return getAllArticles().filter((a) =>
    (a.tags || []).some((t) => t.trim().toLowerCase() === target)
  );
}
