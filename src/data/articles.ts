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

export interface LocalizedArticleContent {
  title: string;
  subtitle: string;
  summary: string;
  highlightPoint: string;
  sections: ArticleSection[];
  resultTableTitle?: string;
  results?: ResultRow[];
  catDialogues: CatDialogue[];
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
  factCheck?: FactCheckMeta;
  eventMeta: {
    date: string;
    venue: Record<Lang, string>;
    weather: Record<Lang, string>;
  };
  locales: Record<Lang, LocalizedArticleContent>;
}

const articleModules = import.meta.glob('./articles/*.json', { eager: true });

export function getAllArticles(): ArticleData[] {
  const articles = Object.values(articleModules).map((mod: any) => mod.default || mod) as ArticleData[];
  return articles.sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
}
