## set & load 
import polars as pl
import numpy as np

n_patients = 3_000_000
np.random.seed(42)

basedir = r'C:\Users\User\Desktop\Me\ckddash\data'
# --- 1. 使用 tolist() 強制繞過 ndarray 檢查 ---
# 雖然 tolist() 會消耗記憶體，但能確保 Series 構造成功
demo_df = pl.DataFrame([
    pl.Series("PatientID", np.arange(1, n_patients + 1).tolist()),
    pl.Series("Age", np.random.randint(20, 95, n_patients).tolist()),
    pl.Series("Gender", np.random.choice(["M", "F"], n_patients).tolist())
])

# --- 2. 隨機生成共病 ---
comorbidities = [
    "MI", "CHF", "PVD", "CVD", "Dementia", "COPD", "Rheumatic", "PUD",
    "Mild_Liver", "DM_no_complication", "DM_with_complication", "Hemiplegia",
    "Renal_Disease", "Cancer", "Moderate_Liver", "Metastatic_Tumor", "HIV"
]

for disease in comorbidities:
    prob = 0.15 if "DM" in disease or "Renal" in disease else 0.05
    # 同樣使用 .tolist() 確保穩定性
    data = np.random.choice([0, 1], n_patients, p=[1-prob, prob]).tolist()
    demo_df = demo_df.with_columns(pl.Series(disease, data))

def get_dist(median, q1, q3, size):
    """根據中位數與 IQR 模擬常態分布"""
    std = (q3 - q1) / 1.35
    return np.random.normal(median, std, size)


# 讓資料更極端
def get_extreme_dist(median, q1, q3, size, outliers_rate=0.05):
    """
    產生帶有極端值的分布：
    80% 符合常態分布, 15% 偏向病理性極端, 5% 為完全不合理的 Dirty Data
    """
    std = (q3 - q1) / 1.35
    base_data = np.random.normal(median, std, size)
    
    # 加入病理性極端值 (例如 CKD 惡化導致數值飆升或驟降)
    n_outliers = int(size * outliers_rate)
    outlier_indices = np.random.choice(size, n_outliers, replace=False)
    
    # 50% 機率往極大值跑，50% 往極小值跑
    base_data[outlier_indices] = base_data[outlier_indices] * np.random.uniform(2, 5, n_outliers)
    
    return base_data

# --- 2. 臨床指標表 (Clinical Lab Results) ---
# 根據附圖 eGFR < 60 欄位數據模擬 (Median, Q1, Q3)
labs_df = pl.DataFrame({
    "PatientID": np.arange(1, n_patients + 1).tolist(),
    # SBP: 128 (117, 140)
    "SBP": get_extreme_dist(128, 117, 140, n_patients, 0.02).tolist(),
    "DBP": get_extreme_dist(74, 67, 81, n_patients, 0.02).tolist(),
    # Serum Albumin: 4.2 (3.9,4.5)
    "Albumin": get_dist(4.2, 3.9, 4.5, n_patients).tolist(),
    # Serum calcium 9.5 (9.2, 9.8)
    "Calcium": get_dist(9.5, 9.2, 9.8, n_patients).tolist(),
    # serum phosphate: 3.6 (3.1, 4.1)
    "Phosphate": get_dist(3.6, 3.1, 4.1, n_patients).tolist(),
    # Serum potassium: 4.5 (4.2, 4.8)
    # Potassium: 模擬高血鉀 (Hyperkalemia)，這對 CKD 監控非常關鍵
    "Potassium": get_extreme_dist(4.5, 4.2, 4.8, n_patients, 0.08).tolist() ,
    # Serum sodium: 140 (138, 142)
    "Sodium": get_dist(140, 138, 142, n_patients).tolist(),
    # Serum uric acid: 6.3 (5.1, 7.6)
    "Uric_Acid": get_dist(6.3, 5.1, 7.6, n_patients).tolist(),
    # Total Cholesterol: 170 (142, 202)
    "Cholesterol": get_dist(170, 142, 202, n_patients).tolist(),
    # Triglyceride: 117 (85, 165)
    "Triglyceride": get_dist(117, 85, 165, n_patients).tolist(),
    # Hemoglobin: 13.3 (11.9, 14.4)
    "Hemoglobin": get_dist(13.3, 11.9, 14.4, n_patients).tolist(),
    # Fasting Glucose: 102 (94, 115)
    "Glucose": get_dist(102, 94, 115, n_patients).tolist(),
    # uACR: 30 (12, 100) -> 採 Log-normal 模擬偏態分布
    "uACR": np.random.lognormal(mean=np.log(30), sigma=0.8, size=n_patients).tolist(),
    # uPCR: 170 (90, 550) -> 採 Log-normal 模擬偏態分布
    "uPCR": np.random.lognormal(mean=np.log(170), sigma=0.8, size=n_patients).tolist(),
    # Urine Creatinine: 35 (60, 142)    
    "uCreatinine": np.random.lognormal(mean=np.log(35), sigma=0.8, size=n_patients).tolist(),
    # Urine Total protein: 21 (9,84)    
    "uTotal_Protein": np.random.lognormal(mean=np.log(21), sigma=0.8, size=n_patients).tolist(),
    # SCr: 模擬基礎值以利後續計算 eGFR (假設中位數在 1.5 左右)
    "SCr": np.random.normal(1.55, 0.4, n_patients).tolist()
})

# 清洗數據：確保生理數值不為負數
labs_df = labs_df.with_columns([
    pl.when(pl.col(c) < 0).then(0).otherwise(pl.col(c)).alias(c)
    for c in labs_df.columns if c != "PatientID"
])

def calculate_egfr_polars(df):
    # 1. 定義公式中的常數 (基於 2021 CKD-EPI)
    df = df.with_columns([
        pl.when(pl.col("Gender") == "F").then(0.7).otherwise(0.9).alias("kappa"),
        pl.when(pl.col("Gender") == "F").then(-0.241).otherwise(-0.302).alias("alpha"),
        pl.when(pl.col("Gender") == "F").then(1.012).otherwise(1.0).alias("gender_factor")
    ])

    # 2. 執行運算：使用最新的 .clip() API
    # 公式：142 * min(SCr/kappa, 1)^alpha * max(SCr/kappa, 1)^-1.200 * 0.9938^Age * gender_factor
    df = df.with_columns(
        (142 * (pl.col("SCr") / pl.col("kappa")).clip(upper_bound=1).pow(pl.col("alpha")) * (pl.col("SCr") / pl.col("kappa")).clip(lower_bound=1).pow(-1.200) * (0.9938 ** pl.col("Age")) * pl.col("gender_factor")
        ).alias("eGFR")
    )
    
    # 3. 根據 KDIGO 標準進行 CKD 分期 (Risk Stratification)
    df = df.with_columns(
        pl.when(pl.col("eGFR") >= 90).then(pl.lit("G1"))
        .when(pl.col("eGFR") >= 60).then(pl.lit("G2"))
        .when(pl.col("eGFR") >= 45).then(pl.lit("G3a"))
        .when(pl.col("eGFR") >= 30).then(pl.lit("G3b"))
        .when(pl.col("eGFR") >= 15).then(pl.lit("G4"))
        .otherwise(pl.lit("G5")).alias("CKD_Stage")
    )
    return df

def calculate_cci_polars(df):
    # 定義權重清單
    w1 = ["MI", "CHF", "PVD", "CVD", "Dementia", "COPD", "Rheumatic", "PUD", "Mild_Liver", "DM_no_complication"]
    w2 = ["Hemiplegia", "Renal_Disease", "DM_with_complication", "Cancer"]
    w3 = ["Moderate_Liver"]
    w6 = ["Metastatic_Tumor", "HIV"]

    # 使用 horizontal sum 進行高效加權計算
    df = df.with_columns(
        (
            pl.sum_horizontal(pl.col(w1)) * 1 +
            pl.sum_horizontal(pl.col(w2)) * 2 +
            pl.sum_horizontal(pl.col(w3)) * 3 +
            pl.sum_horizontal(pl.col(w6)) * 6
        ).alias("CCI_Score")
    )
    return df

# 1. Join Tables (假設 PatientID 為 Key)
full_df = demo_df.join(labs_df, on="PatientID")

# 2. 執行計算
full_df = calculate_cci_polars(full_df)
full_df = calculate_egfr_polars(full_df)

demo_df.write_parquet(f"{basedir}/demo_df.parquet")
labs_df.write_parquet(f"{basedir}/labs_df.parquet")
