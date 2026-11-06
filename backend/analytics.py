import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

logger = logging.getLogger("vaanibi.analytics")

# Comprehensive Column & Entity Aliases (English, Hindi transliterated, and Devanagari)
ALIASES = {
    "metric": {
        "sales": [
            "sales", "total", "total sales", "revenue", "amount", "cogs", "gross income",
            "bikri", "vikray", "aamdani", "turnover", "rajasva", "rupaye",
            "बिक्री", "राजस्व", "आमदनी", "रकम", "कुल बिक्री"
        ],
        "quantity": [
            "quantity", "qty", "volume", "units", "items", "count",
            "matra", "sankhya", "sankhyaa", "pieces",
            "मात्रा", "संख्या", "इकाई"
        ],
        "price": [
            "unit price", "price", "rate", "cost", "mrp",
            "kimat", "moolya", "dar", "daam",
            "कीमत", "मूल्य", "दर", "दाम"
        ],
        "rating": [
            "rating", "score", "review", "stars",
            "santushti", "reting",
            "रेटिंग", "समीक्षा"
        ],
        "profit": [
            "gross income", "profit", "margin", "income",
            "munafa", "labh", "fayda",
            "मुनाफा", "लाभ", "फायदा"
        ]
    },
    "group": {
        "category": [
            "product line", "category", "item category", "type",
            "shreni", "varg", "kategori", "prakar",
            "श्रेणी", "वर्ग", "प्रकार"
        ],
        "product": [
            "product line", "product", "item", "product_name", "title",
            "utpad", "saman", "maal",
            "उत्पाद", "सामान", "माल"
        ],
        "branch": [
            "branch", "store", "outlet", "shop", "center",
            "shakha", "dukaan", "kendra",
            "शाखा", "दुकान", "केंद्र"
        ],
        "city": [
            "city", "town", "region", "location", "place",
            "shahar", "sthan", "nagar",
            "शहर", "स्थान", "नगर"
        ],
        "customer_type": [
            "customer type", "membership", "customer", "client",
            "grahak", "graahak",
            "ग्राहक", "सदस्य"
        ],
        "gender": [
            "gender", "sex",
            "ling", "purush", "mahila",
            "लिंग", "पुरुष", "महिला"
        ],
        "payment": [
            "payment", "payment method", "mode", "tender",
            "bhugtan", "bhughthan",
            "भुगतान", "माध्यम"
        ],
        "date": [
            "date", "order date", "invoice date", "time", "timestamp",
            "tarikh", "dinank", "samay", "mahina", "year", "saal",
            "तारीख", "दिनांक", "समय", "महीना", "साल"
        ]
    }
}

class DatasetSession:
    """Stores the currently uploaded DataFrame and computed profile in memory."""
    def __init__(self):
        self.filename: Optional[str] = None
        self.df: Optional[pd.DataFrame] = None
        self.profile: Optional[Dict[str, Any]] = None

    def load_file(self, file_path: str, original_filename: str) -> Dict[str, Any]:
        """Loads CSV or Excel and builds dataset profile."""
        path = str(file_path)
        if path.lower().endswith((".xlsx", ".xls")):
            self.df = pd.read_excel(path)
        else:
            # Try comma, then semicolon, then tab
            try:
                self.df = pd.read_csv(path)
            except Exception:
                self.df = pd.read_csv(path, sep=None, engine="python")

        self.filename = original_filename
        self.profile = self.compute_profile(self.df, original_filename)
        return self.profile

    @staticmethod
    def compute_profile(df: pd.DataFrame, filename: str) -> Dict[str, Any]:
        """Calculates rows, columns, missing values, duplicates, and column categories."""
        total_rows = int(len(df))
        total_cols = int(len(df.columns))
        missing_count = int(df.isnull().sum().sum())
        missing_pct = round(float(missing_count / (total_rows * total_cols) * 100) if total_rows * total_cols > 0 else 0.0, 2)
        duplicate_rows = int(df.duplicated().sum())
        memory_kb = round(float(df.memory_usage(deep=True).sum() / 1024), 2)

        column_types = {str(col): str(dtype) for col, dtype in df.dtypes.items()}

        numeric_cols = [str(col) for col in df.select_dtypes(include=[np.number]).columns]
        categorical_cols = [str(col) for col in df.select_dtypes(include=["object", "category"]).columns]

        # Detect potential date columns
        date_cols = []
        for col in df.columns:
            if "date" in str(col).lower() or "time" in str(col).lower() or "day" in str(col).lower():
                date_cols.append(str(col))
            elif df[col].dtype == "object":
                # Sample check
                sample = df[col].dropna().head(5)
                try:
                    pd.to_datetime(sample, errors="raise")
                    date_cols.append(str(col))
                except Exception:
                    pass

        # Sample preview (first 10 rows sanitized for JSON)
        sample_df = df.head(10).copy()
        # Format timestamps / replace NaNs
        sample_df = sample_df.fillna("—")
        for col in sample_df.columns:
            if pd.api.types.is_datetime64_any_dtype(sample_df[col]):
                sample_df[col] = sample_df[col].dt.strftime("%Y-%m-%d")
        sample_records = sample_df.to_dict(orient="records")

        # Dynamically generate tailored questions for this dataset
        suggested_questions = DatasetSession.generate_suggested_questions(
            df=df,
            numeric_cols=numeric_cols,
            categorical_cols=categorical_cols,
            date_cols=list(set(date_cols)),
        )

        return {
            "filename": filename,
            "total_rows": total_rows,
            "total_columns": total_cols,
            "columns": [str(c) for c in df.columns],
            "column_types": column_types,
            "missing_count": missing_count,
            "missing_pct": missing_pct,
            "duplicate_rows": duplicate_rows,
            "memory_kb": memory_kb,
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "date_columns": list(set(date_cols)),
            "sample_data": sample_records,
            "suggested_questions": suggested_questions,
        }

    @staticmethod
    def generate_suggested_questions(
        df: pd.DataFrame,
        numeric_cols: List[str],
        categorical_cols: List[str],
        date_cols: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Dynamically analyzes the uploaded dataset schema, columns, and distributions
        to generate tailored analytical questions in English and Hindi.
        """
        questions: List[Dict[str, Any]] = []

        def score_metric(col_name: str) -> int:
            c = col_name.lower()
            score = 0
            if any(k in c for k in ['total', 'sales', 'revenue', 'amount', 'salary', 'profit', 'spend', 'income', 'cogs', 'turnover', 'gross']):
                score += 15
            elif any(k in c for k in ['price', 'cost', 'fee', 'rate', 'quantity', 'qty', 'rating', 'score', 'units', 'age', 'balance', 'gpa']):
                score += 8
            if any(k in c for k in ['id', 'uuid', 'serial', 'index', 'key', 'code', 'phone', 'zip', 'pincode']):
                score -= 25
            return score

        def score_group(col_name: str, nunique: int) -> int:
            c = col_name.lower()
            score = 0
            if any(k in c for k in ['product', 'category', 'line', 'dept', 'department', 'branch', 'store', 'city', 'region', 'country', 'type', 'segment', 'service', 'role', 'team', 'designation']):
                score += 15
            elif any(k in c for k in ['customer', 'gender', 'status', 'payment', 'tier', 'group', 'membership', 'mode', 'channel', 'grade']):
                score += 8
            if any(k in c for k in ['id', 'uuid', 'serial', 'invoice', 'email', 'name', 'address', 'url', 'token']):
                score -= 25
            if 3 <= nunique <= 30:
                score += 6
            elif nunique < 2 or nunique > 60:
                score -= 15
            return score

        # Filter and rank numeric columns
        ranked_metrics = sorted(numeric_cols, key=score_metric, reverse=True)
        # Filter and rank categorical columns
        ranked_groups = sorted(
            categorical_cols,
            key=lambda c: score_group(c, df[c].nunique() if c in df else 0),
            reverse=True
        )

        p_metric = ranked_metrics[0] if ranked_metrics else None
        s_metric = ranked_metrics[1] if len(ranked_metrics) > 1 else None
        p_group = ranked_groups[0] if ranked_groups else None
        s_group = ranked_groups[1] if len(ranked_groups) > 1 else None

        # 1. Highest / Leader question
        if p_metric and p_group:
            questions.append({
                "id": "q_highest",
                "question_en": f"Which {p_group} has the highest {p_metric}?",
                "question_hi": f"{p_group} के अनुसार {p_metric} सबसे अधिक किसमें है?",
                "intent": "HIGHEST",
                "metric": p_metric,
                "group": p_group,
                "category": "Leader",
                "badge": "Top Performer",
                "icon": "trophy"
            })

        # 2. Comparison / Distribution question
        if p_metric and p_group:
            questions.append({
                "id": "q_compare",
                "question_en": f"Compare {p_metric} across {p_group}",
                "question_hi": f"{p_group} के अनुसार {p_metric} की तुलना करें",
                "intent": "COMPARE",
                "metric": p_metric,
                "group": p_group,
                "category": "Comparison",
                "badge": "Breakdown",
                "icon": "bar-chart"
            })

        # 3. Average / Benchmark question
        if p_metric and p_group:
            questions.append({
                "id": "q_avg",
                "question_en": f"What is the average {p_metric} by {p_group}?",
                "question_hi": f"{p_group} के हिसाब से औसत {p_metric} क्या है?",
                "intent": "AVERAGE",
                "metric": p_metric,
                "group": p_group,
                "category": "Average",
                "badge": "Mean Value",
                "icon": "pie-chart"
            })

        # 4. Temporal Trend (if date column exists)
        if p_metric and date_cols:
            questions.append({
                "id": "q_trend",
                "question_en": f"Show monthly {p_metric} trend",
                "question_hi": f"समय के अनुसार {p_metric} का मासिक ट्रेंड दिखाएं",
                "intent": "TREND",
                "metric": p_metric,
                "group": date_cols[0],
                "category": "Trend",
                "badge": "Time Series",
                "icon": "trending-up"
            })

        # 5. Secondary group breakdown
        if p_metric and s_group:
            questions.append({
                "id": "q_group2",
                "question_en": f"Compare {p_metric} by {s_group}",
                "question_hi": f"{s_group} के अनुसार {p_metric} का विवरण दिखाएं",
                "intent": "COMPARE",
                "metric": p_metric,
                "group": s_group,
                "category": "Breakdown",
                "badge": "Secondary Group",
                "icon": "layers"
            })

        # 6. Secondary metric analysis
        if s_metric and p_group:
            s_name = s_metric.lower()
            is_avg_preferred = any(w in s_name for w in ['price', 'rating', 'score', 'rate', 'age', 'percentage'])
            if is_avg_preferred:
                q_en = f"What is the average {s_metric} by {p_group}?"
                q_hi = f"{p_group} के हिसाब से औसत {s_metric} क्या है?"
                q_intent = "AVERAGE"
            else:
                q_en = f"Compare {s_metric} across {p_group}"
                q_hi = f"{p_group} के अनुसार {s_metric} की तुलना करें"
                q_intent = "COMPARE"
            questions.append({
                "id": "q_metric2",
                "question_en": q_en,
                "question_hi": q_hi,
                "intent": q_intent,
                "metric": s_metric,
                "group": p_group,
                "category": "Metric Analysis",
                "badge": "Metric Deep-Dive",
                "icon": "compass"
            })

        # 7. Lowest / Minimum question
        if p_metric and p_group:
            questions.append({
                "id": "q_lowest",
                "question_en": f"Which {p_group} has the lowest {p_metric}?",
                "question_hi": f"किस {p_group} में सबसे कम {p_metric} है?",
                "intent": "LOWEST",
                "metric": p_metric,
                "group": p_group,
                "category": "Lowest",
                "badge": "Lowest Performer",
                "icon": "arrow-down"
            })

        # 8. Row Count & Dataset Overview
        questions.append({
            "id": "q_rows",
            "question_en": "How many rows are in the dataset?",
            "question_hi": "इस डेटासेट में कुल कितनी पंक्तियाँ और रिकॉर्ड हैं?",
            "intent": "COUNT_ROWS",
            "metric": None,
            "group": None,
            "category": "Overview",
            "badge": "Dataset Scale",
            "icon": "database"
        })

        return questions

# Global in-memory dataset session
active_session = DatasetSession()


class QuestionPlanner:
    """
    Interprets natural language queries (English and Hindi), binds columns,
    executes pandas aggregations, generates Plotly visualizations,
    and returns conversational responses.
    """

    @classmethod
    def match_column(cls, text: str, available_cols: List[str], alias_group: str) -> Optional[str]:
        """Matches query text against dataset columns using exact match, concept aliases, and substrings."""
        text_lower = text.lower()
        col_lookup = {str(c).lower(): str(c) for c in available_cols}

        # 1. Exact direct occurrence of column name in query
        for col_lower, original_col in col_lookup.items():
            if col_lower in text_lower:
                return original_col

        # 2. Check concept aliases
        group_aliases = ALIASES.get(alias_group, {})
        for concept, aliases in group_aliases.items():
            matched_alias = any(a.lower() in text_lower for a in aliases)
            if matched_alias:
                # Find matching column in dataset for this concept
                # 2a. First check if any column matches the aliases of this concept
                for a in aliases:
                    for col_lower, original_col in col_lookup.items():
                        if a.lower() == col_lower or a.lower() in col_lower:
                            return original_col
                # 2b. Check if concept name itself is in column name
                for col_lower, original_col in col_lookup.items():
                    if concept in col_lower:
                        return original_col

        return None

    @classmethod
    def detect_intent(cls, query: str) -> str:
        """Classifies user intent based on keywords in English and Hindi."""
        q = query.lower()

        if any(w in q for w in [
            "how many rows", "row count", "kitne rows", "kitna data", "total records",
            "number of records", "kitne record", "rows kitne", "records count", "कुल पंक्तियाँ", "कितने रो"
        ]):
            return "COUNT_ROWS"

        if any(w in q for w in [
            "highest", "most", "top", "max", "sabse jyada", "sabse adhik", "sarvoch",
            "sabse bada", "bestseller", "leading", "sabse zyada", "सबसे ज्यादा", "सबसे अधिक", "शीर्ष"
        ]):
            return "HIGHEST"

        if any(w in q for w in [
            "lowest", "least", "bottom", "min", "sabse kam", "sabse ghatia", "kam se kam",
            "सबसे कम", "न्यूनतम"
        ]):
            return "LOWEST"

        if any(w in q for w in [
            "monthly", "trend", "over time", "timeline", "growth", "progression",
            "mahina", "mahine", "tarikh", "dinank", "samay", "महीने", "ट्रेंड", "समय के अनुसार"
        ]):
            return "TREND"

        if any(w in q for w in [
            "average", "avg", "mean", "ausat", "madhya", "per", "औसत"
        ]):
            return "AVERAGE"

        if any(w in q for w in [
            "compare", "breakdown", "distribution", "by", "wise", "tulna", "antarr", "hisab se",
            "तुलना", "के हिसाब से", "विभाजन"
        ]):
            return "COMPARE"

        if any(w in q for w in [
            "total", "sum", "overall", "kul", "sab milakar", "कुल", "समग्र"
        ]):
            return "TOTAL"

        return "GENERAL_AGG"

    @classmethod
    def execute_query(cls, query: str, language: str = "hi-IN") -> Dict[str, Any]:
        """Executes question analysis on the active dataset."""
        if active_session.df is None or len(active_session.df) == 0:
            return {
                "answer": "कृपया पहले एक CSV या Excel फ़ाइल अपलोड करें। (Please upload a CSV or Excel file first.)",
                "intent": "ERROR",
                "data": None,
                "chart_json": None,
                "metrics_summary": None,
            }

        df = active_session.df
        numeric_cols = [str(c) for c in df.select_dtypes(include=[np.number]).columns]
        categorical_cols = [str(c) for c in df.select_dtypes(include=["object", "category"]).columns]
        date_cols = active_session.profile.get("date_columns", [])

        intent = cls.detect_intent(query)
        is_hindi = language.startswith("hi")

        # 1. Intent: Row count
        if intent == "COUNT_ROWS":
            count = len(df)
            cols_count = len(df.columns)
            if is_hindi:
                answer = f"इस डेटासेट में कुल {count:,} पंक्तियाँ (rows) और {cols_count} कॉलम हैं।"
            else:
                answer = f"The dataset contains {count:,} rows and {cols_count} columns."

            fig = go.Figure(go.Indicator(
                mode="number+gauge",
                value=count,
                title={"text": "Total Rows in Dataset", "font": {"size": 20, "color": "#10b981"}},
                gauge={"axis": {"range": [None, max(count * 1.5, 100)]}, "bar": {"color": "#10b981"}}
            ))
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"color": "#e2e8f0"})

            return {
                "answer": answer,
                "intent": intent,
                "data": [{"Total Rows": count, "Total Columns": cols_count}],
                "chart_json": fig.to_json(),
                "metrics_summary": {"rows": count, "columns": cols_count},
            }

        # Match target metric and group column
        metric_col = cls.match_column(query, numeric_cols, "metric")
        group_col = cls.match_column(query, categorical_cols, "group")

        # Fallback bindings if not explicitly matched
        if not metric_col and numeric_cols:
            # prefer 'total', 'sales', 'revenue', 'quantity', 'price'
            for pref in ["total", "sales", "revenue", "cogs", "quantity", "unit price"]:
                for nc in numeric_cols:
                    if pref in nc.lower():
                        metric_col = nc
                        break
                if metric_col:
                    break
            if not metric_col:
                metric_col = numeric_cols[0]

        if not group_col and categorical_cols:
            # prefer 'product line', 'category', 'branch', 'city'
            for pref in ["product line", "category", "branch", "city", "customer type"]:
                for cc in categorical_cols:
                    if pref in cc.lower():
                        group_col = cc
                        break
                if group_col:
                    break
            if not group_col:
                group_col = categorical_cols[0]

        # 2. Intent: Trend analysis
        if intent == "TREND" and date_cols:
            date_col = date_cols[0]
            try:
                temp_df = df.copy()
                temp_df["_dt"] = pd.to_datetime(temp_df[date_col], errors="coerce")
                temp_df = temp_df.dropna(subset=["_dt"])
                temp_df["Period"] = temp_df["_dt"].dt.to_period("M").astype(str)

                trend_df = temp_df.groupby("Period")[metric_col].sum().reset_index()
                trend_records = trend_df.to_dict(orient="records")

                fig = px.line(
                    trend_df,
                    x="Period",
                    y=metric_col,
                    markers=True,
                    title=f"Monthly Trend of {metric_col}",
                    color_discrete_sequence=["#38bdf8"],
                )
                fig.update_traces(line=dict(width=3), fill="tozeroy", fillcolor="rgba(56, 189, 248, 0.15)")
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font={"color": "#e2e8f0"},
                    xaxis=dict(showgrid=False, title="Month"),
                    yaxis=dict(gridcolor="#334155", title=metric_col),
                )

                best_period = trend_df.loc[trend_df[metric_col].idxmax()]["Period"]
                best_val = trend_df[metric_col].max()

                if is_hindi:
                    answer = f"महीने के हिसाब से {metric_col} का ट्रेंड दर्शाया गया है। सबसे अधिक {metric_col} {best_period} में था ({best_val:,.2f})।"
                else:
                    answer = f"Showing monthly trend for {metric_col}. Peak {metric_col} occurred in {best_period} with {best_val:,.2f}."

                return {
                    "answer": answer,
                    "intent": "TREND",
                    "data": trend_records,
                    "chart_json": fig.to_json(),
                    "metrics_summary": {"peak_period": str(best_period), "peak_value": float(best_val)},
                }
            except Exception as e:
                logger.warning(f"Trend processing failed: {e}")

        # 3. Intent: Highest / Lowest / Compare / Average
        if not group_col or not metric_col:
            # Simple aggregation over metric
            if metric_col:
                total_val = float(df[metric_col].sum())
                avg_val = float(df[metric_col].mean())
                if is_hindi:
                    answer = f"कुल {metric_col} {total_val:,.2f} है, और औसत {metric_col} {avg_val:,.2f} है।"
                else:
                    answer = f"Total {metric_col} is {total_val:,.2f}, with an average of {avg_val:,.2f}."

                fig = px.box(df, y=metric_col, title=f"Distribution of {metric_col}", color_discrete_sequence=["#a855f7"])
                fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font={"color": "#e2e8f0"})
                return {
                    "answer": answer,
                    "intent": "METRIC_SUMMARY",
                    "data": [{"Metric": metric_col, "Total": total_val, "Average": avg_val}],
                    "chart_json": fig.to_json(),
                    "metrics_summary": {"total": total_val, "average": avg_val},
                }
            else:
                return {
                    "answer": "डेटासेट में गणना के लिए कोई उपयुक्त संख्यात्मक कॉलम नहीं मिला। (No suitable numeric column found for calculation.)",
                    "intent": "UNKNOWN",
                    "data": None,
                    "chart_json": None,
                    "metrics_summary": None,
                }

        # Perform groupby aggregation
        agg_func = "mean" if intent == "AVERAGE" else "sum"
        agg_label = "Average" if intent == "AVERAGE" else "Total"

        grouped = df.groupby(group_col)[metric_col].agg(agg_func).reset_index()
        grouped = grouped.sort_values(by=metric_col, ascending=(intent == "LOWEST"))
        grouped[metric_col] = grouped[metric_col].round(2)
        records = grouped.to_dict(orient="records")

        # Top item
        top_row = grouped.iloc[0]
        top_name = str(top_row[group_col])
        top_val = float(top_row[metric_col])

        # Generate answer text
        if intent == "HIGHEST":
            if is_hindi:
                answer = f"'{top_name}' की कुल {metric_col} सबसे अधिक है, जो कि {top_val:,.2f} है।"
            else:
                answer = f"'{top_name}' has the highest {metric_col} at {top_val:,.2f}."
        elif intent == "LOWEST":
            if is_hindi:
                answer = f"'{top_name}' की कुल {metric_col} सबसे कम है, जो कि {top_val:,.2f} है।"
            else:
                answer = f"'{top_name}' has the lowest {metric_col} at {top_val:,.2f}."
        elif intent == "AVERAGE":
            if is_hindi:
                answer = f"{group_col} के अनुसार औसत {metric_col} निकाला गया है। सबसे अधिक औसत '{top_name}' का है ({top_val:,.2f})।"
            else:
                answer = f"Average {metric_col} calculated across {group_col}. Top average belongs to '{top_name}' at {top_val:,.2f}."
        else: # COMPARE / TOTAL
            total_sum = float(grouped[metric_col].sum())
            if is_hindi:
                answer = f"{group_col} के हिसाब से {metric_col} की तुलना की गई है। कुल योग {total_sum:,.2f} है, जिसमें '{top_name}' का योगदान सबसे बड़ा है ({top_val:,.2f})।"
            else:
                answer = f"Comparison of {metric_col} by {group_col}. Total is {total_sum:,.2f}, with '{top_name}' leading at {top_val:,.2f}."

        # Create Plotly Chart
        chart_title = f"{agg_label} {metric_col} by {group_col}"
        if len(grouped) <= 8:
            fig = px.bar(
                grouped,
                x=group_col,
                y=metric_col,
                text=metric_col,
                title=chart_title,
                color=metric_col,
                color_continuous_scale="Viridis",
            )
            fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside")
        else:
            top_grouped = grouped.head(10)
            fig = px.bar(
                top_grouped,
                y=group_col,
                x=metric_col,
                text=metric_col,
                orientation="h",
                title=f"Top 10 {chart_title}",
                color=metric_col,
                color_continuous_scale="Viridis",
            )
            fig.update_traces(texttemplate="%{text:,.2f}", textposition="outside")

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "#e2e8f0"},
            xaxis=dict(gridcolor="#334155"),
            yaxis=dict(gridcolor="#334155"),
            coloraxis_showscale=False,
            margin=dict(l=40, r=40, t=60, b=40),
        )

        return {
            "answer": answer,
            "intent": intent,
            "data": records[:15],
            "chart_json": fig.to_json(),
            "metrics_summary": {
                "group_by": group_col,
                "metric": metric_col,
                "top_entity": top_name,
                "top_value": top_val,
                "total_items": len(grouped),
            },
        }
