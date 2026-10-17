# Data Dictionary (قاموس البيانات)

| Field | Meaning / الوصف | Notes |
| :--- | :--- | :--- |
| `product_id` | معرف داخلي موحد للمنتج في المشروع | Unique internal ID |
| `product_name` | اسم المنتج كما جاء من المصدر | Raw product name from source |
| `strength` | التركيز أو القوة إذا كان متاحاً | e.g., 500mg, 10mg/ml |
| `dosage_form` | الشكل الدوائي إذا كان متاحاً | e.g., Tablet, Syrup, Vial |
| `pack_size` / `unit` | حجم العبوة أو وحدة القياس | e.g., 30 Tablets, 100ml |
| `supplier_id` / `source_id` | معرف المورد أو المصدر إذا كان متاحاً | Supplier / Source identifier |
| `price` | السعر مع العملة ووحدة التسعير إن أمكن | Unit/pack price (must be $\ge 0$) |
| `availability_status` | حالة التوافر حسب تعريف المصدر | In Stock, Shortage, Discontinued |
| `observation_date` | التاريخ اللي بتمثله المعلومة | Date of observation |
| `ingested_at` | وقت إدخال السجل للـ Pipeline | Timestamp of ingestion |
| `source_url` | رابط المصدر أو مرجع الملف | Source URL or file reference |
| `quality_status` | نتيجة فحوصات الجودة أو سبب العزل | VALID, QUARANTINED (with reason) |

---

### Product Identity Rule (قاعدة مطابقة المنتج)
مطابقة المنتج لا تعتمد على الاسم فقط إذا كانت التفاصيل متاحة:  
**مفتاح المقارنة:** `الاسم + التركيز/القوة + الشكل الدوائي + حجم العبوة/الوحدة`  
لأن مقارنة السعر بدون وحدة واضحة تكون مضللة.
