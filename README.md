# ckddash
A Synthetic Clinical Data Dashboard for Chronic Kidney Disease Monitoring
📌 Project Overview
本專案旨在建立一個具備300萬人規模的合成臨床數據庫，並開發一套用於監控慢性腎臟病（CKD）病程的自動化儀表板。專案核心在於模擬真實醫院環境中高度異質且具有挑戰性的數據，並展示如何透過 ETL 管道與生物統計模型轉化為臨床決策支持（Clinical Decision Support）工具。

🛠️ Key Technical Features
High-Performance Data Simulation: 利用 Polars 引擎模擬 300 萬筆患者基底，並根據臨床分布引入極端值（Outliers）與非隨機缺失值（MNAR）。

Automated ETL Pipeline: 實作數據清洗、單位換算，並動態計算臨床指標（如 eGFR CKD-EPI 2021 公式）。

Clinical Logic Integration: * CCI Score: 自動化計算查爾森共病指數（Charlson Comorbidity Index），用於評估患者預後。

Risk Stratification: 參考 KDIGO 熱圖（Heatmap）進行風險分層。

Containerized Environment: 使用 Docker 封裝數據庫（PostgreSQL）與處理環境，確保研究結果的可重複性（Reproducibility）。

📊 Data Simulation Logic (數據模擬邏輯)
為了反映真實世界的臨床數據品質，模擬過程包含以下特點：

Distribution Matching: 參考臨床文獻中 CKD 族群的生理指標分布（Median, IQR），模擬包含 SBP, Hb, Potassium, SCr 等核心變項。

Edge Cases & Noise: * 加入生理學上的極端值（如高血鉀、高血壓危象），測試系統的異常偵測能力。

模擬高缺失率（uACR/uPCR 缺失率 > 90%），展示統計插補（Imputation）的需求。

Comorbidity Matrix: 模擬 17 種共病症狀，確保數據支持複雜的 CCI 生存分析分析。

📈 Analysis & Visualization
Table 1 (Baseline Characteristics): 自動生成符合醫學期刊投稿格式的基準特徵表。

eGFR Trajectory: 展示不同共病組別（如糖尿病 vs 非糖尿病）患者腎功能下降的斜率差異。

Population Health View: 提供醫院管理層全院患者的分級分布情形。

目前有3大分析
1. Table 1: 基礎臨床描述統計。

2. Longitudinal: eGFR 斜率下降分析。

3. Survival: ESRD 進展風險預測（Cox Model）。