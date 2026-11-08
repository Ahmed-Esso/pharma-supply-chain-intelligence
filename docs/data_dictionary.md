# قاموس البيانات ومخططات الطبقات (Data Dictionary & Medallion Schemas)

**المشروع:** Pharma Supply Chain Intelligence  
**المسؤول:** Member 2 — Lakehouse & Data Quality (أحمد عصام)  
**المنصة المعتمدة:** Databricks Lakehouse (`Delta Lake / Parquet`)  

---

## 1. هيكل الجداول عبر طبقات Medallion (`Bronze -> Silver -> Gold`)

| الطبقة (Layer) | اسم الجدول في Databricks / مسار الملف | نوع التخزين | الوصف |
| :--- | :--- | :--- | :--- |
| **Bronze (الخام)** | `bronze.supply_chain_raw` | Delta / Parquet | لقطة خام لبيانات الأسعار والتوافر (`raw_sample.csv`) مع بيانات التتبع (`ingested_at`, `record_hash`). |
| **Bronze (الخام)** | `bronze.openfda_ndc_raw` | Delta / JSON | البيانات الخام لسجل الأدوية من هيئة الدواء الأمريكية (`openFDA NDC`). |
| **Bronze (الخام)** | `bronze.openfda_enforcement_raw` | Delta / JSON | البيانات الخام لتنبيهات استدعاء الأدوية (`openFDA Enforcement Recalls`). |
| **Bronze (الخام)** | `bronze.rxnav_concepts_raw` | Delta / JSON | البيانات الخام لمطابقة المواد الفعالة وأكواد `RxCUI` من `NIH RxNav`. |
| **Bronze (الخام)** | `bronze.kaggle_medicines_raw` | Delta / CSV | البيانات الخام لملفَي Kaggle (`medicine_data.csv` و `Medicine_Details.csv`). |
| **Silver (المنظف)** | `silver.supply_chain_valid` | Delta Table | سجلات سلاسل الإمداد والأسعار والتوافر السليمة بعد التوحيد واجتياز فحوصات الجودة الـ 7. |
| **Silver (العزل)** | `silver.supply_chain_quarantine` | Delta Table | السجلات المرفوضة من فحوصات الجودة مع سبب العزل التفصيلي في عمود `quality_status`. |
| **Silver (المنظف)** | `silver.drug_master` | Delta Table | جدول الأدوية المرجعي الموحد بعد دمج وتنظيف `openFDA NDC` و `RxNav` و `Kaggle`. |
| **Silver (المنظف)** | `silver.drug_recalls` | Delta Table | جدول استدعاءات الأدوية المنظف والمفهرس برقم الاستدعاء `recall_number`. |
| **Gold (التحليلات)** | `gold.price_changes` | Delta / Parquet | تحليل تغير أسعار الأدوية عبر الزمن (الحد الأدنى، الأقصى، ونسبة التغير `%`) لنفس هوية المنتج والعملة. |
| **Gold (التحليلات)** | `gold.availability_and_recalls` | Delta / Parquet | ملخص الأدوية التي تعاني من نقص (`Shortage` / `Limited`) أو المرتبطة باستدعاءات دوائية (`Recalls`). |
| **Gold (التحليلات)** | `gold.unified_drug_catalog` | Delta / Parquet | الكتالوج التحليلي الموحد للأدوية والمواد الفعالة وأكواد `RxCUI` الجاهز للـ API والـ UI. |
| **Gold (التحليلات)** | `gold.data_quality_summary` | Delta / Parquet | إحصائيات جودة البيانات (إجمالي السجلات، المقبول، المعزول، وتوزيع أسباب الرفض). |

---

## 2. قاموس البيانات القياسي لجدول سلاسل الإمداد (`silver.supply_chain_valid` & `quarantine`)

يمثل هذا الجدول العقد الموحد (Schema Contract) المكون من **12 عموداً أساسياً** بالإضافة إلى بصمة التتبع:

| # | اسم العمود (`Column Name`) | النوع (`Delta Type`) | إلزامي؟ (`NOT NULL`) | الوصف والمعنى | المصدر في البيانات الخام (`Source Mapping`) | قاعدة فحص الجودة (`Data Quality Rule`) |
| :-: | :--- | :--- | :---: | :--- | :--- | :--- |
| 1 | **`product_id`** | `STRING` | نعم | معرّف داخلي موحّد للمنتج في المشروع | يُشتق برمجياً (`MD5/SHA256`) | يُحسب من المفتاح المركب: `product_name + strength + dosage_form + pack_size` |
| 2 | **`product_name`** | `STRING` | نعم | اسم الدواء التجاري أو العلمي كما ورد من المصدر | `product_name` / `brand_name` / `Name` | غير فارغ بعد إزالة المسافات (`TRIM(product_name) != ''`) وإلا يُعزل كـ `MISSING_PRODUCT_NAME` |
| 3 | **`strength`** | `STRING` | لا | التركيز أو القوة الدوائية (مثل `500 mg` أو `1 g`) | `strength` / `active_ingredients.strength` | توحيد مسافات ووحدات القياس (`mg`, `g`, `ml`) |
| 4 | **`dosage_form`** | `STRING` | لا | الشكل الصيدلي للدواء (مثل `Tablet`, `Capsule`, `Vial`) | `dosage_form` | توحيد حالة الأحرف (`Title Case`) |
| 5 | **`pack_size`** | `STRING` | لا | حجم العبوة أو وحدة البيع (مثل `20 Capsules`, `30 Tablets`) | `pack_size` / `packaging.description` | يُستخدم ضمن هوية المنتج لمنع مقارنة أسعار عبوات مختلفة الحجم |
| 6 | **`supplier_id`** | `STRING` | نعم | معرّف المورد أو الشركة المصنعة أو المصدر | `supplier_id` / `labeler_name` / `Company` | غير فارغ (`NOT NULL`) |
| 7 | **`price`** | `DOUBLE` | لا | سعر العبوة بالعملة المحددة | `price` / `Price` | رقم عشري غير سالب (`price >= 0.0`)؛ إذا كان سالباً (مثل `-10.00`) يُعزل كـ `NEGATIVE_PRICE` |
| 8 | **`currency`** | `STRING` | مشروط | كود العملة القياسي (`EGP`, `USD`, `INR`) | `currency` (أو `INR` لبيانات Kaggle 1mg) | إلزامي في حال وجود قيمة في `price` (`MISSING_CURRENCY`) |
| 9 | **`availability_status`** | `STRING` | لا | حالة التوافر في السلسلة (`In Stock`, `Shortage`, `Limited`) | `availability_status` | ضمن القيم المعتمدة أو `UNKNOWN` عند عدم التوفر من المصدر |
| 10 | **`observation_date`** | `DATE` | نعم | التاريخ الفعلي الذي تمثله المعلومة | `observation_date` | تاريخ صالح بصيغة `YYYY-MM-DD` ولا يقع في المستقبل (`observation_date <= CURRENT_DATE()`) وإلا يُعزل كـ `FUTURE_OBSERVATION_DATE` |
| 11 | **`ingested_at`** | `TIMESTAMP` | نعم | وقت إدخال السجل إلى طبقة Bronze بالتوقيت العالمي `UTC` | يُولّد تلقائياً عند السحب | طابع زمني صالح (`UTC ISO-8601`) |
| 12 | **`source_url`** | `STRING` | نعم | رابط المصدر أو اسم الملف الخام وتصنيف المصدر | `source_url` | غير فارغ لحفظ أصل المعلومة (`Data Lineage`) |
| 13 | **`quality_status`** | `STRING` | نعم | نتيجة فحوصات الجودة أو سبب العزل | يُولّد بواسطة محرك الجودة في `Silver` | `VALID` للسجلات المقبولة، أو كود/أكواد الخطأ للسجلات المعزولة في `Quarantine` |
| 14 | **`record_hash`** | `STRING` | نعم | بصمة `SHA-256` للسجل الخام لمنع التكرار وتتبع الأصل | يُولّد في طبقة `Bronze` | نص سداسي عشري بطول 64 حرفاً (`Unique per raw record`) |

---

## 3. قاعدة مطابقة المنتج (`Product Matching & Composite Key Rule`)

وفقاً لمتطلبات المشروع (قسم 6 و 15 في دليل الفريق)، **يُمنع مطابقة الأدوية أو مقارنة أسعارها بالاعتماد على اسم الدواء (`product_name`) فقط**:
- يتم توليد `product_id` الموحد باستخدام المعادلة التالية بعد تنظيف النصوص وتوحيد الأحرف الصغيرة (`lowercase`):
  $$\text{product\_key} = \text{trim(lower(product\_name))} \;\|\; \text{trim(lower(strength))} \;\|\; \text{trim(lower(dosage\_form))} \;\|\; \text{trim(lower(pack\_size))}$$
- بذلك يتم التفريق تلقائياً بين:
  - `Amoxicillin | 500 mg | Capsule | 20 Capsules`
  - `Amoxicillin | 250 mg | Suspension | 100 ml`

---

## 4. قاموس أكواد العزل في غرفة الحجر الصحي (`Quarantine Reason Codes`)

عند فشل أي سجل في اجتياز قواعد الجودة في طبقة **Silver**، لا يتم حذفه، بل يُنقل إلى جدول `silver.supply_chain_quarantine` مع تسجيل أحد الأكواد التالية في عمود `quality_status`:

| كود العزل (`quality_status`) | القاعدة التي انتهكها السجل | مثال من بيانات المشروع الفعلية (`raw_sample.csv`) |
| :--- | :--- | :--- |
| **`MISSING_PRODUCT_NAME`** | حقل `product_name` فارغ أو `NULL` | السطر 10: `,100 mg,Tablet,10 Tablets,SUPP_UNKNOWN,15.00,EGP...` |
| **`NEGATIVE_PRICE`** | قيمة `price` أقل من الصفر (`price < 0`) | السطر 9 (`Metformin`): السعر مسجل `-10.00 EGP` |
| **`FUTURE_OBSERVATION_DATE`** | تاريخ `observation_date` أكبر من تاريخ اليوم | السطر 11 (`Ibuprofen`): التاريخ مسجل `2099-01-01` |
| **`INVALID_DATE_FORMAT`** | تاريخ غير قابل للتحويل إلى صيغة `YYYY-MM-DD` | أي نص تاريخ تالف |
| **`MISSING_CURRENCY`** | وجود سعر رقمي بدون تحديد العملة `currency` | سجل يحتوي على سعر بدون عملة |
| **`DUPLICATE_RECORD`** | تكرار تام لنفس المنتج والمورد والتاريخ والسعر | السجلات المكررة при إعادة السحب |

---

## 5. توصيف المصادر وقيود البيانات (`Source Limitations & Data Labeling`)

التزاماً بسياسة الشفافية ومنع البيانات الوهمية (`Zero-Mock Policy`):
1. **بيانات `data_samples/raw_sample.csv`:** موسومة صراحةً كبيانات اختبار قياسية (`SAMPLE_TEST_DATA`) لقياس تغير الأسعار واختبار قواعد العزل (`Quarantine`).
2. **بيانات `openFDA NDC` و `openFDA Enforcement`:** بيانات تنظيمية حقيقية وموثقة من هيئة الدواء الأمريكية (`VERIFIED_REGULATORY_DATA`)، ولكن وجود الدواء في دليل NDC لا يعني توافر مخزون تجاري لحظي في الصيدليات.
3. **بيانات `Kaggle 1mg (medicine_data.csv)`:** بيانات مرجعية تكميلية؛ الأسعار الواردة بها مقومة بالروبية الهندية (`INR`) للسوق الهندي ولا تُخلط مع أسعار الجنيه المصري (`EGP`) أو الدولار (`USD`).
