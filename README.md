# Pharma Supply Chain Intelligence

نظام هندسة بيانات (Data Engineering) لتحليل بيانات سلاسل إمداد الأدوية (الأسعار، التوافر، والمخزون) وتنظيمها عبر طبقات Lakehouse، مع **RAG Assistant** للبحث الموثق في المستندات التنظيمية وتنبيهات استدعاء الأدوية.

> **تنبيه:** النظام أداة تحليلية ودعم قرار للمشتريات وسلاسل الإمداد، وليس بديلاً طبياً أو صيدلانياً لتشخيص المرضى.

---

## هيكل الـ Repository

```text
pharma-supply-chain-intelligence/
├── README.md
├── docs/
│   ├── requirements.md       # نطاق ومتطلبات المشروع
│   ├── architecture.md       # معمارية النظام ومسار البيانات
│   ├── data_dictionary.md    # قاموس البيانات وقواعد المطابقة
│   ├── decisions.md          # قرارات المشروع المعتمدة وقيد الاختبار (ADR)
│   └── testing.md            # خطة الاختبارات وجودة البيانات
├── dags/                     # Apache Airflow DAGs
├── ingestion/                # سكربتات جلب البيانات من المصادر
├── lakehouse/
│   ├── bronze/               # البيانات الخام مع الـ Metadata
│   ├── silver/               # البيانات المنظفة والموحدة وفحوصات الجودة
│   └── gold/                 # جداول التحليلات والتقارير
├── rag/
│   ├── extraction/           # استخراج النص من الـ PDFs
│   ├── chunking/             # تقسيم النصوص مع حفظ البيانات الوصفية
│   ├── retrieval/            # البحث والاسترجاع عبر الـ Vector Index
│   └── evaluation/           # تقييم دقة الإجابات والاستشهاد بالمصادر
├── api/                      # FastAPI Backend
├── app/                      # Streamlit Dashboard & UI
├── tests/                    # اختبارات النظام وجودة البيانات
├── data_samples/             # عينات بيانات صغيرة للاختبار المحلي
├── requirements.txt          # مكتبات المشروع
├── .env.example              # نموذج المتغيرات البيئية
└── .gitignore
```

---

## تقسيم العمل على الفريق (4 أفراد)

| الدور | المسؤوليات الأساسية | التسليمات |
| :--- | :--- | :--- |
| **Member 1: Ingestion & Airflow** | مصادر البيانات، Connectors، الـ DAGs، الـ Retries/Logging، وتسليم البيانات الخام لطبقة Bronze. | `dags/` ، `ingestion/` ، فحص الـ Logs |
| **Member 2: Lakehouse & Data Quality** | تصميم الـ Schema، تنظيف وتوحيد البيانات، طبقات Bronze/Silver/Gold على Delta Lake، وقواعد الجودة والعزل (Quarantine). | `lakehouse/` ، جداول Gold ، تقرير الجودة |
| **Member 3: Documents & RAG** | تجهيز الـ Corpus، استخراج النصوص، الـ Chunking، الـ Embeddings، والاسترجاع مع التوثيق (Citations) وسلوك عدم التخمين. | `rag/` ، تقييم الـ RAG ، بنك الأسئلة |
| **Member 4: API, UI & Integration** | بناء الـ API بـ FastAPI، واجهة Streamlit، ربط المكونات، وقيادة سيناريو الـ Demo والاختبارات الشاملة. | `api/` ، `app/` ، الـ E2E Tests ، الـ Demo |

---

## قواعد العمل على GitHub

1. **العمل عبر Branches:** العمل على فروع واضحة مثل `feature/airflow-ingestion` أو `feature/rag-retrieval` وعمل Pull Request إلى فرع `develop`.
2. **عدم رفع بيانات ضخمة أو أسرار:** ممنوع رفع أي API Keys أو كلمات مرور أو ملفات بيانات ضخمة. استخدم `.env` والملفات التجريبية في `data_samples/`.
3. **توثيق القرارات:** أي تعديل في الـ Architecture أو الـ Schema يجب توثيقه في `docs/decisions.md`.
4. **تشغيل الاختبارات:** قبل طلب الدمج (PR)، تأكد من مراجعة الكود وتشغيل الاختبارات وتحديث التوثيق إذا تغيرت طريقة التشغيل.

---

## مواعيد التسليم (Delivery Milestones)

- **16 أكتوبر:** Planning + Requirements + Literature Review
- **6 نوفمبر:** System Analysis & Design (الـ Architecture، الـ Data Model، خطة الاختبارات)
- **30 نوفمبر:** Implementation (الـ Pipeline، طبقات Delta، الـ RAG، والواجهة)
- **4 ديسمبر:** Final Testing + Report + Presentation & Demo

---

## البدء السريع (Quickstart)

```bash
# 1. إنشاء البيئة الافتراضية
python -m venv .venv
source .venv/bin/activate  # وعلى Windows: .venv\Scripts\activate

# 2. تثبيت الاعتماديات
pip install -r requirements.txt

# 3. إعداد المتغيرات البيئية
cp .env.example .env
```
