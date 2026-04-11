from django.shortcuts import render

def home(request):
    return render(request, 'core/home.html')

def question_bank(request):
    return render(request, 'core/question_bank.html')

def login_view(request):
    return render(request, 'core/login.html')


def study_notes(request):
    subjects = [
        {
            'name': 'Physics',
            'icon': '⚡',
            'color': 'blue',
            'chapters': [
                {
                    'title': 'Electrostatics',
                    'pages': 12,
                    'downloads': 1200,
                    'rating': 4.8,
                    'key_notes': [
                        {'heading': 'Coulomb\'s Law',
                         'content': 'F = kq₁q₂/r² — দুটি চার্জের মধ্যে বল তাদের গুণফলের সমানুপাতিক এবং দূরত্বের বর্গের ব্যস্তানুপাতিক।'},
                        {'heading': 'Electric Field (E)',
                         'content': 'E = F/q = kQ/r² — প্রতি একক চার্জে যে বল অনুভব হয় তাই Electric Field। একক: N/C বা V/m।'},
                        {'heading': 'Gauss\'s Law',
                         'content': 'φ = Q_enc/ε₀ — বদ্ধ পৃষ্ঠের মধ্য দিয়ে মোট electric flux ভেতরের মোট চার্জের সমানুপাতিক।'},
                        {'heading': 'Electric Potential (V)',
                         'content': 'V = kQ/r — একটি বিন্দুতে কাজ করাতে যে শক্তি দরকার তাই potential। একক: Volt (J/C)।'},
                        {'heading': 'Capacitance (C)',
                         'content': 'C = Q/V = ε₀A/d — Capacitor চার্জ সঞ্চয় করে। Parallel plate: C বাড়ে যখন A বাড়ে বা d কমে।'},
                    ]
                },
                {
                    'title': 'Current Electricity',
                    'pages': 15,
                    'downloads': 980,
                    'rating': 4.7,
                    'key_notes': [
                        {'heading': 'Ohm\'s Law',
                         'content': 'V = IR — Voltage, Current ও Resistance এর মধ্যে সম্পর্ক। R ধ্রুবক থাকলে V ও I সমানুপাতিক।'},
                        {'heading': 'Resistance Formula',
                         'content': 'R = ρL/A — ρ হলো resistivity, L হলো দৈর্ঘ্য, A হলো প্রস্থচ্ছেদের ক্ষেত্রফল।'},
                        {'heading': 'Kirchhoff\'s Laws',
                         'content': 'KCL: জংশনে আসা মোট current = যাওয়া মোট current। KVL: একটি loop-এ voltage এর বীজগাণিতিক যোগফল = 0।'},
                        {'heading': 'Power Dissipation',
                         'content': 'P = VI = I²R = V²/R — Resistor-এ dissipated power। একক: Watt (W)।'},
                        {'heading': 'Series vs Parallel',
                         'content': 'Series: R_total = R₁+R₂+... | Parallel: 1/R_total = 1/R₁+1/R₂+...'},
                    ]
                },
                {
                    'title': 'Magnetism',
                    'pages': 10,
                    'downloads': 750,
                    'rating': 4.6,
                    'key_notes': [
                        {'heading': 'Magnetic Force',
                         'content': 'F = qvB sinθ — চার্জিত particle-এর উপর magnetic force। θ হলো v ও B এর মধ্যবর্তী কোণ।'},
                        {'heading': 'Biot-Savart Law',
                         'content': 'dB = μ₀I dl sinθ / 4πr² — current-carrying conductor থেকে magnetic field নির্ণয়।'},
                        {'heading': 'Ampere\'s Law',
                         'content': '∮B·dl = μ₀I_enc — বদ্ধ পথে B-field এর line integral মোট enclosed current এর সমানুপাতিক।'},
                        {'heading': 'Faraday\'s Law',
                         'content': 'ε = -dΦ/dt — Magnetic flux পরিবর্তনের হার থেকে EMF তৈরি হয়। ঋণচিহ্ন Lenz\'s law নির্দেশ করে।'},
                    ]
                },
                {
                    'title': 'Optics',
                    'pages': 18,
                    'downloads': 1100,
                    'rating': 4.9,
                    'key_notes': [
                        {'heading': 'Snell\'s Law',
                         'content': 'n₁ sinθ₁ = n₂ sinθ₂ — আলোর প্রতিসরণের সূত্র। n হলো refractive index।'},
                        {'heading': 'Mirror Formula',
                         'content': '1/f = 1/v + 1/u — দর্পণের focal length, image distance ও object distance এর সম্পর্ক।'},
                        {'heading': 'Lens Maker\'s Equation',
                         'content': '1/f = (n-1)(1/R₁ - 1/R₂) — Lens এর focal length নির্ভর করে উপাদান ও বক্রতার উপর।'},
                        {'heading': 'Total Internal Reflection',
                         'content': 'θ_c = sin⁻¹(n₂/n₁) — Critical angle এর বেশি হলে আলো সম্পূর্ণ প্রতিফলিত হয়। Optical fiber এর ভিত্তি।'},
                        {'heading': 'Young\'s Double Slit',
                         'content': 'β = λD/d — Fringe width, λ হলো wavelength, D হলো screen distance, d হলো slit separation।'},
                    ]
                },
            ]
        },
        {
            'name': 'Chemistry',
            'icon': '🧪',
            'color': 'green',
            'chapters': [
                {
                    'title': 'Acids & Bases',
                    'pages': 14,
                    'downloads': 1500,
                    'rating': 4.9,
                    'key_notes': [
                        {'heading': 'pH Scale',
                         'content': 'pH = -log[H⁺] — 0-14 স্কেলে। pH < 7 = Acid, pH = 7 = Neutral, pH > 7 = Base।'},
                        {'heading': 'Arrhenius Theory',
                         'content': 'Acid: H⁺ দেয়, Base: OH⁻ দেয়। সীমাবদ্ধতা: শুধু জলীয় দ্রবণে প্রযোজ্য।'},
                        {'heading': 'Bronsted-Lowry Theory',
                         'content': 'Acid: Proton donor (H⁺ দেয়), Base: Proton acceptor (H⁺ নেয়)। Conjugate acid-base pair গঠন করে।'},
                        {'heading': 'Buffer Solution',
                         'content': 'Weak acid + Conjugate base মিশ্রণ। pH পরিবর্তনকে প্রতিরোধ করে। Henderson-Hasselbalch: pH = pKa + log([A⁻]/[HA])'},
                        {'heading': 'Titration',
                         'content': 'Equivalence point: moles acid = moles base। Indicator পরিবর্তনে endpoint চেনা যায়।'},
                    ]
                },
                {
                    'title': 'Periodic Table',
                    'pages': 20,
                    'downloads': 2100,
                    'rating': 4.8,
                    'key_notes': [
                        {'heading': 'Periodic Trends',
                         'content': 'Atomic radius: Period বরাবর কমে, Group বরাবর বাড়ে। Ionization energy: Period বরাবর বাড়ে।'},
                        {'heading': 'Electronegativity',
                         'content': 'Pauling scale-এ F সবচেয়ে বেশি (4.0)। Period বরাবর বাড়ে, Group বরাবর কমে।'},
                        {'heading': 'Electronic Configuration',
                         'content': 'Aufbau principle: 1s → 2s → 2p → 3s → 3p → 4s → 3d। Hund\'s rule ও Pauli exclusion principle মানতে হবে।'},
                        {'heading': 'Block Classification',
                         'content': 's-block (Group 1,2), p-block (Group 13-18), d-block (Transition metals), f-block (Lanthanides/Actinides)।'},
                    ]
                },
                {
                    'title': 'Chemical Bonding',
                    'pages': 16,
                    'downloads': 1300,
                    'rating': 4.7,
                    'key_notes': [
                        {'heading': 'Ionic Bond',
                         'content': 'Electron transfer দ্বারা গঠিত। Metal + Non-metal। NaCl উদাহরণ: Na → Na⁺ + e⁻, Cl + e⁻ → Cl⁻।'},
                        {'heading': 'Covalent Bond',
                         'content': 'Electron sharing দ্বারা গঠিত। Non-metal + Non-metal। Single (σ), Double (σ+π), Triple (σ+2π) bond।'},
                        {'heading': 'VSEPR Theory',
                         'content': 'Electron pair বিকর্ষণ করে সর্বোচ্চ দূরত্বে থাকে। BeCl₂: Linear, BF₃: Trigonal planar, CH₄: Tetrahedral।'},
                        {'heading': 'Hybridization',
                         'content': 'sp: Linear (180°), sp²: Trigonal (120°), sp³: Tetrahedral (109.5°), sp³d: Trigonal bipyramidal।'},
                    ]
                },
                {
                    'title': 'Organic Chemistry',
                    'pages': 25,
                    'downloads': 1800,
                    'rating': 4.9,
                    'key_notes': [
                        {'heading': 'Functional Groups',
                         'content': '-OH (Alcohol), -COOH (Carboxylic acid), -CHO (Aldehyde), -CO- (Ketone), -NH₂ (Amine), -COO- (Ester)।'},
                        {'heading': 'IUPAC Naming',
                         'content': 'Longest chain = parent chain। Side chains alphabetical order। Numbering: substituents কম নম্বরে।'},
                        {'heading': 'Isomerism',
                         'content': 'Structural: Chain, Position, Functional isomers। Stereoisomers: Geometric (cis/trans) ও Optical (R/S)।'},
                        {'heading': 'Reaction Types',
                         'content': 'Addition (Alkene + X₂), Substitution (Alkane + X₂ + hv), Elimination (alcohol → alkene + H₂O), Condensation।'},
                    ]
                },
            ]
        },
        {
            'name': 'Biology',
            'icon': '🧬',
            'color': 'purple',
            'chapters': [
                {
                    'title': 'Genetics',
                    'pages': 18,
                    'downloads': 950,
                    'rating': 4.6,
                    'key_notes': [
                        {'heading': 'Mendel\'s Laws',
                         'content': 'Law of Segregation: Allele জোড়া গেমেট তৈরিতে আলাদা হয়। Law of Independent Assortment: ভিন্ন traits স্বাধীনভাবে বংশগত হয়।'},
                        {'heading': 'DNA Structure',
                         'content': 'Double helix, 5\'→3\' direction। Base pairing: A-T (2 H-bond), G-C (3 H-bond)। Deoxyribose sugar + Phosphate backbone।'},
                        {'heading': 'Mitosis vs Meiosis',
                         'content': 'Mitosis: 2n→2n, 2 daughter cells, somatic cells। Meiosis: 2n→n, 4 gametes, genetic diversity সৃষ্টি করে।'},
                        {'heading': 'Gene Expression',
                         'content': 'Transcription: DNA→mRNA (nucleus)। Translation: mRNA→Protein (ribosome)। Codon = 3 nucleotides = 1 amino acid।'},
                    ]
                },
                {
                    'title': 'Cell Structure',
                    'pages': 12,
                    'downloads': 1100,
                    'rating': 4.8,
                    'key_notes': [
                        {'heading': 'Prokaryote vs Eukaryote',
                         'content': 'Prokaryote: No membrane-bound nucleus, No organelles। Eukaryote: True nucleus, Membrane-bound organelles।'},
                        {'heading': 'Cell Organelles',
                         'content': 'Mitochondria: ATP উৎপাদন। Ribosome: Protein সংশ্লেষণ। Golgi: Processing ও packaging। ER: Transport network।'},
                        {'heading': 'Cell Membrane',
                         'content': 'Phospholipid bilayer + Proteins। Fluid mosaic model। Selective permeable: osmosis, diffusion, active transport।'},
                        {'heading': 'Cell Cycle',
                         'content': 'G1 (growth) → S (DNA replication) → G2 (preparation) → M (mitosis)। Checkpoints: G1/S, G2/M, Spindle checkpoint।'},
                    ]
                },
                {
                    'title': 'Human Physiology',
                    'pages': 22,
                    'downloads': 1400,
                    'rating': 4.7,
                    'key_notes': [
                        {'heading': 'Circulatory System',
                         'content': 'Heart: 4 chambers। Pulmonary circuit: Heart→Lungs। Systemic circuit: Heart→Body। Blood pressure: Systolic/Diastolic।'},
                        {'heading': 'Nervous System',
                         'content': 'Neuron: Dendrite→Cell body→Axon→Synapse। Action potential: Na⁺ rush in, K⁺ rush out। Neurotransmitters chemical signal।'},
                        {'heading': 'Digestive System',
                         'content': 'Mouth→Esophagus→Stomach→Small intestine→Large intestine। Enzyme: Amylase (starch), Pepsin (protein), Lipase (fat)।'},
                        {'heading': 'Hormones',
                         'content': 'Insulin: Blood glucose কমায়। Glucagon: Blood glucose বাড়ায়। Adrenaline: Fight-or-flight। Thyroid: Metabolism নিয়ন্ত্রণ।'},
                    ]
                },
                {
                    'title': 'Ecology',
                    'pages': 15,
                    'downloads': 800,
                    'rating': 4.5,
                    'key_notes': [
                        {'heading': 'Food Chain & Web',
                         'content': 'Producer→Primary Consumer→Secondary Consumer→Tertiary Consumer। 10% energy rule: প্রতি trophic level-এ 10% শক্তি স্থানান্তরিত হয়।'},
                        {'heading': 'Biomes',
                         'content': 'Tropical rainforest: সর্বোচ্চ biodiversity। Tundra: সর্বনিম্ন temperature। Desert: কম rainfall। Grassland: মধ্যবর্তী।'},
                        {'heading': 'Population Dynamics',
                         'content': 'Carrying capacity (K): সর্বোচ্চ জনসংখ্যা। J-curve: Exponential growth। S-curve: Logistic growth।'},
                        {'heading': 'Nutrient Cycles',
                         'content': 'Carbon cycle: CO₂ fixation (photosynthesis) ও release (respiration/decomposition)। Nitrogen cycle: N₂→NH₃→NO₃⁻→N₂।'},
                    ]
                },
            ]
        },
        {
            'name': 'Mathematics',
            'icon': '📐',
            'color': 'yellow',
            'chapters': [
                {
                    'title': 'Integration',
                    'pages': 20,
                    'downloads': 2200,
                    'rating': 4.9,
                    'key_notes': [
                        {'heading': 'Fundamental Theorem',
                         'content': '∫[a to b] f(x)dx = F(b) - F(a) যেখানে F\'(x) = f(x)। Integration is anti-differentiation।'},
                        {'heading': 'Integration by Parts',
                         'content': '∫u dv = uv - ∫v du। LIATE rule: Logarithm, Inverse trig, Algebraic, Trig, Exponential।'},
                        {'heading': 'Standard Integrals',
                         'content': '∫xⁿdx = xⁿ⁺¹/(n+1)+C, ∫eˣdx = eˣ+C, ∫sinx dx = -cosx+C, ∫(1/x)dx = ln|x|+C।'},
                        {'heading': 'Substitution Method',
                         'content': 'u = g(x) রাখলে du = g\'(x)dx। Complex integral কে সহজ করার পদ্ধতি।'},
                        {'heading': 'Definite vs Indefinite',
                         'content': 'Indefinite: +C থাকে, ব্যবহার: antiderivative খোঁজা। Definite: [a,b] limit, ব্যবহার: area, volume, arc length।'},
                    ]
                },
                {
                    'title': 'Differentiation',
                    'pages': 18,
                    'downloads': 1900,
                    'rating': 4.8,
                    'key_notes': [
                        {'heading': 'First Principle',
                         'content': 'f\'(x) = lim[h→0] [f(x+h)-f(x)]/h — derivative এর মূল সংজ্ঞা।'},
                        {'heading': 'Standard Derivatives',
                         'content': 'd/dx(xⁿ) = nxⁿ⁻¹, d/dx(eˣ) = eˣ, d/dx(ln x) = 1/x, d/dx(sin x) = cos x।'},
                        {'heading': 'Chain Rule',
                         'content': 'd/dx[f(g(x))] = f\'(g(x))·g\'(x) — Composite function differentiate করার নিয়ম।'},
                        {'heading': 'Product & Quotient Rule',
                         'content': '(uv)\' = u\'v + uv\' — Product rule। (u/v)\' = (u\'v - uv\')/v² — Quotient rule।'},
                    ]
                },
                {
                    'title': 'Trigonometry',
                    'pages': 15,
                    'downloads': 1600,
                    'rating': 4.7,
                    'key_notes': [
                        {'heading': 'Basic Ratios',
                         'content': 'sin θ = P/H, cos θ = B/H, tan θ = P/B। sin²θ + cos²θ = 1 — Pythagorean identity।'},
                        {'heading': 'Important Values',
                         'content': 'sin 30°=½, sin 45°=1/√2, sin 60°=√3/2। cos এর ক্ষেত্রে বিপরীত। tan 45°=1, tan 60°=√3।'},
                        {'heading': 'Compound Angles',
                         'content': 'sin(A±B) = sinA cosB ± cosA sinB। cos(A±B) = cosA cosB ∓ sinA sinB।'},
                        {'heading': 'Double Angle',
                         'content': 'sin 2A = 2 sinA cosA। cos 2A = cos²A - sin²A = 1-2sin²A = 2cos²A-1।'},
                    ]
                },
                {
                    'title': 'Vectors',
                    'pages': 12,
                    'downloads': 1200,
                    'rating': 4.6,
                    'key_notes': [
                        {'heading': 'Vector Operations',
                         'content': 'Addition: Component-wise। Scalar multiplication: প্রতিটি component গুণ করা। Magnitude: |v| = √(x²+y²+z²)।'},
                        {'heading': 'Dot Product',
                         'content': 'a·b = |a||b|cosθ = axbx + ayby + azbz। Result: Scalar। Perpendicular হলে dot product = 0।'},
                        {'heading': 'Cross Product',
                         'content': 'a×b: Magnitude = |a||b|sinθ, Result: Vector। Direction: Right-hand rule। Parallel হলে cross product = 0।'},
                        {'heading': 'Unit Vector',
                         'content': 'â = a/|a| — Magnitude = 1। i, j, k হলো x, y, z অক্ষ বরাবর unit vectors।'},
                    ]
                },
            ]
        },
        {
            'name': 'English',
            'icon': '📖',
            'color': 'red',
            'chapters': [
                {
                    'title': 'Grammar Rules',
                    'pages': 25,
                    'downloads': 3000,
                    'rating': 4.8,
                    'key_notes': [
                        {'heading': 'Parts of Speech',
                         'content': '8 parts: Noun, Pronoun, Verb, Adjective, Adverb, Preposition, Conjunction, Interjection। প্রতিটির নিজস্ব কাজ আছে।'},
                        {'heading': 'Tenses',
                         'content': '12 tenses: Present/Past/Future × Simple/Continuous/Perfect/Perfect Continuous। Subject-verb agreement মানতে হবে।'},
                        {'heading': 'Voice Change',
                         'content': 'Active: Subject + Verb + Object। Passive: Object + be + V3 + by + Subject। Tense অনুযায়ী "be" verb পরিবর্তন।'},
                        {'heading': 'Conditionals',
                         'content': 'Zero: If + Present, Present। 1st: If + Present, will + V1। 2nd: If + Past, would + V1। 3rd: If + Past Perfect, would have + V3।'},
                        {'heading': 'Articles',
                         'content': 'a/an: Indefinite (vowel sound → an)। the: Definite (specific, unique, superlative, rivers/mountains)। No article: Plural general, abstract।'},
                    ]
                },
                {
                    'title': 'Essay Writing',
                    'pages': 10,
                    'downloads': 1500,
                    'rating': 4.7,
                    'key_notes': [
                        {'heading': 'Essay Structure',
                         'content': 'Introduction (Hook + Thesis) → Body Paragraphs (Topic sentence + Evidence + Analysis) → Conclusion (Summary + Final thought)।'},
                        {'heading': 'Paragraph Writing',
                         'content': 'PEEL: Point (main idea), Evidence (support), Explanation (analysis), Link (back to thesis)। প্রতিটি paragraph এ এক main idea।'},
                        {'heading': 'Linking Words',
                         'content': 'Addition: Furthermore, Moreover। Contrast: However, Nevertheless। Cause: Therefore, Consequently। Example: For instance।'},
                        {'heading': 'Formal vs Informal',
                         'content': 'Formal: No contractions, passive voice, complex sentences। Informal: Conversational, active, simple sentences।'},
                    ]
                },
                {
                    'title': 'Vocabulary',
                    'pages': 20,
                    'downloads': 2000,
                    'rating': 4.9,
                    'key_notes': [
                        {'heading': 'Word Formation',
                         'content': 'Prefix: un-, dis-, mis-, re- (meaning পরিবর্তন)। Suffix: -tion, -ness, -ful, -less (word class পরিবর্তন)।'},
                        {'heading': 'Synonyms & Antonyms',
                         'content': 'Context অনুযায়ী সঠিক synonym বেছে নাও। Antonym জানলে meaning বুঝতে সহজ হয়।'},
                        {'heading': 'Phrasal Verbs',
                         'content': 'Verb + Preposition/Adverb = নতুন meaning। Give up = ছেড়ে দেওয়া, Look after = যত্ন নেওয়া, Break down = ভেঙে পড়া।'},
                        {'heading': 'Idioms',
                         'content': 'Literal meaning আলাদা। "Break a leg" = শুভকামনা। "Hit the nail on the head" = সঠিকভাবে বলা। Context থেকে বোঝা যায়।'},
                    ]
                },
                {
                    'title': 'Comprehension',
                    'pages': 15,
                    'downloads': 1800,
                    'rating': 4.6,
                    'key_notes': [
                        {'heading': 'Reading Strategies',
                         'content': 'Skimming: মূল ধারণার জন্য দ্রুত পড়া। Scanning: নির্দিষ্ট তথ্য খোঁজা। Close reading: বিস্তারিত বিশ্লেষণ।'},
                        {'heading': 'Finding Main Idea',
                         'content': 'Topic sentence সাধারণত paragraph এর শুরুতে। Repeated ideas ও key words মনোযোগ দাও।'},
                        {'heading': 'Inference Questions',
                         'content': 'Directly stated নয়। Context clues ব্যবহার করো। Author\'s tone ও purpose বোঝার চেষ্টা করো।'},
                        {'heading': 'Vocabulary in Context',
                         'content': 'Unknown word এর আগে-পরের text দেখো। Prefix/suffix ব্যবহার করো। Synonyms দিয়ে meaning আন্দাজ করো।'},
                    ]
                },
            ]
        },
        {
            'name': 'Bangla',
            'icon': '🇧🇩',
            'color': 'indigo',
            'chapters': [
                {
                    'title': 'ব্যাকরণ',
                    'pages': 22,
                    'downloads': 2500,
                    'rating': 4.8,
                    'key_notes': [
                        {'heading': 'শব্দের শ্রেণিবিভাগ',
                         'content': 'বিশেষ্য, সর্বনাম, বিশেষণ, ক্রিয়া, ক্রিয়াবিশেষণ, অনুসর্গ, যোজক, আবেগ শব্দ — প্রতিটির নিজস্ব কাজ ও বৈশিষ্ট্য আছে।'},
                        {'heading': 'সন্ধি',
                         'content': 'স্বরসন্ধি: দুটি স্বরের মিলন। ব্যঞ্জনসন্ধি: ব্যঞ্জনের সাথে মিলন। বিসর্গ সন্ধি: বিসর্গ (ঃ) যুক্ত। নিয়ম মেনে শব্দ গঠন।'},
                        {'heading': 'কারক ও বিভক্তি',
                         'content': 'কর্তৃকারক (-এ, -রা), কর্মকারক (-কে, -রে), করণকারক (-দিয়ে), সম্প্রদানকারক (-কে), অপাদানকারক (-থেকে), অধিকরণকারক (-এ, -তে)।'},
                        {'heading': 'সমাস',
                         'content': 'দ্বন্দ্ব, তৎপুরুষ, কর্মধারয়, বহুব্রীহি, অব্যয়ীভাব, দ্বিগু — প্রতিটির আলাদা গঠনরীতি আছে।'},
                        {'heading': 'ক্রিয়ার কাল',
                         'content': 'বর্তমান (করি, করছি, করেছি), অতীত (করলাম, করছিলাম, করেছিলাম), ভবিষ্যৎ (করব, করতে থাকব, করে থাকব)।'},
                    ]
                },
                {
                    'title': 'রচনা',
                    'pages': 12,
                    'downloads': 1400,
                    'rating': 4.6,
                    'key_notes': [
                        {'heading': 'রচনার কাঠামো',
                         'content': 'ভূমিকা → মূল অংশ (একাধিক অনুচ্ছেদ) → উপসংহার। প্রতিটি অনুচ্ছেদে একটি মূল ভাব।'},
                        {'heading': 'ভাষার বৈশিষ্ট্য',
                         'content': 'প্রমিত বাংলা ব্যবহার করতে হবে। তথ্যসমৃদ্ধ, যুক্তিযুক্ত এবং সাবলীল হওয়া প্রয়োজন।'},
                        {'heading': 'বিষয় নির্বাচন',
                         'content': 'সমসাময়িক, জাতীয় ও আন্তর্জাতিক বিষয়ে ধারণা রাখো। পরিবেশ, প্রযুক্তি, সমাজ — গুরুত্বপূর্ণ বিষয়।'},
                        {'heading': 'উদ্ধৃতি ব্যবহার',
                         'content': 'বিখ্যাত ব্যক্তির উক্তি রচনাকে সমৃদ্ধ করে। প্রাসঙ্গিক কবিতার লাইন বা প্রবাদ ব্যবহার করো।'},
                    ]
                },
                {
                    'title': 'সারাংশ',
                    'pages': 8,
                    'downloads': 1000,
                    'rating': 4.5,
                    'key_notes': [
                        {'heading': 'সারাংশ লেখার নিয়ম',
                         'content': 'মূল বক্তব্য নিজের ভাষায় লেখো। মূল অনুচ্ছেদের ১/৩ ভাগের মধ্যে রাখো। বিস্তারিত উদাহরণ বাদ দাও।'},
                        {'heading': 'মূলভাব খোঁজা',
                         'content': 'বারবার আসা ভাব বা শব্দে মনোযোগ দাও। লেখকের মূল বক্তব্য কী তা বোঝার চেষ্টা করো।'},
                        {'heading': 'পরিহারযোগ্য বিষয়',
                         'content': 'উদাহরণ, কাহিনি, অলঙ্কার বাদ দাও। প্রথম-পুরুষ এড়াও। হুবহু বাক্য নেওয়া যাবে না।'},
                    ]
                },
                {
                    'title': 'পত্র লিখন',
                    'pages': 10,
                    'downloads': 1200,
                    'rating': 4.7,
                    'key_notes': [
                        {'heading': 'পত্রের অংশ',
                         'content': 'তারিখ → সম্বোধন → মূল বক্তব্য → ইতি/বিদায় → স্বাক্ষর। আনুষ্ঠানিক পত্রে পূর্ণ ঠিকানা দিতে হয়।'},
                        {'heading': 'আনুষ্ঠানিক পত্র',
                         'content': 'প্রধান শিক্ষক, সম্পাদক, কর্মকর্তাদের লেখা। ভাষা: মার্জিত, নম্র, সংক্ষিপ্ত ও স্পষ্ট।'},
                        {'heading': 'ব্যক্তিগত পত্র',
                         'content': 'বন্ধু, আত্মীয়দের লেখা। ভাষা: আন্তরিক, সহজ ও স্বাভাবিক। ঘটনা বিস্তারিত লেখা যায়।'},
                        {'heading': 'সাধারণ ভুল',
                         'content': 'সম্বোধন ও বিদায় সংগতিপূর্ণ হওয়া চাই। তারিখ ও ঠিকানা সঠিক হওয়া জরুরি। বিষয় স্পষ্টভাবে উল্লেখ করো।'},
                    ]
                },
            ]
        },
    ]

    popular_notes = [
        {'title': 'Electrostatics Formulas', 'subject': 'Physics', 'rating': 4.8, 'downloads': '1.2k', 'icon': '⚡'},
        {'title': 'Acid-Base Titration', 'subject': 'Chemistry', 'rating': 4.9, 'downloads': '980', 'icon': '🧪'},
        {'title': 'Integration Cheat Sheet', 'subject': 'Mathematics', 'rating': 4.9, 'downloads': '2.1k', 'icon': '📐'},
        {'title': 'Genetics Key Terms', 'subject': 'Biology', 'rating': 4.6, 'downloads': '750', 'icon': '🧬'},
        {'title': 'Grammar Quick Guide', 'subject': 'English', 'rating': 4.8, 'downloads': '3k', 'icon': '📖'},
        {'title': 'Periodic Table Trends', 'subject': 'Chemistry', 'rating': 4.9, 'downloads': '1.5k', 'icon': '🧪'},
    ]

    context = {
        'subjects': subjects,
        'popular_notes': popular_notes,
    }
    return render(request, 'core/study_notes.html', context)
def pricing(request):
    return render(request, 'core/pricing.html')

def dashboard(request):
    return render(request, 'core/dashboard.html')

def home(request):
    boards = ['Dhaka', 'Chittagong', 'Rajshahi', 'Comilla', 'Sylhet', 'Jessore', 'Barisal', 'Dinajpur']
    context = {
        'boards': boards,
    }
    return render(request, 'core/home.html', context)

def practical_lab(request):
    return render(request, 'core/practical_lab.html')