# Architecture & System Design

## 1. مسار البيانات (Data Flow Diagram)

```
Data Sources (APIs / CSV / JSON / Public PDFs)
                     ↓
               Apache Airflow
         (Scheduling · Retries · Logs)
                     ↓
        Python Ingestion & Validation
                     ↓
       Databricks + Delta Lake / Parquet
           (Bronze → Silver → Gold)
                     ↓
        ┌────────────┴────────────┐
        ↓                         ↓
   SQL Analytics             RAG Pipeline
(Curated tables & metrics) (Extraction → Chunks → Vector Index)
        └────────────┬────────────┘
                     ↓
             FastAPI + Streamlit
       (Application Layer & Dashboard)
```

---

## 2. طبقات البيانات (Bronze / Silver / Gold)

- **Bronze (Raw Data):** حفظ نسخة من البيانات كما وردت مع Metadata (اسم المصدر، وقت التحميل، رابط المصدر أو اسم الملف). بدون تعديل أو مسح.
- **Silver (Cleaned & Standardized):** تنظيف القيم، توحيد أنواع البيانات وأسماء الأعمدة والوحدات، وإجراء فحوصات الجودة. السجلات غير الصالحة تُعزل (Quarantine) مع سبب الرفض.
- **Gold (Analytics-ready):** جداول مجهزة للأسئلة التحليلية (تغير الأسعار عبر الزمن، سجل التوافر، ملخص جودة البيانات).

---

## 3. مسار المستندات (RAG Pipeline)

1. **Extract:** استخراج النص من الـ PDF الرقمي أولاً، واستخدام الـ OCR فقط للصفحات الممسوحة.
2. **Chunk:** تقسيم النص لمقاطع مع الاحتفاظ بعنوان المستند ورابطه ورقم الصفحة.
3. **Embed & Index:** إنشاء Embeddings وحفظها في Vector Index خفيف.
4. **Retrieve:** استرجاع المقاطع الأكثر ارتباطاً بالسؤال.
5. **Answer:** توليد إجابة مبنية تماماً على المقاطع المسترجعة مع Citation صريح.
6. **No-Answer:** إذا لم توجد أدلة كافية، يصرح النظام بعدم كفاية المعلومات بدلاً من التخمين.

---

## 4. دور كل أداة (Tools Role)

| الأداة | الدور في المشروع |
| :--- | :--- |
| **Airflow** | تشغيل وترتيب خطوات الـ Pipeline وتسجيل الأخطاء. |
| **Databricks / Delta Lake** | بيئة معالجة البيانات وإدارة جداول ومعاملات الـ Lakehouse. |
| **Parquet** | صيغة التخزين Columnar للبيانات الجدولية. |
| **RAG Engine** | مسار استرجاع وتلخيص المستندات التنظيمية بمصادر موثقة. |
| **FastAPI + Streamlit** | واجهة العرض والـ API لتقليل التعقيد خارج Databricks. |
