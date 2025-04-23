import pandas as pd
from functools import lru_cache
import streamlit as st

@st.cache_data
def load_classification_map(
    mapping_path: str = "D:/Github/magic_modular/交易对手类别.csv"
) -> dict:
    """
    加载并缓存分类映射：交易对手方名称 -> 分类
    """
    df = pd.read_csv(mapping_path)
    mapping = {}
    for col in df.columns:
        for name in df[col].dropna():
            mapping[name] = col
    return mapping

def apply_classification(
    df: pd.DataFrame,
    source_col: str = 'counterparty',
    mapping_path: str = "D:/Github/magic_modular/交易对手类别.csv"
) -> pd.DataFrame:
    """
    在 DataFrame 上添加一列 '分类'，将 source_col 的值映射到分类。
    未映射项归为 '其它'
    """
    mapping = load_classification_map(mapping_path)
    df['分类'] = df[source_col].map(mapping).fillna('其它')
    return df

def classification_options(
    mapping_path: str = "D:/Github/magic_modular/交易对手类别.csv"
) -> list[str]:
    """
    返回所有可能的分类选项
    """
    mapping = load_classification_map(mapping_path)
    opts = sorted(set(mapping.values()))
    if '其它' not in opts:
        opts.insert(0, '其它')
    return opts
