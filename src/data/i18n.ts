export type Lang = 'ja' | 'ca' | 'en';

export interface CatCharacter {
  id: 'marc' | 'suzuka' | 'naoko';
  image: string;
  badgeColor: string;
  gender: { ja: string; ca: string; en: string };
  name: { ja: string; ca: string; en: string };
  role: { ja: string; ca: string; en: string };
  specialty: { ja: string; ca: string; en: string };
  bio: { ja: string; ca: string; en: string };
  quoteNormal: { ja: string; ca: string; en: string };
  quoteAlt?: {
    label: { ja: string; ca: string; en: string };
    text: { ja: string; ca: string; en: string };
  };
}

export const CAT_TEAM: Record<'marc' | 'suzuka' | 'naoko', CatCharacter> = {
  marc: {
    id: 'marc',
    image: '/images/cats/marc.png',
    badgeColor: '#e63946',
    gender: { ja: 'オス ♂', ca: 'Mascle ♂', en: 'Male ♂' },
    name: {
      ja: 'マルク (Marc)',
      ca: 'Marc (El Cap de Pàdoc)',
      en: 'Marc (Chief Paddock Editor)'
    },
    role: {
      ja: '編集長 / MotoGP・SBK・カタルーニャ担当',
      ca: 'Redactor en Cap / MotoGP, SBK i Catalunya',
      en: 'Editor-in-Chief / MotoGP, SBK & Catalunya'
    },
    specialty: {
      ja: '世界選手権・スーパーセーブ物理解説・モンメロ現地情報',
      ca: 'Mundial, física de les salvades i Circuit de Barcelona-Catalunya',
      en: 'World Championships, Super-Save Physics & Barcelona-Catalunya'
    },
    bio: {
      ja: 'バルセロナ（モンメロ）生まれの二足歩行茶トラ猫。プレスジャケットをビシッと着こなし、ストップウォッチ片手に世界グランプリから日本のサーキットまで駆け回る熱血ジャーナリスト。65度バンクからの「肘・肉球スーパーセーブ」を猫の空中姿勢制御になぞらえて解説するのが十八番。',
      ca: 'Gat tigrada bípede nascut a Montmeló (Catalunya). Sempre amb la seva jaqueta de premsa i cronòmetre en mà, connecta la passió del motociclisme català amb els circuits japonesos. Expert en analitzar "salvades impossibles" a més de 65 graus d\'inclinació.',
      en: 'Bipedal orange tabby born in Montmeló, Catalonia. Dressed in his press jacket with a stopwatch in paw, he bridges Catalan motorsport passion with Japanese racing culture. Famous for breaking down 65-degree lean angle "super saves" using feline mid-air physics.'
    },
    quoteNormal: {
      ja: '「アミーゴ！今の最終コーナー、フロントが完全に逃げてからの肘＆肉球セーブ見たかニャ！？物理法則を超えてるニャ！」',
      ca: '«Amics! Heu vist aquesta salvada amb el colze i els coixinets a l\'última corba?! Això desafia totes les lleis de la física, miau!»',
      en: '"Amigos! Did you see that front-end tuck and elbow-plus-paw save in the final corner?! That defies every law of physics, meow!"'
    }
  },
  suzuka: {
    id: 'suzuka',
    image: '/images/cats/suzuka.png',
    badgeColor: '#2a9d8f',
    gender: { ja: 'メス ♀', ca: 'Femella ♀', en: 'Female ♀' },
    name: {
      ja: 'スズカ (Suzuka)',
      ca: 'Suzuka (Reportera Nacional)',
      en: 'Suzuka (National & Kyushu Desk)'
    },
    role: {
      ja: '国内選手権＆九州サーキット特派員',
      ca: 'Corresponsal del Campionat del Japó i Circuits de Kyushu',
      en: 'All-Japan Championship & Kyushu Circuit Correspondent'
    },
    specialty: {
      ja: 'MFJ全日本ロードレース・オートポリス・SPA直入・HSR九州',
      ca: 'MFJ All-Japan, Autopolis, SPA Naoiri i HSR Kyushu',
      en: 'MFJ All-Japan Road Race, Autopolis, SPA Naoiri & HSR Kyushu'
    },
    bio: {
      ja: 'カメラマンベストを着て二足歩行でパドックを駆ける三毛猫フォトジャーナリスト。全日本ロードレースや鈴鹿8耐はもちろん、大分・熊本の九州3大サーキット（オートポリス・SPA直入・HSR九州）の地方選手権やサンデーレースを誰よりも丁寧に取材するしっかり者。',
      ca: 'Gata calicó bípede i fotoperiodista equipada amb la seva armilla i teleobjectiu. Cobreix el Campionat del Japó (MFJ) i té una passió especial pels tres grans circuits de Kyushu: Autopolis, SPA Naoiri (Oita) i HSR Kyushu (Kumamoto).',
      en: 'Bipedal calico photojournalist in a press vest toting a telephoto DSLR. She covers MFJ All-Japan Road Racing with a special focus on Kyushu’s big three circuits in Oita and Kumamoto: Autopolis, SPA Naoiri, and HSR Kyushu.'
    },
    quoteNormal: {
      ja: '「今週末のSPA直入とオートポリスは路面コンディション抜群！朝のブリーフィングから皆さんの熱い走りをバッチリ撮りますよ！」',
      ca: '«Aquest cap de setmana l\'asfalt de SPA Naoiri i Autopolis està en condicions ideals! Capturaré cada avançament des del briefing matinal!»',
      en: '"Track conditions at SPA Naoiri and Autopolis are prime this weekend! I’ll be capturing every overtake right from the morning riders’ briefing!"'
    }
  },
  naoko: {
    id: 'naoko',
    image: '/images/cats/naoko.png',
    badgeColor: '#c77dff',
    gender: { ja: 'メス ♀（やさぐれ×時々乙女）', ca: 'Femella ♀ (Rondinaire però Dolça)', en: 'Female ♀ (Scruffy Garage Queen)' },
    name: {
      ja: 'ナオコ (Naoko)',
      ca: 'Naoko (Mecànica de Garatge)',
      en: 'Naoko (Garage Mechanic & Grassroots Chief)'
    },
    role: {
      ja: '草レース・お題付き耐久＆ガレージ担当',
      ca: 'Especialista en Curses Populars, Resistència amb Reptes i Garatge',
      en: 'Grassroots Racing, "Odai" Challenge Endurance & Garage Chief'
    },
    specialty: {
      ja: 'お題付き耐久草レース・レン耐・九州草レース・キャブ＆足回り整備',
      ca: 'Resistència amb reptes (Odai-tsuki), Rentai, curses populars de Kyushu',
      en: 'Task-Challenge Endurance (Odai Endurance), Rentai & Kyushu Grassroots'
    },
    bio: {
      ja: '大分・九州のガレージに棲みつく二足歩行の黒雌猫メカニック。オイルまみれのツナギを腰巻きにし、レンチ片手に毒づく「やさぐれ姐御」だが、実は誰よりも草レーサーの安全と完走を願っている。ふとした瞬間に褒められたり甘い差し入れをもらうと、隠しきれない「乙女な一面」が漏れ出てしまうギャップの持ち主。',
      ca: 'Gata negra bípede que viu en un garatge d\'Oita amb la seva granota tacada d\'oli. Sempre rondina als pilots amateurs («No entreu tan colats a la corba!»), però en el fons té un cor tendre i quan algú li dóna les gràcies o li porta un dolç, li surt la seva faceta més romàntica i tímida.',
      en: 'Bipedal black female cat living in an Oita garage, wearing oil-stained coveralls tied at her waist. Normally a sharp-tongued, scruffy veteran mechanic who scolds grassroots riders, she secretly cares deeply—and unexpectedly blushes like a shy maiden whenever thanked or gifted local sweets.'
    },
    quoteNormal: {
      ja: '「ったく、どいつもこいつも1コーナー突っ込みすぎなんだよ！『お題付き耐久』はピットのお題でコケたら何秒削ってもパーだって言ってるだろ、この素人どもが！」',
      ca: '«Però què feu entrant tan passats al primer revolt?! A la resistència amb reptes, si falleu la prova del box perdeu tot el que heu guanyat a pista, colla d\'aficionats!»',
      en: '"Tch, every single one of you is over-cooking Turn 1! In Challenge Endurance, if you botch the pit-stop mission, shaving a second on track means nothing, you amateurs!"'
    },
    quoteAlt: {
      label: {
        ja: '🌸 ナオコの「時々出る乙女モード」を見る',
        ca: '🌸 Veure el costat tendre secret de la Naoko',
        en: '🌸 Peek at Naoko’s secret maiden side'
      },
      text: {
        ja: '「…え？ナオコさんが組んだ足回りのおかげで自己ベスト出たし、無事に完走できたって…？べ、別にあんたのために徹夜したんじゃないわよ！マシンが泣いてただけよ！…で、でも、帰りに直入のソフトクリーム奢ってくれるなら…一緒に食べてあげなくもないわよ…🌸」',
        ca: '«...Eh? Que gràcies a la meva posada a punt has fet rècord personal i has acabat la cursa sa i estalvi...? N-no és pas que m\'hagi quedat tota la nit treballant per tu! Ho he fet per la moto! ...Però bé, si em convides a un gelat tornant de Naoiri... potser sí que t\'acompanyo... 🌸»',
        en: '"...Huh? You set a personal best and finished safely thanks to my suspension setup...? I-it’s not like I stayed up all night wrenching for YOU! The bike was crying for help, that’s all! ...B-but if you’re buying Naoiri soft-serve ice cream on the way back... I suppose I wouldn’t mind sharing it with you... 🌸"'
      }
    }
  }
};

export const UI_TEXT = {
  siteTitle: {
    ja: 'HONDA.CAT — 猫たちの二輪レース情報局',
    ca: 'HONDA.CAT — El Pàdoc dels Gats del Motociclisme',
    en: 'HONDA.CAT — Feline Motorsport & Grassroots Paddock'
  },
  siteTagline: {
    ja: 'MotoGP・SBKから九州（SPA直入・オートポリス・HSR九州）＆お題付き耐久草レースまで！二足歩行の猫編集部がお届けする3カ国語レーシングメディア',
    ca: 'De MotoGP i SBK fins als circuits de Kyushu (SPA Naoiri, Autopolis, HSR) i les curses de resistència populars! Periodisme felí en català, japonès i anglès.',
    en: 'From MotoGP & SBK to Kyushu circuits (SPA Naoiri, Autopolis, HSR) and Challenge Endurance grassroots racing! Feline motorsport journalism in 3 languages.'
  },
  nav: {
    home: { ja: 'トップ', ca: 'Inici', en: 'Home' },
    articles: { ja: '最新レース記事', ca: 'Notícies i Cròniques', en: 'Race Articles' },
    kyushu: { ja: '九州サーキット＆お題耐久', ca: 'Kyushu i Resistència Popular', en: 'Kyushu & Fun Endurance' },
    cats: { ja: '猫編集部紹介', ca: 'Redacció Felina', en: 'Cat Editorial Team' },
    catalunya: { ja: '.cat カタルーニャ貢献', ca: 'Missió .cat Catalunya-Japó', en: '.cat Catalunya Mission' }
  },
  hero: {
    badge: {
      ja: '🐾 AI全自動・日/カタルーニャ/英 3言語モータースポーツメディア',
      ca: '🐾 Mitjà de Motociclisme Trilingüe (CA / JA / EN) impulsat per IA',
      en: '🐾 AI-Powered Trilingual (JA / CA / EN) Motorsport Portal'
    },
    title: {
      ja: '世界グランプリの肘セーブも、九州の熱い草耐久も。猫たちが全部追いかける。',
      ca: 'Des de les salvades de MotoGP fins a les curses populars de Kyushu: els nostres gats ho viuen tot.',
      en: 'From World GP Elbow Saves to Kyushu Grassroots Endurance: Our Paddock Cats Cover It All.'
    },
    subtitle: {
      ja: 'カタルーニャ（モンメロ）と日本（大分・SPA直入、オートポリス、熊本・HSR九州、そして全国サーキット）を繋ぐ二輪レース情報サイト。今週の開催情報、リザルト、スーパーセーブ、そして笑いと涙の「お題付き耐久草レース」まで毎日発信！',
      ca: 'Un pont entre Catalunya (Montmeló) i el Japó (Oita SPA Naoiri, Autopolis, Kumamoto HSR Kyushu i tot el país). Previews setmanals, resultats, salvades espectaculars i les divertides curses de resistència amb reptes!',
      en: 'Bridging Catalonia (Montmeló) and Japan (Oita’s SPA Naoiri, Autopolis, Kumamoto’s HSR Kyushu & nationwide tracks). Weekly race previews, results, super saves, and hilarious "Odai" task-challenge endurance races!'
    },
    ctaPrimary: {
      ja: '🏁 最新レース記事を読む',
      ca: '🏁 Llegir les últimes cròniques',
      en: '🏁 Read Latest Race Reports'
    },
    ctaSecondary: {
      ja: '🔧 九州サーキット＆お題耐久特設へ',
      ca: '🔧 Especial Kyushu i Resistència Popular',
      en: '🔧 Explore Kyushu & Fun Endurance Hub'
    }
  },
  categories: {
    all: { ja: 'すべて表示', ca: 'Totes les categories', en: 'All Categories' },
    world: { ja: '🌍 MotoGP / SBK 世界戦', ca: '🌍 Mundial MotoGP / SBK', en: '🌍 MotoGP / SBK World' },
    kyushu: { ja: '🔥 九州 (SPA直入・AP・HSR)', ca: '🔥 Kyushu (SPA Naoiri / AP / HSR)', en: '🔥 Kyushu (SPA Naoiri / AP / HSR)' },
    'endurance-fun': { ja: '🎯 お題付き耐久・レン耐・草レース', ca: '🎯 Resistència amb Reptes i Popular', en: '🎯 Odai Endurance & Grassroots' },
    'all-japan': { ja: '🗾 全日本・全国地方選', ca: '🗾 Campionat del Japó (MFJ)', en: '🗾 All-Japan & Regional' },
    spotlight: { ja: '⚡ スーパーセーブ＆注目解説', ca: '⚡ Salvades i Anàlisi Tècnica', en: '⚡ Super Saves & Spotlight' }
  },
  articleTypes: {
    preview: { ja: '📅 今週の開催情報＆見どころ', ca: '📅 Prèvia i Horaris', en: '📅 Weekly Race Preview' },
    digest: { ja: '🏆 レース結果＆ダイジェスト', ca: '🏆 Resultats i Resum', en: '🏆 Race Results & Digest' },
    spotlight: { ja: '⚡ スーパーセーブ・深掘り特集', ca: '⚡ Salvada / Punt Clau', en: '⚡ Super Save & Spotlight' }
  },
  kyushuHub: {
    title: {
      ja: '🌋 九州3大サーキット＆「お題付き耐久草レース」特設パドック',
      ca: '🌋 Pàdoc Especial de Kyushu i Curses de Resistència amb Reptes',
      en: '🌋 Kyushu Big-3 Circuits & "Odai" Challenge Endurance Hub'
    },
    subtitle: {
      ja: '大分・熊本を中心に熱狂的な盛り上がりを見せる九州の二輪レースと、速さだけじゃないエンタメ草耐久をナオコ姐さんが徹底ナビゲート！',
      ca: 'La mecànica Naoko us guia pels circuits d\'Oita i Kumamoto i per les curses de resistència més divertides i originals del Japó!',
      en: 'Garage chief Naoko guides you through Oita & Kumamoto’s legendary tracks and Japan’s most entertaining recreational endurance races!'
    },
    spots: [
      {
        id: 'spa-naoiri',
        badge: 'OITA / TAKEDA',
        name: {
          ja: 'SPA直入（スパなおいり）',
          ca: 'Circuit SPA Naoiri (Takeda, Oita)',
          en: 'SPA Naoiri Circuit (Takeda, Oita)'
        },
        spec: {
          ja: '全長 1,430m / 九州ロードレース・サンデーレース・お題付き耐久の聖地',
          ca: '1.430m / Bressol de les curses populars i resistència d\'Oita',
          en: '1,430m / Home of Oita club racing, Sunday battles & Fun Endurance'
        },
        desc: {
          ja: '大分県竹田市直入町にある、ライダーとの距離が最高に近いテクニカルサーキット！九州ロードレースシリーズからミニバイク、走行会、そして名物「お題付き耐久草レース」まで、初心者もベテランも一日中笑って走れる最高の遊び場。終わった後の直入の温泉とソフトクリームも定番！',
          ca: 'Situat a Takeda (prefectura d\'Oita), és un traçat tècnic envoltat de natura on l\'ambient del pàdoc és com una gran família. Escenari habitual de campionats regionals,走行会 (track days) i les famoses curses de resistència amb proves especials al box.',
          en: 'Nestled in Takeda, Oita Prefecture, this tight, technical 1,430m track boasts the friendliest paddock in Kyushu. Hosts regional championships, track days, and legendary recreational endurance events—best followed by local hot springs and soft-serve ice cream!'
        }
      },
      {
        id: 'autopolis',
        badge: 'OITA / HITA',
        name: {
          ja: 'オートポリス (AUTOPOLIS)',
          ca: 'Circuit Internacional Autopolis (Hita, Oita)',
          en: 'Autopolis International Racing Course (Hita, Oita)'
        },
        spec: {
          ja: '全長 4,674m / 全日本スーパーバイク in 九州・ゴールドカップ・ミニろく',
          ca: '4.674m / Superbike All-Japan, Gold Cup i Mini-6 Resistència',
          en: '4,674m / All-Japan Superbike, Gold Cup & Mini-Bike Endurance'
        },
        desc: {
          ja: '大分県日田市上津江町の標高900mに位置する国際格式サーキット。名物「ファイナルコーナースタンド」や高低差52mのジェットコースターレイアウトで、全日本ロードレース（スーパーバイクレース in 九州）から地方選手権ゴールドカップ、ミニバイク耐久まで熱いバトルが繰り広げられます。',
          ca: 'Circuit internacional d\'alta muntanya a Hita (Oita), amb un desnivell de 52 metres que posa a prova el coratge dels pilots i la potència dels motors. Acull des del Campionat del Japó de Superbikes fins a la Gold Cup amateur.',
          en: 'High-altitude international circuit in Hita, Oita featuring a dramatic 52m elevation change. Home to MFJ All-Japan Superbike rounds, the Gold Cup regional series, and grueling mini-bike endurance races.'
        }
      },
      {
        id: 'hsr-kyushu',
        badge: 'KUMAMOTO / OZU',
        name: {
          ja: 'HSR九州（ホンダセーフティ＆ライディングプラザ九州）',
          ca: 'HSR Kyushu (Ozu, Kumamoto)',
          en: 'HSR Kyushu Circuit (Ozu, Kumamoto)'
        },
        spec: {
          ja: '全長 2,350m / 九州ロードレース選手権・鉄馬・ドリームカップ・ミニバイク8耐',
          ca: '2.350m / Campionat de Kyushu, Tetsuma (Iron Horse) i 8 Hores Mini',
          en: '2,350m / Kyushu Road Race, "Tetsuma" Iron Horse & Mini 8-Hours'
        },
        desc: {
          ja: '熊本空港近く、ホンダ熊本製作所に隣接する本格サーキットコース。九州ロードレース選手権、空冷・鉄フレームの祭典「鉄馬（Tetsuma）」、GROMやCBR250Rドリームカップ、冬のミニバイク8時間耐久など、九州の草レーサーなら誰もが通う聖地です。',
          ca: 'Situat al costat de la fàbrica de motos de Kumamoto, aquest circuit de 2.350m és el cor del motociclisme base a Kyushu: des del festival de clàssiques i xassís de ferro «Tetsuma» fins a les 8 Hores de resistència en minimoto.',
          en: 'Located right beside the Kumamoto motorcycle plant, this 2,350m course is a cornerstone of Kyushu grassroots racing—hosting the "Tetsuma" iron-frame festival, Dream Cup one-make races, and the famous 8-Hour Mini-Bike Endurance.'
        }
      },
      {
        id: 'odai-endurance',
        badge: 'SPECIAL FEATURE',
        name: {
          ja: 'お題付き耐久草レース ＆ レン耐（レクリエーション耐久）',
          ca: 'Curses de Resistència amb Reptes («Odai-tsuki») i Rentai',
          en: '"Odai-Tsuki" Task-Challenge Endurance & Rentai Racing'
        },
        spec: {
          ja: 'ラップタイム × ピットお題攻略 ＝ 誰もが主役になれる究極の草レース！',
          ca: 'Temps per volta + Reptes d\'enginy al box = Diversió garantida!',
          en: 'Lap Times × Pit-Stop Mini-Games = Grassroots Fun for Everyone!'
        },
        desc: {
          ja: 'ただ速く走るだけじゃない！ピットインのたびに「お題（けん玉、知恵の輪、早食い、クイズ、お絵描き、じゃんけん等）」が課され、クリアしないとコース復帰できないレクリエーション耐久レース（SPA直入などで開催されるお題付き耐久や、全国で人気のレン耐など）。ガチ勢が知恵の輪でハマる間にエンジョイ勢が大逆転する、草レースの最高峰エンターテインメント！',
          ca: 'Una modalitat única del motociclisme amateur japonès! A cada canvi de pilot al box, l\'equip ha de superar un «repte sorpresa» (puzles, jocs d\'habilitat, preguntes o reptes gastronòmics) abans de tornar a pista. Així, un equip amateur pot guanyar als pilots més ràpids!',
          en: 'A beloved Japanese recreational endurance format where every pit stop requires clearing a surprise "Odai" challenge (puzzles, kendama, trivia, or snack missions) before rejoining the track! Even if a pro rider shaves seconds on track, getting stuck on a puzzle in the pits lets casual teams pull off hilarious upset victories!'
        }
      }
    ]
  },
  catPaddock: {
    title: {
      ja: '🐾 二足歩行の猫編集部（Cat Paddock Press）',
      ca: '🐾 La Redacció Felina del Pàdoc',
      en: '🐾 Meet the Bipedal Cat Editorial Paddock'
    },
    subtitle: {
      ja: 'レーシングジャケットとメカニックツナギを着こなし、2本足でサーキットを駆け回る3匹のスペシャリスト',
      ca: 'Tres periodistes i mecànics felins que recorren els circuits sobre dues potes amb passió pel motor',
      en: 'Three bipedal feline motorsport specialists walking the pit lane in press vests and oil-stained coveralls'
    }
  },
  catalunyaSection: {
    badge: '.CAT DOMAIN COMMUNITY MISSION',
    title: {
      ja: '🏴󠁥󠁳󠁣󠁴󠁿 カタルーニャ語と二輪文化への貢献（Fundació .cat 準拠）',
      ca: '🏴󠁥󠁳󠁣󠁴󠁿 Compromís amb la Llengua Catalana i la Cultura del Motor (.cat)',
      en: '🏴󠁥󠁳󠁣󠁴󠁿 Commitment to Catalan Language & Motorsport Culture (.cat)'
    },
    body: {
      ja: 'honda.cat は、カタルーニャ語およびカタルーニャ文化の発展を目的とする「.cat」ドメインの理念に賛同し、すべての記事を日本語・カタルーニャ語（Català）・英語の3カ国語で発信しています。MotoGPカタルーニャGP（モンメロ）の熱狂を日本へ、そして大分（SPA直入・オートポリス）や熊本（HSR九州）をはじめとする日本の草レース文化をカタルーニャ語圏のモータースポーツファンへ届ける文化交流メディアです。',
      ca: 'El domini honda.cat forma part de la comunitat puntCAT (Fundació .cat) i té com a missió difondre el motociclisme en llengua catalana. Catalunya i el Japó comparteixen una tradició única en el món de les dues rodes: des del Circuit de Barcelona-Catalunya (Montmeló) i les 24 Hores de Catalunya fins a Suzuka i els circuits de Kyushu (Autopolis, SPA Naoiri, HSR Kyushu). Totes les nostres cròniques, anàlisis tècniques de salvades i reportatges de curses populars es publiquen íntegrament en català.',
      en: 'honda.cat proudly supports the Fundació .cat mission by publishing every motorsport report in Catalan (Català), Japanese, and English. Catalonia and Japan share one of the world’s deepest two-wheel racing bonds—from Circuit de Barcelona-Catalunya (Montmeló) to Suzuka and Kyushu’s grassroots circuits.'
    }
  },
  footer: {
    disclaimer: {
      ja: '※免責事項：当サイト（honda.cat）は二輪モータースポーツおよび草レースを愛する独立系ファン＆AIメディアであり、本田技研工業株式会社（Honda Motor Co., Ltd.）および関連企業の公式ウェブサイトではありません。',
      ca: '*Avís legal: Aquest lloc web (honda.cat) és un portal independent d\'informació sobre motociclisme i curses populars impulsat per IA, i no està afiliat ni és el lloc web oficial de Honda Motor Co., Ltd.',
      en: '*Disclaimer: honda.cat is an independent, AI-powered motorsport and grassroots racing fan portal and is not affiliated with or endorsed by Honda Motor Co., Ltd.'
    },
    langMemoryNote: {
      ja: '💾 選択した表示言語はブラウザ（localStorage）に自動保存され、次回アクセス時も維持されます。',
      ca: '💾 L\'idioma seleccionat es desa automàticament al navegador (localStorage) per a futures visites.',
      en: '💾 Your selected language is automatically saved in browser storage (localStorage) for future visits.'
    }
  }
};
