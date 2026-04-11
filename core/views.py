from django.shortcuts import render


def home(request):
    boards = ['Dhaka', 'Chittagong', 'Rajshahi', 'Comilla', 'Sylhet', 'Jessore', 'Barisal', 'Dinajpur']
    context = {
        'boards': boards,
    }
    return render(request, 'core/home.html', context)


def question_bank(request):
    questions = [
        {
            'board': 'Dhaka',
            'class': '10',
            'subject': 'Physics',
            'year': 2023,
            'difficulty': 'Medium',
            'chapter': 'আলো ও প্রতিসরণ',
            'preview': 'আলো যখন ঘন মাধ্যম থেকে হালকা মাধ্যমে যায় তখন কী হয়?',
            'is_mcq': True,
            'correct_option_index': 1,
            'options': ['প্রতিসরণ কোণ ছোট হয়', 'প্রতিসরণ কোণ বড় হয়', 'কোণ সমান হয়', 'আলো ফিরে আসে'],
        },
        {
            'board': 'Rajshahi',
            'class': '10',
            'subject': 'Chemistry',
            'year': 2023,
            'difficulty': 'Hard',
            'chapter': 'অ্যাসিড, ক্ষার ও লবণ',
            'preview': 'নিচের কোনটি অ্যাম্ফোটেরিক অক্সাইড?',
            'is_mcq': True,
            'correct_option_index': 2,
            'options': ['Na₂O', 'CO₂', 'Al₂O₃', 'CaO'],
        },
        {
            'board': 'Chittagong',
            'class': '9',
            'subject': 'Biology',
            'year': 2022,
            'difficulty': 'Easy',
            'chapter': 'কোষ বিভাজন',
            'preview': 'কোষের শক্তি উৎপাদনকারী অঙ্গাণুর নাম কী?',
            'is_mcq': True,
            'correct_option_index': 1,
            'options': ['রাইবোজোম', 'মাইটোকন্ড্রিয়া', 'গলজি বডি', 'লাইসোজোম'],
        },
    ]

    context = {
        'questions': questions,
        'boards': ['Dhaka', 'Rajshahi', 'Chittagong', 'Sylhet', 'Comilla'],
        'subjects': ['Physics', 'Chemistry', 'Biology', 'Math', 'English'],
        'classes': ['9', '10', '11', '12'],
        'years': [2023, 2022, 2021, 2020],
    }
    return render(request, 'core/question_bank.html', context)


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
                        {'heading': 'Coulomb\'s Law', 'content': 'F = kq₁q₂/r² — দুটি চার্জের মধ্যে বল তাদের গুণফলের সমানুপাতিক এবং দূরত্বের বর্গের ব্যস্তানুপাতিক।'},
                        {'heading': 'Electric Field (E)', 'content': 'E = F/q = kQ/r² — প্রতি একক চার্জে যে বল অনুভব হয় তাই Electric Field। একক: N/C বা V/m।'},
                        {'heading': 'Gauss\'s Law', 'content': 'φ = Q_enc/ε₀ — বদ্ধ পৃষ্ঠের মধ্য দিয়ে মোট electric flux ভেতরের মোট চার্জের সমানুপাতিক।'},
                        {'heading': 'Electric Potential (V)', 'content': 'V = kQ/r — একটি বিন্দুতে কাজ করাতে যে শক্তি দরকার তাই potential। একক: Volt (J/C)।'},
                        {'heading': 'Capacitance (C)', 'content': 'C = Q/V = ε₀A/d — Capacitor চার্জ সঞ্চয় করে। Parallel plate: C বাড়ে যখন A বাড়ে বা d কমে।'},
                    ]
                },
                {
                    'title': 'Current Electricity',
                    'pages': 15,
                    'downloads': 980,
                    'rating': 4.7,
                    'key_notes': [
                        {'heading': 'Ohm\'s Law', 'content': 'V = IR — Voltage, Current ও Resistance এর মধ্যে সম্পর্ক।'},
                        {'heading': 'Resistance Formula', 'content': 'R = ρL/A — ρ হলো resistivity, L হলো দৈর্ঘ্য, A হলো প্রস্থচ্ছেদের ক্ষেত্রফল।'},
                        {'heading': 'Kirchhoff\'s Laws', 'content': 'KCL: জংশনে আসা মোট current = যাওয়া মোট current।'},
                        {'heading': 'Power Dissipation', 'content': 'P = VI = I²R = V²/R — Resistor-এ dissipated power। একক: Watt।'},
                        {'heading': 'Series vs Parallel', 'content': 'Series: R_total = R₁+R₂ | Parallel: 1/R_total = 1/R₁+1/R₂'},
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
                        {'heading': 'pH Scale', 'content': 'pH = -log[H⁺] — 0-14 স্কেলে। pH < 7 = Acid, pH = 7 = Neutral, pH > 7 = Base।'},
                        {'heading': 'Arrhenius Theory', 'content': 'Acid: H⁺ দেয়, Base: OH⁻ দেয়।'},
                        {'heading': 'Bronsted-Lowry Theory', 'content': 'Acid: Proton donor, Base: Proton acceptor।'},
                        {'heading': 'Buffer Solution', 'content': 'Weak acid + Conjugate base মিশ্রণ। pH পরিবর্তনকে প্রতিরোধ করে।'},
                        {'heading': 'Titration', 'content': 'Equivalence point: moles acid = moles base।'},
                    ]
                },
                {
                    'title': 'Periodic Table',
                    'pages': 20,
                    'downloads': 2100,
                    'rating': 4.8,
                    'key_notes': [
                        {'heading': 'Periodic Trends', 'content': 'Atomic radius: Period বরাবর কমে, Group বরাবর বাড়ে।'},
                        {'heading': 'Electronegativity', 'content': 'Pauling scale-এ F সবচেয়ে বেশি (4.0)।'},
                        {'heading': 'Electronic Configuration', 'content': 'Aufbau principle: 1s → 2s → 2p → 3s → 3p → 4s → 3d।'},
                        {'heading': 'Block Classification', 'content': 's-block (Group 1,2), p-block (Group 13-18), d-block, f-block।'},
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
                        {'heading': 'Mendel\'s Laws', 'content': 'Law of Segregation ও Law of Independent Assortment।'},
                        {'heading': 'DNA Structure', 'content': 'Double helix। Base pairing: A-T, G-C।'},
                        {'heading': 'Mitosis vs Meiosis', 'content': 'Mitosis: 2n→2n। Meiosis: 2n→n।'},
                        {'heading': 'Gene Expression', 'content': 'Transcription: DNA→mRNA। Translation: mRNA→Protein।'},
                    ]
                },
                {
                    'title': 'Cell Structure',
                    'pages': 12,
                    'downloads': 1100,
                    'rating': 4.8,
                    'key_notes': [
                        {'heading': 'Prokaryote vs Eukaryote', 'content': 'Prokaryote: No nucleus। Eukaryote: True nucleus।'},
                        {'heading': 'Cell Organelles', 'content': 'Mitochondria: ATP। Ribosome: Protein। Golgi: Packaging।'},
                        {'heading': 'Cell Membrane', 'content': 'Phospholipid bilayer + Proteins। Fluid mosaic model।'},
                        {'heading': 'Cell Cycle', 'content': 'G1 → S → G2 → M phase।'},
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
                        {'heading': 'Fundamental Theorem', 'content': '∫[a to b] f(x)dx = F(b) - F(a)।'},
                        {'heading': 'Integration by Parts', 'content': '∫u dv = uv - ∫v du। LIATE rule।'},
                        {'heading': 'Standard Integrals', 'content': '∫xⁿdx = xⁿ⁺¹/(n+1)+C, ∫eˣdx = eˣ+C।'},
                        {'heading': 'Substitution Method', 'content': 'u = g(x) রাখলে du = g\'(x)dx।'},
                    ]
                },
                {
                    'title': 'Differentiation',
                    'pages': 18,
                    'downloads': 1900,
                    'rating': 4.8,
                    'key_notes': [
                        {'heading': 'First Principle', 'content': 'f\'(x) = lim[h→0] [f(x+h)-f(x)]/h।'},
                        {'heading': 'Standard Derivatives', 'content': 'd/dx(xⁿ) = nxⁿ⁻¹, d/dx(eˣ) = eˣ।'},
                        {'heading': 'Chain Rule', 'content': 'd/dx[f(g(x))] = f\'(g(x))·g\'(x)।'},
                        {'heading': 'Product & Quotient Rule', 'content': '(uv)\' = u\'v + uv\'। (u/v)\' = (u\'v - uv\')/v²।'},
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
                        {'heading': 'Parts of Speech', 'content': '8 parts: Noun, Pronoun, Verb, Adjective, Adverb, Preposition, Conjunction, Interjection।'},
                        {'heading': 'Tenses', 'content': '12 tenses: Present/Past/Future × Simple/Continuous/Perfect/Perfect Continuous।'},
                        {'heading': 'Voice Change', 'content': 'Active → Passive: Object + be + V3 + by + Subject।'},
                        {'heading': 'Conditionals', 'content': '1st: If + Present, will + V1। 2nd: If + Past, would + V1।'},
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
                        {'heading': 'শব্দের শ্রেণিবিভাগ', 'content': 'বিশেষ্য, সর্বনাম, বিশেষণ, ক্রিয়া, ক্রিয়াবিশেষণ।'},
                        {'heading': 'সন্ধি', 'content': 'স্বরসন্ধি, ব্যঞ্জনসন্ধি, বিসর্গ সন্ধি।'},
                        {'heading': 'কারক ও বিভক্তি', 'content': 'কর্তৃ, কর্ম, করণ, সম্প্রদান, অপাদান, অধিকরণ কারক।'},
                        {'heading': 'সমাস', 'content': 'দ্বন্দ্ব, তৎপুরুষ, কর্মধারয়, বহুব্রীহি, অব্যয়ীভাব, দ্বিগু।'},
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


def practical_lab(request):
    return render(request, 'core/practical_lab.html')