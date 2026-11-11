export type Lang = 'ja' | 'ca' | 'en';

export interface CatCharacter {
  id: 'marc' | 'suzuka' | 'naomi';
  image: string;
  badgeColor: string;
  gender: { ja: string; ca: string; en: string };
  name: { ja: string; ca: string; en: string };
  role: { ja: string; ca: string; en: string };
  specialty: { ja: string; ca: string; en: string };
  bio: { ja: string; ca: string; en: string };
  quoteNormal: { ja: string; ca: string; en: string };
}

export const CAT_TEAM: Record<'marc' | 'suzuka' | 'naomi', CatCharacter> = {
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
      ja: 'バルセロナ（モンメロ）生まれの二足歩行茶トラ猫。プレスジャケットをビシッと着こなし、ストップウォッチ片手に世界グランプリから日本のサーキットまで駆け回る熱血ジャーナリスト。64〜66度バンクからの「肘・肉球スーパーセーブ」を猫の空中姿勢制御になぞらえて解説するのが十八番。',
      ca: 'Gat tigrat bípede nascut a Montmeló (Catalunya). Sempre amb la seva jaqueta de premsa i cronòmetre en mà, connecta la passió del motociclisme català amb els circuits japonesos. Expert en analitzar "salvades impossibles" a més de 64 graus d\'inclinació.',
      en: 'Bipedal orange tabby born in Montmeló, Catalonia. Dressed in his press jacket with a stopwatch in paw, he bridges Catalan motorsport passion with Japanese racing culture. Famous for breaking down 64+ degree lean angle "super saves" using feline mid-air physics.'
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
      en: 'Suzuka (National & Regional Desk)'
    },
    role: {
      ja: '全日本ロードレース＆全国地方選手権特派員',
      ca: 'Corresponsal del Campionat del Japó i Sèries Regionals',
      en: 'All-Japan Championship & Regional Series Correspondent'
    },
    specialty: {
      ja: 'MFJ全日本ロードレース・全国地方選手権・九州サーキット取材',
      ca: 'MFJ All-Japan, Campionats Regionals del Japó i Kyushu',
      en: 'MFJ All-Japan Road Race, Nationwide Regional Series & Kyushu'
    },
    bio: {
      ja: 'カメラマンベストを着て二足歩行でパドックを駆ける三毛猫フォトジャーナリスト。MFJ全日本ロードレースや鈴鹿8耐をはじめ、北海道・東北・関東・中部・近畿・中国・九州（オートポリス・SPA直入・HSR九州）まで日本全国の地方選手権やサンデーレースを丁寧に取材するしっかり者。',
      ca: 'Gata calicó bípede i fotoperiodista equipada amb la seva armilla i teleobjectiu. Cobreix el Campionat del Japó (MFJ) i tots els campionats regionals de l\'arxipèlag japonès, amb una atenció especial als circuits d\'Autopolis, SPA Naoiri i HSR Kyushu.',
      en: 'Bipedal calico photojournalist in a press vest toting a telephoto DSLR. She covers MFJ All-Japan Road Racing and regional championships across Japan, with deep coverage of Kyushu’s Autopolis, SPA Naoiri, and HSR Kyushu.'
    },
    quoteNormal: {
      ja: '「今週末も全国のサーキットは路面コンディション抜群！朝のブリーフィングから皆さんの熱い走りをバッチリ撮りますよ！」',
      ca: '«Aquest cap de setmana l\'asfalt està en condicions ideals! Capturaré cada avançament des del briefing matinal!»',
      en: '"Track conditions are prime this weekend! I’ll be capturing every overtake right from the morning riders’ briefing!"'
    }
  },
  naomi: {
    id: 'naomi',
    image: '/images/cats/naomi.png',
    badgeColor: '#c77dff',
    gender: { ja: 'メス ♀', ca: 'Femella ♀', en: 'Female ♀' },
    name: {
      ja: 'ナオミ (Naomi)',
      ca: 'Naomi (Mecànica de Garatge)',
      en: 'Naomi (Garage Mechanic & Endurance Chief)'
    },
    role: {
      ja: 'サーキット整備・耐久＆ガレージ担当',
      ca: 'Especialista en Manteniment de Circuit, Resistència i Garatge',
      en: 'Circuit Maintenance, Endurance Racing & Garage Chief'
    },
    specialty: {
      ja: 'サーキットメンテナンス・車検対策・耐久＆サンデーレース・足回り整備',
      ca: 'Manteniment de competició, verificacions tècniques, resistència i suspensions',
      en: 'Track Maintenance, Tech Inspection Prep, Endurance & Suspension Setup'
    },
    bio: {
      ja: '九州のガレージに棲みつく二足歩行の黒雌猫メカニック。オイル汚れのついたヴィンテージのツナギを腰巻きにし、レンチ片手にライダーたちの甘い整備や無理な突っ込みをバッサリ斬る現場主義の職人。ぶっきらぼうな物言いの裏で、コースへ送り出すマシンの仕上がりとライダーの無事な帰還に誰よりも心を砕いている。',
      ca: 'Gata negra bípede que viu en un garatge de Kyushu amb la seva granota tacada d\'oli i una clau anglesa a l\'espatlla. De caràcter directe i exigent amb la mecànica, no perdona cap descuit al box, però vetlla com ningú perquè cada moto i cada pilot tornin sans i estalvis a meta.',
      en: 'Bipedal black female cat living in a Kyushu garage, wearing oil-stained coveralls tied at her waist with a box wrench over her shoulder. Blunt, battle-hardened, and uncompromising about mechanical prep, she watches over every rider rolling out of pit lane.'
    },
    quoteNormal: {
      ja: '「ったく、どいつもこいつも1コーナー突っ込みすぎなんだよ！タイム削る前にまずブレーキのエア抜きと温間空気圧をきっちり合わせなって言ってるだろ！…え？私が組んだ足回りのおかげで自己ベスト出たって？…べ、別にあんたのために徹夜したんじゃないわよ、帰りに直入のソフトクリーム奢ってくれるなら許してあげるけど…」',
      ca: '«Però què feu entrant tan passats al primer revolt?! Abans de buscar el rècord de pista, purgueu bé els frens i reviseu les pressions! ...Eh? Que gràcies a la meva posada a punt has fet rècord personal? N-no és pas que m\'hagi quedat tota la nit treballant per tu... però si em convides a un gelat tornant de Naoiri, potser t\'acompanyo...»',
      en: '"Tch, every single one of you is over-cooking Turn 1! Bleed your brakes and check your hot tire pressures before chasing lap times! ...Huh? You set a personal best thanks to my suspension setup? I-it’s not like I stayed up all night wrenching for you... though if you’re buying Naoiri soft-serve on the way home, I suppose I’ll come along..."'
    }
  }
};

export const UI_TEXT = {
  siteTitle: {
    ja: 'HONDA.CAT — 猫たちの二輪レース＆サーキット情報局',
    ca: 'HONDA.CAT — El Pàdoc dels Gats del Motociclisme',
    en: 'HONDA.CAT — Feline Motorsport & Circuit Paddock'
  },
  siteTagline: {
    ja: 'MotoGP・WorldSBKからMFJ全日本・全国地方選手権・九州サーキット＆メンテナンス情報まで！二足歩行の猫編集部がお届けする3カ国語レーシングメディア',
    ca: 'De MotoGP i WorldSBK fins al Campionat del Japó MFJ, sèries regionals, circuits de Kyushu i manteniment tècnic! Periodisme felí en català, japonès i anglès.',
    en: 'From MotoGP & WorldSBK to MFJ All-Japan, nationwide regional series, Kyushu circuits & track maintenance! Feline motorsport journalism in 3 languages.'
  },
  nav: {
    home: { ja: 'ホーム', ca: 'Inici', en: 'Home' },
    schedule: { ja: '🗓️ 全国＆世界スケジュール', ca: '🗓️ Calendari Oficial', en: '🗓️ Official Schedule' },
    kyushu: { ja: '九州サーキットガイド', ca: 'Circuits de Kyushu', en: 'Kyushu Circuits' },
    cats: { ja: '猫編集部紹介', ca: 'Redacció Felina', en: 'Cat Editorial Team' },
    about: { ja: 'About (.cat理念・編集方針)', ca: 'Sobre nosaltres (.cat)', en: 'About & Mission' }
  },
  hero: {
    badge: {
      ja: '🐾 AI全自動・日/カタルーニャ/英 3言語モータースポーツメディア',
      ca: '🐾 Mitjà de Motociclisme Trilingüe (CA / JA / EN) impulsat per IA',
      en: '🐾 AI-Powered Trilingual (JA / CA / EN) Motorsport Portal'
    },
    title: {
      ja: '世界グランプリの極限バトルも、日本各地のサーキット熱戦も。猫たちが全部追いかける。',
      ca: 'Des de les batalles de MotoGP fins als circuits de tot el Japó: els nostres gats ho viuen tot.',
      en: 'From World GP Battles to Circuits Across Japan: Our Paddock Cats Cover It All.'
    },
    subtitle: {
      ja: 'カタルーニャ（モンメロ）と日本全国のサーキット（鈴鹿・もてぎ・筑波・SUGO・岡山・十勝・オートポリス・SPA直入・HSR九州）を繋ぐ二輪レース情報サイト。スケジュール連動の開催プレビュー、レース結果ダイジェスト、スーパーセーブ解析、週1回のサーキットメンテナンス講座まで自動発信！',
      ca: 'Un pont entre Catalunya (Montmeló) i tots els circuits del Japó (Suzuka, Motegi, Tsukuba, SUGO, Okayama, Tokachi, Autopolis, SPA Naoiri i HSR Kyushu). Previews setmanals, resultats oficials, anàlisi de salvades i manteniment tècnic de circuit!',
      en: 'Bridging Catalonia (Montmeló) and circuits across Japan (Suzuka, Motegi, Tsukuba, SUGO, Okayama, Tokachi, Autopolis, SPA Naoiri & HSR Kyushu). Schedule-driven race previews, official results, super-save physics, and weekly track maintenance!'
    },
    ctaPrimary: {
      ja: '🏁 最新記事を読む',
      ca: '🏁 Llegir les últimes cròniques',
      en: '🏁 Read Latest Reports'
    },
    ctaSecondary: {
      ja: '🗓️ 公式スケジュールを見る',
      ca: '🗓️ Veure el Calendari Oficial',
      en: '🗓️ View Official Schedule'
    }
  },
  categories: {
    all: { ja: 'すべて表示', ca: 'Totes les categories', en: 'All Categories' },
    world: { ja: '🌍 MotoGP / SBK 世界戦', ca: '🌍 Mundial MotoGP / SBK', en: '🌍 MotoGP / SBK World' },
    'all-japan': { ja: '🗾 全日本・全国地方選 (MFJ)', ca: '🗾 Campionat del Japó i Regionals', en: '🗾 All-Japan & Regional' },
    kyushu: { ja: '🔥 九州 (オートポリス・SPA直入・HSR)', ca: '🔥 Kyushu (Autopolis / SPA Naoiri / HSR)', en: '🔥 Kyushu (Autopolis / SPA Naoiri / HSR)' },
    'endurance-fun': { ja: '🏁 耐久・サンデー・クラブマン', ca: '🏁 Resistència i Clubman', en: '🏁 Endurance & Clubman' },
    spotlight: { ja: '⚡ スーパーセーブ＆技術解説', ca: '⚡ Salvades i Anàlisi Tècnica', en: '⚡ Super Saves & Spotlight' },
    maintenance: { ja: '🔧 サーキット整備＆豆知識', ca: '🔧 Manteniment i Trucs de Circuit', en: '🔧 Track Maintenance & Tips' }
  },
  articleTypes: {
    preview: { ja: '📅 今週の開催情報＆見どころ', ca: '📅 Prèvia i Horaris', en: '📅 Weekly Race Preview' },
    digest: { ja: '🏆 レース結果＆ダイジェスト', ca: '🏆 Resultats i Resum', en: '🏆 Race Results & Digest' },
    spotlight: { ja: '⚡ スーパーセーブ・深掘り特集', ca: '⚡ Salvada / Punt Clau', en: '⚡ Super Save & Spotlight' },
    maintenance: { ja: '🔧 週1連載：サーキット整備＆豆知識', ca: '🔧 Manteniment Setmanal de Pàdoc', en: '🔧 Weekly Track Maintenance & Trivia' }
  },
  kyushuHub: {
    title: {
      ja: '🌋 九州3大サーキット（オートポリス・SPA直入・HSR九州）パドックガイド',
      ca: '🌋 Guia dels Tres Grans Circuits de Kyushu (Autopolis, SPA Naoiri i HSR Kyushu)',
      en: '🌋 Kyushu Big-3 Circuits Guide (Autopolis, SPA Naoiri & HSR Kyushu)'
    },
    subtitle: {
      ja: '大分・熊本を中心に数々の名勝負が繰り広げられる九州の主要サーキット特性と開催カテゴリーを徹底ナビゲート！',
      ca: 'La nostra redacció us guia pels circuits d\'Oita i Kumamoto, les seves característiques tècniques i els campionats que s\'hi disputen!',
      en: 'Our feline paddock crew guides you through Oita and Kumamoto’s premier racing circuits, track layouts, and championship categories!'
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
          ja: '全長 1,430m・最大直線 380m / 九州ロードレース・サンデー・耐久シリーズ',
          ca: '1.430m · Recta 380m / Campionat de Kyushu, Sunday Race i Resistència',
          en: '1,430m · 380m Straight / Kyushu Road Race, Sunday Series & Endurance'
        },
        desc: {
          ja: '1991年開場、大分県竹田市直入町にある全長1,430m・幅員8〜12mの本格テクニカルサーキット。MFJ公認の九州ロードレースシリーズやサンデーレース、ミニバイク・耐久イベント、スポーツ走行まで幅広く開催されています。',
          ca: 'Inaugurat el 1991 a Takeda (prefectura d\'Oita), és un traçat tècnic de 1.430m envoltat de natura que acull proves del Campionat de Kyushu, curses dominicals, tandes esportives i proves de resistència.',
          en: 'Opened in 1991 in Takeda, Oita Prefecture, this technical 1,430m track hosts MFJ Kyushu Road Race rounds, Sunday clubman sprints, endurance events, and regular sports riding sessions.'
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
          ja: '全長 4,674m・高低差 52m / 全日本スーパーバイク in 九州・ゴールドカップ・ミニろく',
          ca: '4.674m · Desnivell 52m / Superbike All-Japan, Gold Cup i Mini-6',
          en: '4,674m · 52m Elevation / All-Japan Superbike, Gold Cup & Mini-6 Endurance'
        },
        desc: {
          ja: '大分県日田市上津江町の標高約900mに位置する国際格式サーキット。全長4,674m・高低差52mのダイナミックなレイアウトで、MFJ全日本ロードレース選手権（スーパーバイクレース in 九州）や地方選手権ゴールドカップ、6時間耐久レースが開催されます。',
          ca: 'Circuit internacional d\'alta muntanya a Hita (Oita), amb un desnivell de 52 metres. Acull el Campionat del Japó de Superbikes (MFJ), la sèrie regional Gold Cup i curses de resistència de 6 hores.',
          en: 'High-altitude international circuit in Hita, Oita featuring a dramatic 52m elevation change. Home to MFJ All-Japan Superbike rounds, the Gold Cup regional championship, and 6-hour endurance races.'
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
          ja: '熊本県菊池郡大津町、ホンダ熊本製作所に隣接する全長2,350mのサーキットコース。MFJ九州ロードレース選手権、鉄フレーム車両の祭典「鉄馬（Tetsuma）」、CBR250R/GROMドリームカップ、ミニバイク8時間耐久など多彩な公式戦が開催されています。',
          ca: 'Situat al costat de la fàbrica de motos de Kumamoto, aquest circuit de 2.350m acull el Campionat de Kyushu MFJ, el festival «Tetsuma» i les 8 Hores de resistència.',
          en: 'Located beside the Kumamoto motorcycle plant, this 2,350m course hosts the MFJ Kyushu Road Race Championship, the "Tetsuma" festival, Dream Cup races, and the 8-Hour Mini-Bike Endurance.'
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
      ja: 'honda.cat は、カタルーニャ語およびカタルーニャ文化の発展を目的とする「.cat」ドメインの理念に賛同し、すべての記事を日本語・カタルーニャ語（Català）・英語の3カ国語で発信しています。MotoGPカタルーニャGP（モンメロ）の熱狂を日本へ、そして日本全国（鈴鹿・もてぎ・筑波・SUGO・岡山・十勝・オートポリス・SPA直入・HSR九州）の二輪レース文化とメンテナンス技術をカタルーニャ語圏のモータースポーツファンへ届ける文化交流メディアです。',
      ca: 'El domini honda.cat forma part de la comunitat puntCAT (Fundació .cat) i té com a missió difondre el motociclisme en llengua catalana. Catalunya i el Japó comparteixen una tradició única en el món de les dues rodes: des del Circuit de Barcelona-Catalunya (Montmeló) i les 24 Hores de Catalunya fins a Suzuka i tots els circuits japonesos. Totes les nostres cròniques, anàlisis tècniques de salvades i guies de manteniment es publiquen íntegrament en català.',
      en: 'honda.cat proudly supports the Fundació .cat mission by publishing every motorsport report and technical guide in Catalan (Català), Japanese, and English. Catalonia and Japan share one of the world’s deepest two-wheel racing bonds—from Circuit de Barcelona-Catalunya (Montmeló) to Suzuka and circuits across Japan.'
    }
  },
  footer: {
    disclaimer: {
      ja: '※免責事項：当サイト（honda.cat）は二輪モータースポーツおよびサーキット文化を愛する独立系ファン＆AIメディアであり、本田技研工業株式会社（Honda Motor Co., Ltd.）および関連企業の公式ウェブサイトではありません。',
      ca: '*Avís legal: Aquest lloc web (honda.cat) és un portal independent d\'informació sobre motociclisme impulsat per IA, i no està afiliat ni és el lloc web oficial de Honda Motor Co., Ltd.',
      en: '*Disclaimer: honda.cat is an independent, AI-powered motorsport fan portal and is not affiliated with or endorsed by Honda Motor Co., Ltd.'
    },
    langMemoryNote: {
      ja: '💾 選択した表示言語はブラウザ（localStorage）に自動保存され、次回アクセス時も維持されます。',
      ca: '💾 L\'idioma seleccionat es desa automàticament al navegador (localStorage) per a futures visites.',
      en: '💾 Your selected language is automatically saved in browser storage (localStorage) for future visits.'
    }
  }
};
