import csv
import random

random.seed(42)

AREAS = [
    "মিরপুর ১০", "ধানমন্ডি ২৭", "মোহাম্মদপুর", "উত্তরা সেক্টর ৭", "যাত্রাবাড়ী",
    "বাড্ডা", "মালিবাগ", "খিলগাঁও", "শান্তিনগর", "রামপুরা", "বাসাবো", "কল্যাণপুর",
    "শ্যামলী", "মহাখালী", "গুলশান ২", "বনানী", "তেজগাঁও", "লালবাগ", "ওয়ারী",
    "পল্টন", "মগবাজার", "কাজীপাড়া", "আগারগাঁও", "মিরপুর ১", "নিউমার্কেট",
]

TIME_PHRASES = [
    "গতকাল রাত থেকে", "আজ সকাল থেকে", "গত তিন দিন ধরে", "কয়েক ঘণ্টা ধরে",
    "গত এক সপ্তাহ ধরে", "বৃষ্টির পর থেকে", "গত বর্ষা মৌসুম থেকে", "",
]

SEVERITY_PHRASES = [
    "খুবই খারাপ অবস্থা", "মারাত্মক সমস্যা হয়ে দাঁড়িয়েছে", "চলাচলে খুব কষ্ট হচ্ছে",
    "অবস্থা ভয়াবহ", "সমস্যাটি জরুরি ভিত্তিতে সমাধান দরকার", "",
]

CATEGORY_TEMPLATES = {
    "blocked_drain": [
        "{area}তে ড্রেন সম্পূর্ণ বন্ধ হয়ে আছে, পানি বের হচ্ছে না।",
        "{area}র রাস্তার পাশের ড্রেনটি ময়লা আবর্জনায় ভরাট হয়ে গেছে।",
        "{time} {area}য় ড্রেন আটকে থাকায় দুর্গন্ধ ছড়াচ্ছে।",
        "আমাদের এলাকার ড্রেনেজ লাইনে প্লাস্টিক ও আবর্জনা জমে ব্লক হয়ে গেছে।",
        "{area}তে নর্দমা বন্ধ, {severity}।",
        "ড্রেন পরিষ্কার না করায় {area}য় পানি জমে থাকছে।",
    ],
    "open_manhole": [
        "{area}তে একটি ম্যানহোলের ঢাকনা খোলা অবস্থায় পড়ে আছে, দুর্ঘটনার আশঙ্কা।",
        "{time} {area}র রাস্তায় ম্যানহোলের কভার ভাঙা, {severity}।",
        "রাস্তার মাঝখানে খোলা ম্যানহোল, রাতে দেখা যায় না, বিপজ্জনক।",
        "{area}তে ম্যানহোলের ঢাকনা চুরি হয়ে গেছে, বাচ্চারা পড়ে যেতে পারে।",
        "ম্যানহোল খোলা থাকায় {area}য় দুর্গন্ধ ও দুর্ঘটনার ঝুঁকি বেড়েছে।",
        "{area}র মোড়ে ম্যানহোলের ঢাকনা নেই, দ্রুত মেরামত দরকার।",
    ],
    "road_flooding": [
        "{time} {area}র প্রধান সড়কে হাঁটু পানি জমে গেছে।",
        "{area}তে সামান্য বৃষ্টিতেই রাস্তা ডুবে যায়, {severity}।",
        "রাস্তায় পানি জমে যানবাহন চলাচল বন্ধ হয়ে গেছে {area}তে।",
        "{area}র অলিগলি সব পানির নিচে, স্কুলে যাওয়া যাচ্ছে না।",
        "সড়কে জলাবদ্ধতার কারণে {area}য় দোকানপাটে পানি ঢুকে গেছে।",
        "{time} {area}তে জলাবদ্ধতা দেখা দিয়েছে, {severity}।",
    ],
    "waterlogging_recurring": [
        "{area}তে প্রতি বছর বর্ষায় একই জায়গায় পানি জমে, স্থায়ী সমাধান দরকার।",
        "বারবার অভিযোগ করার পরও {area}র জলাবদ্ধতা সমস্যার কোনো সমাধান হয়নি।",
        "{area}তে এই এলাকায় প্রতিটি বৃষ্টিতেই জলাবদ্ধতা হয়, এটা নিয়মিত সমস্যা।",
        "গত কয়েক বছর ধরে {area}র এই পয়েন্টে পানি জমার সমস্যা চলছে।",
        "{area}তে ড্রেনেজ ব্যবস্থার স্থায়ী সংস্কার ছাড়া সমস্যা কমছে না।",
        "প্রতি মৌসুমে {area}র একই রাস্তায় জলাবদ্ধতা দেখা দেয়, {severity}।",
    ],
    "sewage_overflow": [
        "{area}তে স্যুয়ারেজ লাইন উপচে রাস্তায় নোংরা পানি চলে এসেছে।",
        "{time} {area}র ম্যানহোল দিয়ে ময়লা পানি উপচে পড়ছে।",
        "স্যুয়ারেজের পানি রাস্তায় উঠে আসায় {area}য় দুর্গন্ধ ছড়াচ্ছে।",
        "{area}তে পয়ঃনিষ্কাশন লাইন ফেটে ময়লা পানি জমে গেছে, {severity}।",
        "বাসার সামনের রাস্তায় স্যুয়ারেজের পানি জমে আছে, {area}।",
        "{area}র নর্দমার নোংরা পানি মূল সড়কে চলে এসেছে, স্বাস্থ্য ঝুঁকি তৈরি করছে।",
    ],
    "other": [
        "{area}তে রাস্তার পাশে অবৈধভাবে ময়লা ফেলে ড্রেন নষ্ট করা হচ্ছে।",
        "নতুন রাস্তা নির্মাণের সময় ড্রেন ব্যবস্থা ঠিকমতো করা হয়নি {area}তে।",
        "{area}র ড্রেনেজ ম্যাপ বা নকশা সম্পর্কে তথ্য জানতে চাই।",
        "{time} {area}তে রাস্তা খোঁড়াখুঁড়ির পর মেরামত না করায় সমস্যা হচ্ছে।",
        "{area}তে ড্রেন নির্মাণ কাজ অর্ধেক রেখে বন্ধ হয়ে আছে।",
        "এলাকাবাসীর পক্ষ থেকে {area}র ড্রেনেজ ব্যবস্থা নিয়ে একটি সাধারণ মতামত।",
    ],
}

CATEGORY_LABELS = list(CATEGORY_TEMPLATES.keys())
SAMPLES_PER_CATEGORY = 60


def fill_template(template):
    return template.format(
        area=random.choice(AREAS),
        time=random.choice(TIME_PHRASES),
        severity=random.choice(SEVERITY_PHRASES),
    ).replace("  ", " ").strip()


def generate_dataset():
    rows = []
    complaint_id = 1
    for category in CATEGORY_LABELS:
        templates = CATEGORY_TEMPLATES[category]
        for _ in range(SAMPLES_PER_CATEGORY):
            template = random.choice(templates)
            text = fill_template(template)
            rows.append({
                "id": complaint_id,
                "text_bn": text,
                "category": category,
            })
            complaint_id += 1
    random.shuffle(rows)
    for i, row in enumerate(rows, start=1):
        row["id"] = i
    return rows


def save_csv(rows, path):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["id", "text_bn", "category"])
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    rows = generate_dataset()
    save_csv(rows, "drainage_complaints_bn.csv")
    print(f"Generated {len(rows)} rows across {len(CATEGORY_LABELS)} categories")
    for cat in CATEGORY_LABELS:
        count = sum(1 for r in rows if r["category"] == cat)
        print(f"  {cat}: {count}")
