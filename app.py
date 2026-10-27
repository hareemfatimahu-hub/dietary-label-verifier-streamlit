import re
import streamlit as st
from PIL import Image, ImageOps

try:
    import pytesseract
except ImportError:
    pytesseract = None

st.set_page_config(page_title="Dietary Label & Recipe Verifier", layout="wide")

# ------------------------------------------------------------------ SETTINGS
CONTACT_EMAIL = "CHANGE-ME@example.com"  # use an email made for this project
RULES_VERSION = "v0.1 STARTER, UNVERIFIED (set a real date after you check the lists)"
RULES_SOURCE = ("Starter lists written from general knowledge. Verify every entry against "
                "EFSA, Codex INS and PSQCA before relying on it.")

TERMS = """
TERMS OF USE AND PRIVACY NOTICE (Version 1.0, beta)

1. Purpose. This tool is for general education and information about ingredient text that
   you provide. It is not a medical device, not medical, dietary or religious advice, and
   not a substitute for a doctor, dietitian, allergist or certifying body.
2. No certification. The tool never states that any food is safe, suitable, gluten free,
   allergen free, Halal, Haram or compliant with any law.
3. Accuracy. Photo reading and text matching can miss or misread words, especially on
   curved, glossy or Urdu text. Results cover only the text you supplied. You must read the
   physical pack yourself before eating or serving any food.
4. Emergencies. Do not use this tool for allergy emergencies or urgent clinical decisions.
   If someone has a reaction, seek emergency care immediately.
5. No statement about manufacturers. Nothing shown is a finding or allegation about any
   brand or manufacturer.
6. Use at your own risk. To the fullest extent permitted by law, the developer is not liable
   for loss or harm arising from use of this tool or reliance on its results.
7. Privacy. Photos and text you submit are processed on the servers of the hosting provider
   while the tool runs. This tool does not intentionally save them, but you should not upload
   names, medical records or other personal information.
8. Rules lists. Ingredient and additive lists are starter lists that may be incomplete or
   outdated. Version and sources are shown on each result.
9. Beta. This is a test version shared with invited people only. Do not share the link.
10. Changes. These terms may be updated. Continued use means you accept the current version.
"""

# ------------------------------------------------------------------ RULES
CLAIM_DEFS = {
    "Sugar free": r"sugar[\s-]*free|zero\s+sugar|no\s+sugar",
    "No added sugar": r"no\s+added\s+sugars?|without\s+added\s+sugars?",
    "Gluten free": r"gluten[\s-]*free|no\s+gluten|free\s+from\s+gluten",
    "Dairy or lactose free": r"dairy[\s-]*free|lactose[\s-]*free|milk[\s-]*free|non[\s-]*dairy|free\s+from\s+(?:dairy|lactose|milk)",
    "No preservatives": r"no\s+(?:added\s+)?preservatives?|preservatives?[\s-]*free|without\s+preservatives?",
    "Nut free": r"(?:nut|peanut)[\s-]*free|free\s+from\s+nuts?",
    "Vegan": r"\bvegan\b|plant[\s-]*based",
}
ALL_CLAIMS_RE = re.compile("|".join(f"(?:{p})" for p in CLAIM_DEFS.values()), re.I)

CONDITIONS = {
    "Celiac (gluten)": {
        "found": ["wheat", "atta", "maida", "semolina", "suji", "sooji", "rye", "barley", "malt",
                  "spelt", "kamut", "triticale", "durum", "couscous", "seitan", "farina",
                  "bulgur", "daliya", "gluten", "soy sauce", "brewer's yeast", "گندم"],
        "verify": ["oats", "starch", "modified starch", "dextrin", "hydrolysed vegetable protein",
                   "hydrolyzed vegetable protein", "natural flavour", "natural flavor",
                   "flavouring", "flavoring", "spices", "seasoning", "glucose syrup",
                   "caramel colour", "caramel color", "emulsifier"],
        "alt": "General swaps: rice, maize, millet (bajra), sorghum (jowar), buckwheat, quinoa, "
               "besan, or flours labelled gluten free by the manufacturer.",
    },
    "Diabetes (sugars and refined carbohydrate)": {
        "found": ["sugar", "sucrose", "glucose", "fructose", "dextrose", "maltose", "maltodextrin",
                  "corn syrup", "glucose syrup", "high fructose", "invert sugar", "honey",
                  "jaggery", "gur", "molasses", "cane juice", "syrup", "maida", "refined flour",
                  "white flour", "condensed milk", "fruit juice concentrate"],
        "verify": ["starch", "modified starch", "sweetener", "sugar alcohol", "maltitol",
                   "sorbitol", "natural flavour", "natural flavor"],
        "alt": "General ideas: whole grains, legumes, unsweetened versions, whole fruit instead of "
               "juice. Portion and medication questions belong to a clinician.",
    },
    "IBS (high FODMAP)": {
        "found": ["onion", "garlic", "wheat", "rye", "barley", "honey", "apple", "pear", "mango",
                  "watermelon", "high fructose", "fructose", "inulin", "chicory", "agave",
                  "sorbitol", "mannitol", "maltitol", "xylitol", "isomalt", "lactitol",
                  "polydextrose", "milk", "lactose", "yoghurt", "yogurt", "cream", "cashew",
                  "pistachio", "chickpea", "lentil", "beans", "cauliflower", "mushroom"],
        "verify": ["natural flavour", "natural flavor", "spices", "seasoning", "flavouring",
                   "flavoring", "fruit concentrate", "fibre", "fiber"],
        "alt": "General low FODMAP ideas: garlic infused oil, green tops of spring onion, rice, "
               "lactose free milk, oranges, strawberries. Individual tolerance varies.",
    },
    "Lactose / milk": {
        "found": ["milk", "lactose", "whey", "cream", "butter", "ghee", "cheese", "paneer",
                  "yoghurt", "yogurt", "dahi", "curd", "khoya", "mawa", "malai", "rabri",
                  "casein", "caseinate", "milk powder", "skimmed milk", "condensed milk",
                  "buttermilk", "lassi", "ice cream", "دودھ"],
        "verify": ["natural flavour", "natural flavor", "margarine", "chocolate", "caramel"],
        "alt": "General swaps: lactose free milk or fortified plant drinks (check their labels). "
               "Ghee and butter are low in lactose but are still milk products.",
        "exclude": ["coconut milk", "almond milk", "soy milk", "soya milk", "oat milk",
                    "rice milk", "cocoa butter", "shea butter", "peanut butter", "nut butter",
                    "coconut cream"],
    },
    "Nut allergy": {
        "found": ["almond", "badam", "cashew", "kaju", "pistachio", "pista", "walnut", "akhrot",
                  "hazelnut", "pecan", "brazil nut", "macadamia", "peanut", "groundnut",
                  "moongphali", "pine nut", "chilgoza", "nut", "nuts", "marzipan", "praline",
                  "nougat", "gianduja", "مونگ پھلی", "بادام", "اخروٹ", "کاجو", "پستہ"],
        "verify": ["natural flavour", "natural flavor", "flavouring", "flavoring", "spices",
                   "chocolate", "vegetable oil", "seasoning"],
        "alt": "General ideas: sunflower or pumpkin seeds, or products certified nut free. "
               "Seeds can still carry cross contact, so check the pack.",
    },
}

MAY_CONTAIN_RE = re.compile(
    r"(may\s+contain[^.\n]{0,120}|traces?\s+of[^.\n]{0,80}|"
    r"(?:made|processed|produced|manufactured)\s+(?:in|on)[^.\n]{0,40}"
    r"(?:facility|factory|line|equipment)[^.\n]{0,80})", re.I)

DOUBTFUL = "Doubtful source"
ADDITIVES = {
    "102": ("Tartrazine", "Colour", "Synthetic azo dye. EU labels carry a children's activity warning."),
    "104": ("Quinoline yellow", "Colour", "Same EU children's activity warning as E102."),
    "110": ("Sunset yellow FCF", "Colour", "Same EU children's activity warning as E102."),
    "120": ("Carmine / cochineal", DOUBTFUL, "Insect derived colour. Rulings differ, verify with a certifying body."),
    "122": ("Carmoisine", "Colour", "Same EU children's activity warning as E102."),
    "124": ("Ponceau 4R", "Colour", "Same EU children's activity warning as E102."),
    "129": ("Allura red AC", "Colour", "Same EU children's activity warning as E102."),
    "171": ("Titanium dioxide", "Other of interest", "No longer authorised as a food additive in the EU (since 2022). Check local rules."),
    "200": ("Sorbic acid", "Preservative", "Preservative."),
    "202": ("Potassium sorbate", "Preservative", "Preservative."),
    "210": ("Benzoic acid", "Preservative", "Preservative."),
    "211": ("Sodium benzoate", "Preservative", "Preservative."),
    "220": ("Sulphur dioxide", "Preservative", "Sulphite. Can trigger reactions in some people, notably asthmatics."),
    "221": ("Sodium sulphite", "Preservative", "Sulphite. Can trigger reactions in some people, notably asthmatics."),
    "222": ("Sodium bisulphite", "Preservative", "Sulphite. Can trigger reactions in some people, notably asthmatics."),
    "223": ("Sodium metabisulphite", "Preservative", "Sulphite. Can trigger reactions in some people, notably asthmatics."),
    "224": ("Potassium metabisulphite", "Preservative", "Sulphite. Can trigger reactions in some people, notably asthmatics."),
    "228": ("Potassium bisulphite", "Preservative", "Sulphite. Can trigger reactions in some people, notably asthmatics."),
    "249": ("Potassium nitrite", "Preservative", "Used in cured meats."),
    "250": ("Sodium nitrite", "Preservative", "Used in cured meats."),
    "251": ("Sodium nitrate", "Preservative", "Used in cured meats."),
    "252": ("Potassium nitrate", "Preservative", "Used in cured meats."),
    "282": ("Calcium propionate", "Preservative", "Common bread preservative."),
    "310": ("Propyl gallate", "Antioxidant", "Synthetic antioxidant."),
    "319": ("TBHQ", "Antioxidant", "Synthetic antioxidant."),
    "320": ("BHA", "Antioxidant", "Synthetic antioxidant."),
    "321": ("BHT", "Antioxidant", "Synthetic antioxidant."),
    "322": ("Lecithin", DOUBTFUL, "Usually soy, sunflower or egg. Allergen source is not stated by the code."),
    "420": ("Sorbitol", "Sweetener (polyol)", "Can cause digestive upset. High FODMAP."),
    "421": ("Mannitol", "Sweetener (polyol)", "Can cause digestive upset. High FODMAP."),
    "422": ("Glycerol", DOUBTFUL, "Can be plant or animal derived."),
    "441": ("Gelatine", DOUBTFUL, "Animal derived. Source animal is rarely stated."),
    "470": ("Fatty acid salts", DOUBTFUL, "Can be plant or animal derived."),
    "471": ("Mono and diglycerides of fatty acids", DOUBTFUL, "Can be plant or animal derived."),
    "472": ("Esters of mono and diglycerides (E472a to f)", DOUBTFUL, "Can be plant or animal derived."),
    "473": ("Sucrose esters of fatty acids", DOUBTFUL, "Fatty acid source may be animal."),
    "475": ("Polyglycerol esters", DOUBTFUL, "Fatty acid source may be animal."),
    "477": ("Propylene glycol esters", DOUBTFUL, "Fatty acid source may be animal."),
    "481": ("Sodium stearoyl lactylate", DOUBTFUL, "Fatty acid source may be animal. Name contains lactylate, not lactose."),
    "482": ("Calcium stearoyl lactylate", DOUBTFUL, "Fatty acid source may be animal."),
    "542": ("Bone phosphate", DOUBTFUL, "Animal bone derived."),
    "570": ("Stearic acid", DOUBTFUL, "Can be plant or animal derived."),
    "621": ("Monosodium glutamate", "Flavour enhancer", "Flavour enhancer."),
    "627": ("Disodium guanylate", DOUBTFUL, "Flavour enhancer, source can be animal, fish or yeast."),
    "631": ("Disodium inosinate", DOUBTFUL, "Flavour enhancer, source can be animal, fish or yeast."),
    "635": ("Disodium 5'-ribonucleotides", DOUBTFUL, "Flavour enhancer, source can be animal, fish or yeast."),
    "904": ("Shellac", DOUBTFUL, "Insect derived glaze."),
    "920": ("L-cysteine", DOUBTFUL, "Can be animal (feather or hair) or synthetic."),
    "924": ("Potassium bromate", "Other of interest", "Bread improver. Restricted or banned in several countries. Check local rules."),
    "950": ("Acesulfame K", "Sweetener", "Artificial sweetener."),
    "951": ("Aspartame", "Sweetener", "Artificial sweetener. Not suitable for people with phenylketonuria."),
    "953": ("Isomalt", "Sweetener (polyol)", "Can cause digestive upset. High FODMAP."),
    "954": ("Saccharin", "Sweetener", "Artificial sweetener."),
    "955": ("Sucralose", "Sweetener", "Artificial sweetener."),
    "965": ("Maltitol", "Sweetener (polyol)", "Can cause digestive upset. High FODMAP."),
    "966": ("Lactitol", "Sweetener (polyol)", "Can cause digestive upset. High FODMAP."),
    "967": ("Xylitol", "Sweetener (polyol)", "Can cause digestive upset. High FODMAP."),
}
CODE_RE = re.compile(r"(?<![A-Za-z0-9])(?:E|INS)[\s\-]?(\d{3,4})([a-z]|\([ivx]+\))?(?![0-9])", re.I)
DOUBTFUL_NAMES = ["gelatin", "gelatine", "lard", "pork", "bacon", "ham", "alcohol", "wine", "beer",
                  "rum", "brandy", "rennet", "carmine", "cochineal", "shellac", "l-cysteine",
                  "animal fat", "tallow", "enzymes"]
PRESERVATIVE_NAMES = ["sodium benzoate", "potassium sorbate", "sorbic acid", "benzoic acid",
                      "sodium nitrite", "sodium nitrate", "potassium nitrite", "sulphite",
                      "sulfite", "sulphur dioxide", "sulfur dioxide", "calcium propionate",
                      "sodium metabisulphite", "sodium metabisulfite", "preservative"]


# ------------------------------------------------------------------ HELPERS
def strip_claims(text):
    """Blank out claim phrases such as 'gluten free' so they are not matched as triggers."""
    return ALL_CLAIMS_RE.sub(lambda m: " " * len(m.group(0)), text)


def find_terms(text, terms, exclude=()):
    clean = strip_claims(text)
    for ex in exclude:
        clean = re.sub(re.escape(ex), lambda m: " " * len(m.group(0)), clean, flags=re.I)
    low = clean.lower()
    out = []
    for term in terms:
        pat = r"(?<!\w)" + re.escape(term.lower()) + r"(?:e?s)?(?!\w)"
        m = re.search(pat, low)
        if m:
            s, e = max(0, m.start() - 25), min(len(clean), m.end() + 25)
            out.append((term, clean[s:e].replace("\n", " ").strip()))
    return out


def find_codes(text):
    seen = {}
    for m in CODE_RE.finditer(text):
        seen.setdefault(m.group(1), m.group(0))
    return seen


def prep(img):
    img = ImageOps.exif_transpose(img).convert("L")
    img = ImageOps.autocontrast(img)
    w, h = img.size
    if max(w, h) < 2000:
        img = img.resize((w * 2, h * 2))
    return img


def ocr_read(img):
    if pytesseract is None:
        return None, None, "pytesseract is not installed"
    p = prep(img)
    err = "unknown error"
    for lang in ("eng+urd", "eng"):
        try:
            d = pytesseract.image_to_data(p, lang=lang, output_type=pytesseract.Output.DICT)
            text = pytesseract.image_to_string(p, lang=lang)
            confs = []
            for w, c in zip(d["text"], d["conf"]):
                try:
                    c = float(c)
                except (TypeError, ValueError):
                    continue
                if w.strip() and c >= 0:
                    confs.append(c)
            return text, (sum(confs) / len(confs) if confs else 0.0), lang
        except Exception as e:  # noqa: BLE001
            err = str(e)
    return None, None, err


def reset_confirm():
    st.session_state["confirm_checked"] = False
    st.session_state["confirm_all_sides"] = False


LABEL, RECIPE = "Packaged food label", "Recipe (typed)"


def gate():
    """Fail closed: return text only when every safeguard is satisfied."""
    text = st.session_state.get("input_text", "")
    mode = st.session_state.get("mode", LABEL)
    problems = []
    if not st.session_state.get("confirm_all_sides"):
        problems.append("You have not confirmed that the text covers every side of the pack "
                        "(or every ingredient of the recipe).")
    if not st.session_state.get("confirm_checked"):
        problems.append("You have not confirmed the text against the physical pack or recipe.")
    if mode == LABEL:
        if len(text.strip()) < 30:
            problems.append("The text is too short to be a label.")
        if not re.search(r"ingredient|اجزاء|اجزا", text, re.I):
            problems.append('No "Ingredients" heading was found in the text.')
    elif len(text.strip()) < 10:
        problems.append("The recipe text is too short.")
    if problems:
        st.error("Cannot assess. " + " ".join(problems))
        return None
    return text


def audit_caption():
    st.caption(f"Rules version: {RULES_VERSION}. {RULES_SOURCE} Claim phrases such as "
               "'gluten free' are ignored when matching triggers. Any ingredient the reader "
               f"misread will not appear in results. Found an error? Contact: {CONTACT_EMAIL}")


# ------------------------------------------------------------------ PAGE
st.markdown("""
<style>
.disc{position:fixed;bottom:0;left:0;right:0;z-index:9999;background:#7a1f1f;color:#fff;
padding:8px 14px;font-size:13px;text-align:center}
.block-container{padding-bottom:110px}
</style>
<div class="disc"><b>Educational tool only. Not medical advice. Not for allergy emergencies or
clinical decisions.</b> It can misread labels. Always check the physical pack.</div>
""", unsafe_allow_html=True)

st.title("Dietary Label & Recipe Verifier")
st.warning("BETA test version. Results may be wrong. Always check the physical pack.")
st.error("In an allergic reaction, call emergency services. This tool is not for emergencies.")

with st.expander("Terms of use and privacy"):
    st.text(TERMS)

if not st.checkbox("I understand this is an educational tool that can misread labels, that I "
                   "must verify the physical pack myself, and that it is not medical advice.",
                   key="consent"):
    st.stop()

tab_in, tab_rec, tab_add = st.tabs(
    ["1. Input and photos", "2. Recipe scanner", "3. Additive detector"])

# ---- TAB 1
with tab_in:
    st.radio("What are you checking?", [LABEL, RECIPE], key="mode", horizontal=True,
             on_change=reset_confirm)
    mode = st.session_state["mode"]

    if mode == LABEL:
        st.subheader("Photos of every side of the pack")
        files = st.file_uploader("Upload front, back, and all sides (max 5 MB each)",
                                 type=["png", "jpg", "jpeg"], accept_multiple_files=True)
        st.caption("Photo reading uses one reader only, so errors are more likely. "
                   "You must correct the text below against the physical pack.")

        if st.button("Read photos", disabled=not files):
            parts, reports = [], []
            with st.spinner("Reading photos..."):
                for i, f in enumerate(files, 1):
                    img = Image.open(f)
                    o_text, conf, lang = ocr_read(img)
                    reports.append({"n": i, "name": f.name, "ocr": o_text, "conf": conf, "lang": lang})
                    if o_text:
                        parts.append(f"--- Photo {i} ---\n{o_text.strip()}")
            st.session_state["reports"] = reports
            st.session_state["input_text"] = "\n\n".join(parts)
            reset_confirm()

        for r in st.session_state.get("reports", []):
            st.markdown(f"**Photo {r['n']}: {r['name']}**")
            if r["ocr"] is None:
                st.error(f"Reading failed: {r['lang']}")
            else:
                if r["conf"] is not None and r["conf"] < 70:
                    st.warning(f"Low reading confidence ({r['conf']:.0f}%). Expect missed or wrong words.")
                if r["lang"] == "eng":
                    st.warning("Urdu reading data was not available, so only English was read.")

    st.subheader("Text to analyse (edit it so it matches the pack exactly)")
    st.text_area("Ingredients and label text", key="input_text", height=300, on_change=reset_confirm)
    side_label = ("I have read or photographed EVERY side of the pack, including small print."
                  if mode == LABEL else "I have listed EVERY ingredient of the recipe.")
    st.checkbox(side_label, key="confirm_all_sides")
    st.checkbox("I have checked the text above against the physical pack or recipe and corrected it.",
                key="confirm_checked")
    st.caption("Analysis stays locked until both boxes are ticked. Editing the text un-ticks them.")

# ---- TAB 2
with tab_rec:
    text = gate()
    if text:
        chosen = st.multiselect("Conditions to check", list(CONDITIONS), default=list(CONDITIONS))
        rows = []
        for name in chosen:
            rule = CONDITIONS[name]
            found = find_terms(text, rule["found"], rule.get("exclude", ()))
            verify = find_terms(text, rule["verify"], rule.get("exclude", ()))
            st.markdown(f"### {name}")
            if found:
                st.warning("Triggers found in the text: " + ", ".join(t for t, _ in found))
                st.write("General alternatives: " + rule["alt"])
            if verify:
                st.warning("Source unclear, verify with the manufacturer: " + ", ".join(t for t, _ in verify))
            if not found and not verify:
                st.info("No triggers detected in the text provided. This is NOT a statement that "
                        "the food is suitable. Check the physical pack.")
            for t, ctx in found:
                rows.append({"Condition": name, "Result": "Trigger", "Matched": t, "In text": ctx})
            for t, ctx in verify:
                rows.append({"Condition": name, "Result": "Source unclear", "Matched": t, "In text": ctx})
        mc = [m.group(0).strip() for m in MAY_CONTAIN_RE.finditer(text)]
        st.markdown("### Cross contact statements")
        if mc:
            st.warning("Found on the label: " + " | ".join(mc))
        else:
            st.info("None detected in the text provided. They may exist in text that was not read.")
        if rows:
            st.markdown("**Audit trail**")
            st.dataframe(rows)
        audit_caption()

# ---- TAB 3
with tab_add:
    text = gate()
    if text:
        codes = find_codes(text)
        rows, unknown = [], []
        for num, raw in codes.items():
            if num in ADDITIVES:
                n, cat, note = ADDITIVES[num]
                rows.append({"Found as": raw, "Name": n, "Category": cat, "Note": note})
            else:
                unknown.append(raw)
        names = find_terms(text, DOUBTFUL_NAMES)
        if rows:
            st.warning("Additives of interest found. This is information, not a safety verdict.")
            st.dataframe(rows)
        if unknown:
            st.warning("Codes found that are NOT in the rule list, look them up: " + ", ".join(unknown))
        if names:
            st.warning("Ingredient names with a doubtful source: " + ", ".join(t for t, _ in names)
                       + ". Verify with the manufacturer or a certifying body.")
        if not rows and not unknown and not names:
            st.info("No additive codes or listed names detected in the text provided. Codes the "
                    "reader missed would not appear here.")
        st.caption("Halal status cannot be decided from an additive code. This tool never gives "
                   "a Halal or Haram ruling.")
        audit_caption()
